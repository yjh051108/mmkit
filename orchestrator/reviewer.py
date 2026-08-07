"""独立的外部 LLM 交叉审查脚本。

调用 OpenAI Chat Completions API 对文本进行交叉审查，
支持多轮对话上下文（通过 thread 文件持久化）。

仅依赖 Python 标准库（os / json / urllib.request / argparse）。
若未配置 OPENAI_API_KEY，向 stderr 输出禁用提示并正常退出（退出码 0）。
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional

# 默认模型（可被 OPENAI_MODEL 环境变量覆盖）
_DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# 默认 Base URL（可被 OPENAI_BASE_URL 覆盖，便于使用代理或 Azure）
_DEFAULT_BASE_URL = os.environ.get(
    "OPENAI_BASE_URL", "https://api.openai.com"
).rstrip("/")

# 请求超时（秒）
_TIMEOUT = 120


def _normalize_base_url(base_url: str) -> str:
    """规范化 Base URL，确保带协议、无尾部斜杠。"""
    value = (base_url or "").strip().rstrip("/")
    if value and "://" not in value:
        value = "https://" + value
    return value


def _load_thread(thread_file: str) -> List[Dict[str, str]]:
    """从 thread 文件加载历史对话上下文。

    文件不存在或解析失败时返回空列表。
    """
    if not os.path.isfile(thread_file):
        return []
    try:
        with open(thread_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [
                m
                for m in data
                if isinstance(m, dict) and "role" in m and "content" in m
            ]
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"[Reviewer] 警告：读取 thread 文件失败: {exc}",
            file=sys.stderr,
        )
    return []


def _save_thread(thread_file: str, messages: List[Dict[str, str]]) -> None:
    """保存对话上下文到 thread 文件。"""
    try:
        with open(thread_file, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(
            f"[Reviewer] 警告：保存 thread 文件失败: {exc}",
            file=sys.stderr,
        )


def _call_openai(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str = _DEFAULT_MODEL,
    base_url: str = _DEFAULT_BASE_URL,
    timeout: int = _TIMEOUT,
) -> str:
    """调用 OpenAI Chat Completions API 进行审查，返回文本结果。"""
    url = f"{_normalize_base_url(base_url)}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
    }
    body = json.dumps(payload).encode("utf-8")
    headers["Content-Length"] = str(len(body))

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url, data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise RuntimeError(
            f"HTTP {exc.code}: {raw.decode('utf-8', errors='replace')}"
        ) from exc

    if status != 200:
        raise RuntimeError(
            f"HTTP {status}: {raw.decode('utf-8', errors='replace')}"
        )

    result = json.loads(raw.decode("utf-8"))
    # OpenAI 返回: {"choices": [{"message": {"content": "..."}}]}
    try:
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, list):
            # 部分代理可能返回数组形式
            text = "".join(
                p.get("text", "")
                for p in content
                if isinstance(p, dict)
            )
        else:
            text = content
        if not isinstance(text, str):
            raise RuntimeError(
                f"OpenAI 响应内容非字符串: {type(text).__name__}"
            )
        if not text:
            raise RuntimeError(f"OpenAI 响应无文本内容: {result}")
        return text
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"OpenAI 响应格式错误: {result}") from exc


def review(prompt_text: str, thread: Optional[str] = None) -> str:
    """对指定 prompt 文本进行外部 LLM 交叉审查。

    Args:
        prompt_text: 审查 prompt 文本。
        thread: 可选的 thread 文件路径。若提供，则：
            - 调用前加载历史对话上下文（从 thread 文件读 JSON）
            - 调用后将本次对话（user + assistant）追加并写回 thread 文件。

    Returns:
        审查结果文本。

    Raises:
        RuntimeError: 未配置 OPENAI_API_KEY、API 调用失败或响应格式错误。
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY 未配置，外部审查器不可用。"
            "请设置环境变量后重试，或由 agent 自行完成审查。"
        )

    # 加载历史上下文
    messages: List[Dict[str, str]] = []
    if thread:
        messages = _load_thread(thread)

    # 追加当前用户消息
    messages.append({"role": "user", "content": prompt_text})

    # 调用 API
    result = _call_openai(api_key, messages)

    # 追加 assistant 回复
    messages.append({"role": "assistant", "content": result})

    # 持久化 thread
    if thread:
        _save_thread(thread, messages)

    return result


def review_file(prompt_file: str, thread_file: Optional[str] = None) -> str:
    """从文件读取 prompt 并进行审查。

    Args:
        prompt_file: 包含审查 prompt 的文件路径。
        thread_file: 可选的 thread 文件路径，用于持久化对话上下文。

    Returns:
        审查结果文本。若未配置 OPENAI_API_KEY，返回空字符串。

    Raises:
        FileNotFoundError: prompt 文件不存在。
        RuntimeError: API 调用失败或响应格式错误。
    """
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_text = f.read()
    return review(prompt_text, thread_file)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewer.py",
        description="外部 LLM 交叉审查工具（OpenAI Chat Completions）。",
    )
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="包含审查 prompt 的文件路径。",
    )
    parser.add_argument(
        "--thread-file",
        default=None,
        help="可选的 thread 文件路径，用于多轮对话上下文持久化。",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        text = review_file(args.prompt_file, args.thread_file)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[Reviewer] 错误: {exc}", file=sys.stderr)
        return 1

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
