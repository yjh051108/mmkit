"""独立的视觉描述脚本。

从桌面应用 llm_client.py 中迁移的图片描述逻辑，
去除对 services.state_store 的依赖，改为直接读取环境变量。

优先使用 Anthropic Messages API（claude-3-5-sonnet），若未设置
ANTHROPIC_API_KEY 则回退到 OpenAI Chat Completions API（gpt-4o）。
两个 key 都未设置时抛出 RuntimeError。

仅依赖 Python 标准库（urllib.request / http.client / base64 / json）。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Optional, Tuple
import urllib.error
import urllib.request

# 支持的图像格式 -> MIME 类型映射
_MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}

# 默认提示语
_DEFAULT_PROMPT = "Describe this image in detail."

# 默认模型
_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# 默认 Base URL（可被环境变量覆盖，便于使用代理）
_ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
).rstrip("/")
_OPENAI_BASE_URL = os.environ.get(
    "OPENAI_BASE_URL", "https://api.openai.com"
).rstrip("/")

# 单张图片最大字节数（超出时仅作警告，仍会尝试发送）
_MAX_IMG_BYTES = 5_000_000


def _normalize_base_url(base_url: str) -> str:
    """规范化 Base URL，确保带协议、无尾部斜杠。"""
    value = (base_url or "").strip().rstrip("/")
    if value and "://" not in value:
        value = "https://" + value
    return value


def _read_image(image_path: str) -> Tuple[bytes, str]:
    """读取图像文件并返回 (二进制数据, MIME 类型)。

    扩展名不在白名单内时抛出 ValueError。
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")

    ext = path.suffix.lower().lstrip(".")
    if ext not in _MIME_MAP:
        raise ValueError(
            f"不支持的图像格式: .{ext}，仅支持 {sorted(_MIME_MAP.keys())}"
        )
    mime_type = _MIME_MAP[ext]

    data = path.read_bytes()
    if len(data) > _MAX_IMG_BYTES:
        # 不强制压缩，保持零依赖；仅提示
        print(
            f"[Vision] 警告：图像 {path.name} 体积较大 "
            f"({len(data)} bytes)，可能超出 API 限制",
            file=sys.stderr,
        )
    return data, mime_type


def _http_post_json(
    url: str,
    payload: dict,
    headers: dict,
    timeout: int = 120,
) -> dict:
    """用 urllib.request 发送 POST JSON 请求，返回解析后的 JSON。"""
    body = json.dumps(payload).encode("utf-8")
    req_headers = dict(headers)
    req_headers.setdefault("Content-Type", "application/json")
    req_headers["Content-Length"] = str(len(body))

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url, data=body, headers=req_headers, method="POST"
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
    return json.loads(raw.decode("utf-8"))


def _call_anthropic(
    api_key: str,
    prompt: str,
    image_b64: str,
    mime_type: str,
    model: str = _ANTHROPIC_MODEL,
    base_url: str = _ANTHROPIC_BASE_URL,
    timeout: int = 120,
) -> str:
    """调用 Anthropic Messages API 进行视觉描述。"""
    url = f"{_normalize_base_url(base_url)}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    result = _http_post_json(url, payload, headers, timeout=timeout)
    # Anthropic 返回: {"content": [{"type": "text", "text": "..."}, ...]}
    try:
        parts = result.get("content", [])
        texts = [
            p.get("text", "")
            for p in parts
            if isinstance(p, dict) and p.get("type") == "text"
        ]
        text = "".join(t for t in texts if t)
        if not text:
            raise RuntimeError(f"Anthropic 响应无文本内容: {result}")
        return text
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Anthropic 响应格式错误: {result}") from exc


def _call_openai(
    api_key: str,
    prompt: str,
    image_b64: str,
    mime_type: str,
    model: str = _OPENAI_MODEL,
    base_url: str = _OPENAI_BASE_URL,
    timeout: int = 120,
) -> str:
    """调用 OpenAI Chat Completions API 进行视觉描述。"""
    url = f"{_normalize_base_url(base_url)}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
    }
    result = _http_post_json(url, payload, headers, timeout=timeout)
    # OpenAI 返回: {"choices": [{"message": {"content": "..."}}]}
    try:
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, list):
            # 部分代理可能返回数组形式
            text = "".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        else:
            text = content
        if not isinstance(text, str):
            raise RuntimeError(f"OpenAI 响应内容非字符串: {type(text).__name__}")
        if not text:
            raise RuntimeError(f"OpenAI 响应无文本内容: {result}")
        return text
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"OpenAI 响应格式错误: {result}") from exc


def describe_image(image_path: str, prompt: str = _DEFAULT_PROMPT) -> str:
    """描述图片内容。

    优先使用 ANTHROPIC_API_KEY 调用 Anthropic Messages API；
    若未设置则回退到 OPENAI_API_KEY 调用 OpenAI Chat Completions API；
    两者均未设置时抛出 RuntimeError。

    Args:
        image_path: 图像文件路径，支持 png/jpg/jpeg/gif/webp。
        prompt: 描述图片所用的提示语，默认为英文简要提示。

    Returns:
        图片描述文本。

    Raises:
        FileNotFoundError: 图像文件不存在。
        ValueError: 不支持的图像格式。
        RuntimeError: 未配置任何 API Key 或 API 调用失败。
    """
    img_data, mime_type = _read_image(image_path)
    img_b64 = base64.b64encode(img_data).decode("ascii")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if not anthropic_key and not openai_key:
        raise RuntimeError(
            "未设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY，"
            "请通过环境变量配置至少一个 API Key。"
        )

    last_error: Optional[Exception] = None

    if anthropic_key:
        try:
            return _call_anthropic(
                anthropic_key, prompt, img_b64, mime_type
            )
        except Exception as exc:
            last_error = exc
            print(
                f"[Vision] Anthropic 调用失败: {exc}",
                file=sys.stderr,
            )
            # 继续尝试 OpenAI 回退

    if openai_key:
        try:
            return _call_openai(openai_key, prompt, img_b64, mime_type)
        except Exception as exc:
            last_error = exc
            print(
                f"[Vision] OpenAI 调用失败: {exc}",
                file=sys.stderr,
            )

    raise RuntimeError(
        f"所有可用的视觉 API 均调用失败。最后错误: {last_error}"
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vision.py",
        description="独立的图片视觉描述工具（Anthropic / OpenAI）。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    desc = sub.add_parser("describe", help="描述指定图片的内容。")
    desc.add_argument("image_path", help="图像文件路径")
    desc.add_argument(
        "--prompt",
        default=_DEFAULT_PROMPT,
        help=f"描述图片所用的提示语（默认: {_DEFAULT_PROMPT}）",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "describe":
        try:
            text = describe_image(args.image_path, args.prompt)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(f"[Vision] 错误: {exc}", file=sys.stderr)
            return 1
        print(text)
        return 0

    parser.error(f"未知命令: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
