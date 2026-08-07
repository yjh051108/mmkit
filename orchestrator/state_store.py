from __future__ import annotations

"""工作流 SQLite 持久化（独立脚本，仅依赖标准库）。

从桌面应用 backend_source/services/state_store.py 迁移而来，
去掉 aiosqlite/config 等外部依赖，保留核心 schema 与同步函数接口。
"""

import json
import os
import platform
import sqlite3
import uuid

# -- Schema（迁移自 backend_source/db/schema.sql，新增 last_heartbeat 列） -----
_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    template TEXT NOT NULL,          -- 模板名称，例如 mmkit
    title TEXT NOT NULL,             -- 用户输入的研究问题
    params TEXT DEFAULT '{}',       -- JSON: language/competition/tools 等
    status TEXT DEFAULT 'pending',  -- pending | running | paused | completed | failed
    current_step TEXT,               -- 当前执行的 skill 名称
    workspace_dir TEXT,              -- 工作区目录路径
    enable_checkpoints INTEGER DEFAULT 0,  -- 0=关闭检查点 1=开启检查点
    last_heartbeat TIMESTAMP,        -- 最近一次心跳时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL REFERENCES workflows(id),
    skill_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',   -- pending | running | waiting_checkpoint | completed | failed | skipped
    has_checkpoint INTEGER DEFAULT 0,
    checkpoint_type TEXT,            -- idea_select | approve | feedback
    output_files TEXT DEFAULT '[]',  -- JSON array
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL REFERENCES workflows(id),
    step_name TEXT,
    level TEXT DEFAULT 'info',       -- info | warn | error | progress
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL REFERENCES workflows(id),
    step_name TEXT NOT NULL,
    checkpoint_type TEXT NOT NULL,
    data TEXT DEFAULT '{}',          -- JSON: 展示给用户的数据
    response TEXT,                   -- JSON: 用户的回复
    status TEXT DEFAULT 'pending',   -- pending | resolved
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def default_db_path() -> str:
    """返回默认数据库路径：~/.mmflow/db/workflow.db（跨平台统一，不依赖原应用目录）。"""
    return os.path.join(os.path.expanduser("~"), ".mmflow", "db", "workflow.db")


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    """建立 SQLite 连接，自动创建父目录并初始化 schema。"""
    path = db_path or default_db_path()
    if path != ":memory:":
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        init_needed = not os.path.exists(path)
    else:
        init_needed = True
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if init_needed:
        conn.executescript(_SCHEMA)
        conn.commit()
    return conn


def init_db(db_path: str | None = None) -> None:
    """显式初始化数据库 schema。"""
    conn = _connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _decode_params(value):
    """把 params JSON 字符串解析为 dict。"""
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def _decode_files(value):
    """把 output_files JSON 字符串解析为 list。"""
    try:
        return json.loads(value or "[]")
    except Exception:
        return []


# -- 工作流 CRUD -----------------------------------------------------------

