#!/usr/bin/env python3
"""Launch the Finance Security Guard local job-material intake UI."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import threading
import uuid
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from finance_guard import TASKS, analyze_task


SKILL_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = SKILL_ROOT / "assets" / "setup.html"
ALLOWED_MODES = {"prepare", "share", "send", "audit"}
ALLOWED_PRIVACY = {"balanced", "strict"}
MAX_REQUEST_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 6 * 1024 * 1024
ALLOWED_ROLES = {"resume", "jd", "project", "notes", "material"}
ROLE_DESTINATIONS = {
    "resume": "workspace/00_inbox/resumes",
    "jd": "workspace/00_inbox/job_descriptions",
    "project": "workspace/00_inbox/projects",
    "notes": "workspace/00_inbox/knowledge",
    "material": "workspace/00_inbox/attachments",
}
TASK_REQUIRED_ROLES = {
    "apply": {"resume", "jd"},
    "interview": {"resume"},
    "review": set(),
    "portfolio": set(),
}


def config_path(workspace: Path) -> Path:
    return workspace / ".finance-security-guard" / "config.json"


def load_config(workspace: Path) -> dict:
    target = config_path(workspace)
    if not target.is_file():
        return {}
    return json.loads(target.read_text(encoding="utf-8-sig"))


def initialize_workspace(workspace: Path) -> None:
    folders = [
        "workspace/00_inbox/resumes",
        "workspace/00_inbox/job_descriptions",
        "workspace/00_inbox/projects",
        "workspace/00_inbox/constraints",
        "workspace/00_inbox/knowledge",
        "workspace/00_inbox/attachments",
        "workspace/10_extracted/resumes",
        "workspace/10_extracted/job_descriptions",
        "workspace/10_extracted/evidence",
        "workspace/10_extracted/gaps",
        "workspace/20_interview/question_sets",
        "workspace/20_interview/sessions",
        "workspace/20_interview/transcripts",
        "workspace/20_interview/evaluations",
        "workspace/30_application/queues",
        "workspace/30_application/emails",
        "workspace/30_application/attachments",
        "workspace/40_outputs",
        "workspace/90_archive",
        "workspace/logs",
    ]
    for folder in folders:
        (workspace / folder).mkdir(parents=True, exist_ok=True)


def validate_config(value: dict) -> dict:
    mode = str(value.get("mode", "")).lower()
    privacy = str(value.get("privacy", "")).lower()
    if mode not in ALLOWED_MODES:
        raise ValueError("请选择主要使用场景。")
    if privacy not in ALLOWED_PRIVACY:
        raise ValueError("请选择隐私拦截等级。")
    approvals = value.get("approvals") or {}
    return {
        "version": 1,
        "mode": mode,
        "privacy": privacy,
        "initialize_workspace": bool(value.get("initialize_workspace", True)),
        "approvals": {
            "share": bool(approvals.get("share", True)),
            "send": True,
            "upload": bool(approvals.get("upload", True)),
        },
        "rules": {
            "preserve_originals": True,
            "require_evidence_for_claims": True,
            "dry_run_before_send": True,
            "store_credentials": False,
            "calendar_event": "actual_send_date",
        },
    }


def safe_filename(value: str) -> str:
    name = Path(value).name.strip()
    if not name:
        raise ValueError("文件名不能为空。")
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._ -]+", "_", name).strip(" .")
    return cleaned[:160] or "upload.bin"


def save_task_files(workspace: Path, task: str, payload_files: list[dict], task_id: str) -> list[dict]:
    if task not in TASKS:
        raise ValueError("请选择一个有效任务。")
    if not payload_files:
        raise ValueError("请先选择需要处理的文件。")
    present_roles = {str(item.get("role", "")) for item in payload_files}
    missing_roles = TASK_REQUIRED_ROLES[task] - present_roles
    if missing_roles:
        labels = {"resume": "简历", "jd": "岗位描述"}
        raise ValueError("还需要选择：" + "、".join(labels.get(role, role) for role in sorted(missing_roles)))

    saved = []
    total_size = 0
    for index, item in enumerate(payload_files):
        role = str(item.get("role", "material"))
        if role not in ALLOWED_ROLES:
            raise ValueError("文件类型不受支持。")
        name = safe_filename(str(item.get("name", "")))
        try:
            content = base64.b64decode(str(item.get("content_base64", "")), validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError(f"{name} 的文件内容无效。") from error
        if not content:
            raise ValueError(f"{name} 是空文件。")
        if len(content) > MAX_FILE_BYTES:
            raise ValueError(f"{name} 超过 6 MB，请压缩或提供文本版本。")
        total_size += len(content)
        if total_size > 12 * 1024 * 1024:
            raise ValueError("本次文件总大小超过 12 MB。")

        destination_dir = workspace / ROLE_DESTINATIONS[role]
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / name
        if destination.exists():
            destination = destination_dir / f"{Path(name).stem}_{task_id}_{index + 1}{Path(name).suffix}"
        destination.write_bytes(content)
        saved.append({"path": str(destination), "name": name, "role": role})
    return saved


def start_task(workspace: Path, payload: dict) -> dict:
    task = str(payload.get("task", "")).lower()
    task_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    initialize_workspace(workspace)
    saved_files = save_task_files(workspace, task, payload.get("files") or [], task_id)
    return analyze_task(task, saved_files, workspace, task_id)


def make_handler(workspace: Path, server_state: dict):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format_string, *args):
            return

        def send_json(self, status: int, value: dict) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlparse(self.path).path
            if route == "/":
                body = HTML_PATH.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if route == "/api/config":
                self.send_json(200, {
                    "ok": True,
                    "configured": config_path(workspace).is_file(),
                    "workspace_name": workspace.name,
                    "config": load_config(workspace),
                })
                return
            if route == "/api/status":
                self.send_json(200, {"ok": True, "service": "finance-security-guard-setup"})
                return
            self.send_json(404, {"ok": False, "error": "Not found."})

        def do_POST(self):
            route = urlparse(self.path).path
            if route not in {"/api/config", "/api/tasks"}:
                self.send_json(404, {"ok": False, "error": "Not found."})
                return
            try:
                origin = self.headers.get("Origin")
                expected_origin = f"http://127.0.0.1:{self.server.server_port}"
                if origin and origin != expected_origin:
                    raise ValueError("拒绝非本地配置页面的请求。")
                length = int(self.headers.get("Content-Length", "0"))
                limit = MAX_REQUEST_BYTES if route == "/api/tasks" else 100_000
                if length <= 0 or length > limit:
                    raise ValueError("请求内容为空或过大。")
                payload = json.loads(self.rfile.read(length) or b"{}")
                if route == "/api/tasks":
                    result = start_task(workspace, payload)
                    self.send_json(200, {"ok": True, **result})
                    return
                config = validate_config(payload)
                if config["initialize_workspace"]:
                    initialize_workspace(workspace)
                target = config_path(workspace)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                server_state["configured"] = True
                self.send_json(200, {
                    "ok": True,
                    "message": "金融保安配置完成。",
                    "config_file": str(target),
                    "next_action": {
                        "prepare": "上传或提供简历与目标 JD。",
                        "share": "选择准备公开分享的文件夹并执行隐私扫描。",
                        "send": "先加载投递材料并运行 dry-run。",
                        "audit": "选择需要审计的本地项目或材料包。",
                    }[config["mode"]],
                })
            except (ValueError, json.JSONDecodeError, OSError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})

    return Handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="Workspace that will own the local configuration.")
    parser.add_argument("--port", type=int, default=47831)
    parser.add_argument("--no-open", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    state = {"configured": config_path(workspace).is_file()}
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(workspace, state))
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(workspace, state))
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(json.dumps({
        "ok": True,
        "url": url,
        "workspace": str(workspace),
        "configured": state["configured"],
        "config_file": str(config_path(workspace)),
    }, ensure_ascii=False))
    if not args.no_open:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