def create_workflow(template_name, workspace, language, competition, problem,
                    tools="python", db_path=None):
    """创建工作流，返回新生成的 workflow_id。"""
    wf_id = uuid.uuid4().hex
    params = {
        "language": language,
        "competition": competition,
        "tools": tools,
    }
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO workflows
               (id, template, title, params, status, workspace_dir, enable_checkpoints)
               VALUES (?, ?, ?, ?, 'pending', ?, 0)""",
            (wf_id, template_name, problem,
             json.dumps(params, ensure_ascii=False), workspace),
        )
        conn.commit()
        return wf_id
    finally:
        conn.close()


def get_workflow(workflow_id, db_path=None):
    """按 id 查询单个工作流，返回 dict 或 None。"""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "SELECT * FROM workflows WHERE id = ?", (workflow_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        wf = dict(row)
        wf["params"] = _decode_params(wf.get("params"))
        return wf
    finally:
        conn.close()


def list_workflows(status=None, db_path=None):
    """列出工作流，可按 status 过滤，按创建时间倒序。"""
    conn = _connect(db_path)
    try:
        if status:
            cur = conn.execute(
                "SELECT * FROM workflows WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM workflows ORDER BY created_at DESC"
            )
        result = []
        for row in cur.fetchall():
            wf = dict(row)
            wf["params"] = _decode_params(wf.get("params"))
            result.append(wf)
        return result
    finally:
        conn.close()


def update_heartbeat(workflow_id, db_path=None):
    """更新工作流心跳时间，返回是否命中。"""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            """UPDATE workflows
               SET last_heartbeat = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (workflow_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# -- 步骤 ------------------------------------------------------------------

def update_step_status(workflow_id, step_index, status, output_files=None,
                       db_path=None):
    """更新（或首次插入）某一步骤的状态。按 (workflow_id, step_order) upsert。
    返回 True 表示成功。"""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "SELECT id FROM workflow_steps WHERE workflow_id = ? AND step_order = ?",
            (workflow_id, step_index),
        )
        existing = cur.fetchone()
        files_json = json.dumps(output_files or [], ensure_ascii=False)
        if existing:
            sets = ["status = ?", "output_files = ?"]
            vals = [status, files_json]
            if status == "running":
                sets.append("started_at = CURRENT_TIMESTAMP")
            elif status == "completed":
                sets.append("completed_at = CURRENT_TIMESTAMP")
            sql = f"UPDATE workflow_steps SET {', '.join(sets)} WHERE id = ?"
            vals.append(existing["id"])
            conn.execute(sql, vals)
        else:
            started_expr = "CURRENT_TIMESTAMP" if status == "running" else "NULL"
            completed_expr = "CURRENT_TIMESTAMP" if status == "completed" else "NULL"
            conn.execute(
                f"""INSERT INTO workflow_steps
                    (workflow_id, skill_name, display_name, step_order, status,
                     output_files, started_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, {started_expr}, {completed_expr})""",
                (workflow_id, f"step_{step_index}", f"Step {step_index}",
                 step_index, status, files_json),
            )
        # 同步 workflow 的 current_step / status
        if status == "running":
            conn.execute(
                """UPDATE workflows
                   SET current_step = ?, status = 'running',
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (f"step_{step_index}", workflow_id),
            )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_current_step(workflow_id, db_path=None):
    """返回当前步骤：优先 status='running' 的步骤，否则第一个 'pending' 步骤。
    若均不存在（全部完成）返回 None。"""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            """SELECT * FROM workflow_steps
               WHERE workflow_id = ? AND status = 'running'
               ORDER BY step_order LIMIT 1""",
            (workflow_id,),
        )
        row = cur.fetchone()
        if not row:
            cur = conn.execute(
                """SELECT * FROM workflow_steps
                   WHERE workflow_id = ? AND status = 'pending'
                   ORDER BY step_order LIMIT 1""",
                (workflow_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        step = dict(row)
        step["output_files"] = _decode_files(step.get("output_files"))
        return step
    finally:
        conn.close()


def advance_step(workflow_id, db_path=None):
    """推进到下一步：
    1. 把当前 running 步骤标记为 completed；
    2. 找到下一个 pending 步骤（按 step_order 升序），标记为 running 并返回其 dict；
    3. 若无下一步，则把 workflow 标记为 completed，返回 None。"""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            """SELECT * FROM workflow_steps
               WHERE workflow_id = ? AND status = 'running'
               ORDER BY step_order LIMIT 1""",
            (workflow_id,),
        )
        current = cur.fetchone()
        if current:
            conn.execute(
                """UPDATE workflow_steps
                   SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (current["id"],),
            )
            cur = conn.execute(
                """SELECT * FROM workflow_steps
                   WHERE workflow_id = ? AND step_order > ? AND status = 'pending'
                   ORDER BY step_order LIMIT 1""",
                (workflow_id, current["step_order"]),
            )
            nxt = cur.fetchone()
        else:
            # 没有正在运行的步骤，直接取第一个 pending
            cur = conn.execute(
                """SELECT * FROM workflow_steps
                   WHERE workflow_id = ? AND status = 'pending'
                   ORDER BY step_order LIMIT 1""",
                (workflow_id,),
            )
            nxt = cur.fetchone()
        if nxt:
            conn.execute(
                """UPDATE workflow_steps
                   SET status = 'running', started_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (nxt["id"],),
            )
            conn.execute(
                """UPDATE workflows
                   SET current_step = ?, status = 'running',
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (nxt["skill_name"], workflow_id),
            )
            conn.commit()
            step = dict(nxt)
            step["status"] = "running"
            step["output_files"] = _decode_files(step.get("output_files"))
            return step
        # 没有下一步，标记 workflow 完成
        conn.execute(
            """UPDATE workflows
               SET status = 'completed', current_step = NULL,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (workflow_id,),
        )
        conn.commit()
        return None
    finally:
        conn.close()


# -- 日志 / 检查点 ----------------------------------------------------------

def add_log(workflow_id, level, message, step_index=None, db_path=None):
    """追加一条日志，step_index 可选。返回 True 表示成功。"""
    step_name = f"step_{step_index}" if step_index is not None else None
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO workflow_logs
               (workflow_id, step_name, level, message)
               VALUES (?, ?, ?, ?)""",
            (workflow_id, step_name, level, message),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def save_checkpoint(workflow_id, step_index, checkpoint_type, data, db_path=None):
    """保存检查点（status='pending'）。返回 True 表示成功。"""
    step_name = f"step_{step_index}"
    data_json = json.dumps(data, ensure_ascii=False)
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO checkpoints
               (workflow_id, step_name, checkpoint_type, data, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (workflow_id, step_name, checkpoint_type, data_json),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# -- 自测 ------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile

    tmp_db = os.path.join(tempfile.gettempdir(), "aris_state_store_test.db")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)

    init_db(tmp_db)

    # 1. 创建工作流
    wf_id = create_workflow(
        "mmkit", "/tmp/ws", "zh", "MCM", "物流网络优化",
        tools="python", db_path=tmp_db,
    )
    print("[1] create_workflow ->", wf_id)

    # 2. 查询工作流
    wf = get_workflow(wf_id, db_path=tmp_db)
    print("[2] get_workflow ->", wf)
    assert wf is not None and wf["title"] == "物流网络优化"
    assert wf["params"]["competition"] == "MCM"
    assert wf["params"]["language"] == "zh"

    # 3. 注册三个 pending 步骤并启动第 0 步
    for i in range(3):
        assert update_step_status(wf_id, i, "pending", db_path=tmp_db) is True
    assert update_step_status(wf_id, 0, "running", db_path=tmp_db) is True
    print("[3] registered steps, started step 0")

    # 4. 查询当前步骤
    cur_step = get_current_step(wf_id, db_path=tmp_db)
    print("[4] get_current_step ->", cur_step)
    assert cur_step is not None and cur_step["step_order"] == 0
    assert cur_step["status"] == "running"

    # 5. 心跳
    assert update_heartbeat(wf_id, db_path=tmp_db) is True
    print("[5] update_heartbeat -> ok")

    # 6. 推进一步
    nxt = advance_step(wf_id, db_path=tmp_db)
    print("[6] advance_step ->", nxt)
    assert nxt is not None and nxt["step_order"] == 1
    assert nxt["status"] == "running"

    # 7. 当前步骤应为 1
    cur_step = get_current_step(wf_id, db_path=tmp_db)
    assert cur_step["step_order"] == 1
    print("[7] current step ->", cur_step["step_order"])

    # 8. 走完剩余步骤
    assert advance_step(wf_id, db_path=tmp_db)["step_order"] == 2
    assert advance_step(wf_id, db_path=tmp_db) is None  # 全部完成
    print("[8] workflow completed")

    # 9. 列表
    wfs = list_workflows(db_path=tmp_db)
    assert len(wfs) == 1 and wfs[0]["status"] == "completed"
    print("[9] list_workflows ->", wfs[0]["status"])

    # 10. 日志 / 检查点
    assert add_log(wf_id, "info", "测试日志", step_index=0, db_path=tmp_db) is True
    assert save_checkpoint(wf_id, 0, "approve", {"k": "v"}, db_path=tmp_db) is True
    print("[10] add_log + save_checkpoint -> ok")

    os.remove(tmp_db)
    print("\nALL TESTS PASSED")
