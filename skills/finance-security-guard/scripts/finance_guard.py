#!/usr/bin/env python3
"""Deterministic privacy, routing, and delivery checks for finance recruiting."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".yaml", ".yml", ".toml", ".ps1", ".py", ".js", ".mjs"}
TASKS = {"apply", "interview", "review", "portfolio"}
ROUTES = {
    "resume": "workspace/00_inbox/resumes",
    "jd": "workspace/00_inbox/job_descriptions",
    "project": "workspace/00_inbox/projects",
    "constraint": "workspace/00_inbox/constraints",
    "knowledge": "workspace/00_inbox/knowledge",
    "attachment": "workspace/00_inbox/attachments",
    "interview_answer": "workspace/20_interview/sessions",
}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
WINDOWS_USER_PATH_RE = re.compile(r"[A-Z]:\\Users\\[^\\\s]+\\", re.I)
UNIX_USER_PATH_RE = re.compile(r"/(?:Users|home)/[^/\s]+/")
SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|authorization[_ -]?code|auth[_ -]?code|api[_ -]?key|secret|token|cookie)\b\s*[:=]\s*[^\s,;]+"
)
DEFAULT_CONFIG = {
    "mode": "audit",
    "privacy": "strict",
    "approvals": {"share": True, "send": True, "upload": True},
    "rules": {
        "preserve_originals": True,
        "require_evidence_for_claims": True,
        "dry_run_before_send": True,
        "store_credentials": False,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_text_files(target: Path):
    if target.is_file():
        if target.suffix.lower() in TEXT_EXTENSIONS:
            yield target
        return
    for path in target.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def finding(kind: str, severity: str, path: Path, line: int, message: str) -> dict:
    return {
        "kind": kind,
        "severity": severity,
        "file": str(path),
        "line": line,
        "message": message,
    }


def relative_display(path: Path, workspace_root: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.name


def task_privacy_findings(path: Path, text: str, role: str, task: str, workspace_root: Path) -> list[dict]:
    findings = []
    displayed_path = relative_display(path, workspace_root)
    public_task = task == "portfolio"
    for line_number, line in enumerate(text.splitlines(), 1):
        if SECRET_RE.search(line):
            findings.append({
                "kind": "secret",
                "severity": "critical",
                "file": displayed_path,
                "line": line_number,
                "message": "发现疑似密码、授权码或密钥，具体内容已隐藏。",
            })
        if PHONE_RE.search(line):
            findings.append({
                "kind": "phone",
                "severity": "high",
                "file": displayed_path,
                "line": line_number,
                "message": "发现手机号，继续对外使用前需要移除或确认。",
            })
        if EMAIL_RE.search(line) and "example.com" not in line.lower():
            if role == "jd":
                severity = "medium"
                message = "发现招聘联系方式，请确认它确实来自岗位信息。"
            elif public_task:
                severity = "high"
                message = "公开材料中发现邮箱地址，需要移除或确认公开用途。"
            else:
                severity = "medium"
                message = "发现邮箱地址，请确认是否需要保留在本次材料中。"
            findings.append({
                "kind": "email",
                "severity": severity,
                "file": displayed_path,
                "line": line_number,
                "message": message,
            })
        if WINDOWS_USER_PATH_RE.search(line) or UNIX_USER_PATH_RE.search(line):
            findings.append({
                "kind": "local_path",
                "severity": "high" if public_task else "medium",
                "file": displayed_path,
                "line": line_number,
                "message": "发现本机用户路径，公开材料中不应保留。" if public_task else "发现本机路径，请确认生成材料不会带出该路径。",
            })
    return findings


def evidence_excerpts(path: Path, text: str, role: str, workspace_root: Path) -> list[dict]:
    if role == "jd":
        return []
    excerpts = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = " ".join(raw_line.split())
        if len(line) < 8 or len(line) > 220:
            continue
        if SECRET_RE.search(line) or PHONE_RE.search(line) or EMAIL_RE.search(line):
            continue
        excerpts.append({
            "type": "source_excerpt",
            "text": line,
            "source": relative_display(path, workspace_root),
            "line": line_number,
            "role": role,
        })
        if len(excerpts) >= 10:
            break
    return excerpts


def task_missing(task: str, readable_by_role: dict[str, list[str]], all_candidate_text: str) -> list[str]:
    missing = []
    if task == "apply":
        if not readable_by_role.get("resume"):
            missing.append("需要一份可读取的简历文本；PDF 或 DOCX 请同时提供对应的 TXT/MD 导出。")
        if not readable_by_role.get("jd"):
            missing.append("需要一份可读取的岗位描述文本，才能区分岗位要求与候选人经历。")
        checks = [
            (r"学校|大学|学院|教育|education|university|college", "简历中未识别到教育背景。"),
            (r"实习|经历|项目|experience|intern|project", "简历中未识别到经历或项目证据。"),
            (r"到岗|每周|实习时间|毕业|availability|graduate", "未识别到到岗时间、每周天数或毕业时间。"),
        ]
        for pattern, message in checks:
            if all_candidate_text and not re.search(pattern, all_candidate_text, re.I):
                missing.append(message)
    elif task == "interview":
        if not readable_by_role.get("resume"):
            missing.append("需要一份可读取的简历文本，才能按真实经历准备面试。")
        if not readable_by_role.get("jd"):
            missing.append("尚未提供可读取的岗位描述，面试准备只能基于简历进行。")
    elif task == "review" and not any(readable_by_role.values()):
        missing.append("至少需要一个可读取的文本文件，当前文件只能登记，不能分析内容。")
    elif task == "portfolio" and not any(readable_by_role.values()):
        missing.append("至少需要一个可读取的作品说明或项目文本，当前文件只能登记，不能检查公开内容。")
    return missing


def analyze_task(task: str, files: list[dict], workspace_root: Path, task_id: str) -> dict:
    if task not in TASKS:
        raise ValueError("Unsupported task.")
    if not files:
        raise ValueError("请先选择需要处理的文件。")

    sources = []
    skipped = []
    privacy_findings = []
    evidence_facts = []
    readable_by_role: dict[str, list[str]] = {}
    candidate_texts = []

    for item in files:
        path = Path(item["path"])
        role = str(item.get("role", "material"))
        displayed_path = relative_display(path, workspace_root)
        source = {
            "name": str(item.get("name") or path.name),
            "role": role,
            "saved_to": displayed_path,
            "sha256": sha256(path),
        }
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            source["readable"] = False
            sources.append(source)
            skipped.append({
                "name": source["name"],
                "role": role,
                "reason": f"{path.suffix.lower() or '该格式'} 文件已保存，但当前版本不会假装读取其正文。",
            })
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        source["readable"] = True
        source["characters"] = len(text)
        sources.append(source)
        readable_by_role.setdefault(role, []).append(text)
        if role != "jd":
            candidate_texts.append(text)
        privacy_findings.extend(task_privacy_findings(path, text, role, task, workspace_root))
        evidence_facts.extend(evidence_excerpts(path, text, role, workspace_root))

    missing = task_missing(task, readable_by_role, "\n".join(candidate_texts))
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    highest = max((severity_rank[item["severity"]] for item in privacy_findings), default=0)
    verdict = "BLOCKED" if highest >= 3 else "REVIEW" if privacy_findings or skipped or missing else "READY"
    next_actions = {
        "apply": ["补齐缺失信息", "确认可用事实", "生成岗位定制材料包"],
        "interview": ["补齐岗位信息", "确认经历证据", "生成面试问题与回答框架"],
        "review": ["处理高风险项", "确认保留内容", "生成整理建议"],
        "portfolio": ["移除公开风险", "确认可公开事实", "生成公开清单"],
    }[task]
    result = {
        "task": task,
        "task_id": task_id,
        "sources": sources,
        "skipped": skipped,
        "privacy_findings": privacy_findings,
        "evidence_facts": evidence_facts,
        "missing": missing,
        "verdict": verdict,
        "next_actions": next_actions,
        "external_action": "NONE",
    }
    output_dir = workspace_root / "workspace" / "40_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{task_id}.check.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["result_file"] = relative_display(output_path, workspace_root)
    return result


def load_operating_config(config_value: str | None = None) -> tuple[dict, str]:
    target = Path(config_value).resolve() if config_value else Path.cwd() / ".finance-security-guard" / "config.json"
    if not target.is_file():
        return json.loads(json.dumps(DEFAULT_CONFIG)), "built-in strict defaults"
    value = json.loads(target.read_text(encoding="utf-8-sig"))
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    for key in ("mode", "privacy"):
        if key in value:
            config[key] = value[key]
    if "privacy_mode" in value:
        config["privacy"] = value["privacy_mode"]
    for section in ("approvals", "rules"):
        if isinstance(value.get(section), dict):
            config[section].update(value[section])
    approval_aliases = {
        "require_share_approval": "share",
        "require_send_approval": "send",
        "require_upload_approval": "upload",
    }
    for legacy_key, approval_key in approval_aliases.items():
        if legacy_key in value:
            config["approvals"][approval_key] = bool(value[legacy_key])
    if config["privacy"] not in {"strict", "balanced"}:
        raise ValueError("Invalid privacy mode in configuration.")
    return config, str(target)


def scan(target: Path, config: dict | None = None, config_source: str = "built-in strict defaults") -> dict:
    config = config or DEFAULT_CONFIG
    strict = config.get("privacy") == "strict"
    findings = []
    scanned = 0
    for path in iter_text_files(target):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            findings.append(finding("read_error", "medium", path, 0, "File could not be read."))
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if SECRET_RE.search(line):
                findings.append(finding("secret", "critical", path, line_number, "Possible credential or authorization secret. Value suppressed."))
            if EMAIL_RE.search(line) and "example.com" not in line.lower():
                findings.append(finding("email", "high" if strict else "medium", path, line_number, "Possible personal or recipient email address."))
            if PHONE_RE.search(line):
                findings.append(finding("phone", "high", path, line_number, "Possible mainland China mobile number."))
            if WINDOWS_USER_PATH_RE.search(line) or UNIX_USER_PATH_RE.search(line):
                findings.append(finding("local_path", "high" if strict else "medium", path, line_number, "Local user path may reveal identity or machine state."))
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    highest = max((severity_rank[item["severity"]] for item in findings), default=0)
    verdict = "BLOCKED" if highest >= 3 else "REVIEW" if findings else "READY"
    return {
        "verdict": verdict,
        "privacy_mode": config.get("privacy"),
        "config_source": config_source,
        "files_scanned": scanned,
        "findings": findings,
    }


def route_file(source: Path, input_type: str, workspace_root: Path) -> dict:
    if not source.is_file():
        raise ValueError(f"Input file not found: {source}")
    destination_dir = workspace_root / ROUTES[input_type]
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    if destination.exists() and sha256(destination) != sha256(source):
        destination = destination_dir / f"{source.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{source.suffix}"
    shutil.copy2(source, destination)
    receipt = {
        "type": input_type,
        "source": str(source.resolve()),
        "destination": str(destination.resolve()),
        "sha256": sha256(destination),
        "routed_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = destination.with_name(destination.name + ".route.json")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"verdict": "READY", "file": str(destination), "receipt": str(receipt_path)}


def preflight(manifest_path: Path, config: dict | None = None, config_source: str = "built-in strict defaults") -> dict:
    config = config or DEFAULT_CONFIG
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    mode = str(manifest.get("mode", "")).lower()
    blockers = []
    warnings = []
    if mode not in {"share", "send"}:
        blockers.append("mode must be share or send")
    privacy = manifest.get("privacy_scan", {})
    if privacy.get("verdict") == "BLOCKED":
        blockers.append("privacy scan is blocked")
    if mode == "send":
        recipients = manifest.get("recipients") or []
        if not recipients or any(not EMAIL_RE.fullmatch(str(value)) for value in recipients):
            blockers.append("valid recipients are required")
        if not str(manifest.get("subject", "")).strip():
            blockers.append("subject is required")
        if manifest.get("dry_run_passed") is not True:
            blockers.append("successful dry-run is required")
        if manifest.get("explicit_confirmation") is not True:
            blockers.append("immediate explicit confirmation is required")
        attachments = manifest.get("attachments") or []
        if not attachments:
            blockers.append("at least one attachment is required")
        for value in attachments:
            if not Path(value).is_file():
                blockers.append(f"attachment not found: {Path(value).name}")
        forbidden_keys = {"password", "auth_code", "authorization_code", "token", "api_key", "secret"}
        present = forbidden_keys.intersection({str(key).lower() for key in manifest})
        if present:
            blockers.append("manifest must not contain credential fields")
    if mode == "share" and not manifest.get("sanitized"):
        blockers.append("public package must be marked sanitized")
    if mode == "share" and config.get("approvals", {}).get("share", True) and manifest.get("explicit_confirmation") is not True:
        blockers.append("explicit share confirmation is required by configuration")
    if privacy.get("verdict") == "REVIEW":
        warnings.append("privacy findings require review")
    return {
        "verdict": "BLOCKED" if blockers else "REVIEW" if warnings else "READY",
        "mode": mode,
        "privacy_mode": config.get("privacy"),
        "config_source": config_source,
        "blockers": blockers,
        "warnings": warnings,
    }

def selftest() -> dict:
    with tempfile.TemporaryDirectory(prefix="finance-guard-") as temp_value:
        temp = Path(temp_value)
        risky = temp / "risky.txt"
        private_email = "real.person@" + "private.test"
        private_phone = "13800" + "138000"
        private_path = "C:\\Us" + "ers\\Alice\\resume.pdf"
        fake_secret = "DO_NOT_" + "PRINT_THIS_VALUE"
        secret_label = "auth_" + "code"
        risky.write_text(
            f"email: {private_email}\n"
            f"phone: {private_phone}\n"
            f"path: {private_path}\n"
            f"{secret_label}={fake_secret}\n",
            encoding="utf-8",
        )
        strict_config = json.loads(json.dumps(DEFAULT_CONFIG))
        audit = scan(risky, strict_config)
        if audit["verdict"] != "BLOCKED":
            raise ValueError("selftest: risky file was not blocked")
        if fake_secret in json.dumps(audit):
            raise ValueError("selftest: secret value leaked into findings")

        source = temp / "resume.txt"
        source.write_text("Candidate Name\n", encoding="utf-8")
        routed = route_file(source, "resume", temp / "pack")
        if not Path(routed["receipt"]).is_file():
            raise ValueError("selftest: routing receipt was not created")

        attachment = temp / "resume.pdf"
        attachment.write_bytes(b"%PDF-1.4 fictional fixture")
        blocked_manifest = temp / "blocked.json"
        blocked_manifest.write_text(json.dumps({
            "mode": "send",
            "recipients": ["recruiting@example.com"],
            "subject": "Application",
            "attachments": [str(attachment)],
            "dry_run_passed": False,
            "explicit_confirmation": False,
            "privacy_scan": {"verdict": "READY"},
        }), encoding="utf-8")
        if preflight(blocked_manifest, strict_config)["verdict"] != "BLOCKED":
            raise ValueError("selftest: unsafe send was not blocked")

        ready_manifest = temp / "ready.json"
        ready_manifest.write_text(json.dumps({
            "mode": "send",
            "recipients": ["recruiting@example.com"],
            "subject": "Candidate Name - Finance Internship Application",
            "attachments": [str(attachment)],
            "dry_run_passed": True,
            "explicit_confirmation": True,
            "privacy_scan": {"verdict": "READY"},
        }), encoding="utf-8")
        if preflight(ready_manifest, strict_config)["verdict"] != "READY":
            raise ValueError("selftest: valid fictional send manifest did not pass")

        balanced_config = json.loads(json.dumps(DEFAULT_CONFIG))
        balanced_config["privacy"] = "balanced"
        email_only = temp / "public-contact.txt"
        email_only.write_text("Contact: hiring@" + "company.test\n", encoding="utf-8")
        if scan(email_only, balanced_config)["verdict"] != "REVIEW":
            raise ValueError("selftest: balanced mode did not downgrade email finding")

        share_manifest = temp / "share.json"
        share_manifest.write_text(json.dumps({
            "mode": "share",
            "sanitized": True,
            "explicit_confirmation": False,
            "privacy_scan": {"verdict": "READY"},
        }), encoding="utf-8")
        if preflight(share_manifest, strict_config)["verdict"] != "BLOCKED":
            raise ValueError("selftest: configured share approval was not enforced")

        task_root = temp / "task"
        task_root.mkdir()
        task_resume = task_root / "resume.txt"
        task_resume.write_text("某大学 金融学\n研究项目：整理行业数据并撰写报告\n每周可实习四天\n", encoding="utf-8")
        task_jd = task_root / "jd.txt"
        task_jd.write_text("岗位要求：研究能力\n招聘邮箱：hiring@" + "company.test\n", encoding="utf-8")
        task_result = analyze_task("apply", [
            {"path": str(task_resume), "name": "resume.txt", "role": "resume"},
            {"path": str(task_jd), "name": "jd.txt", "role": "jd"},
        ], task_root, "test-apply")
        if task_result["verdict"] != "REVIEW":
            raise ValueError("selftest: recruiting email should require review, not block")
        if not task_result["evidence_facts"]:
            raise ValueError("selftest: readable candidate evidence was not collected")

        binary_resume = task_root / "resume.pdf"
        binary_resume.write_bytes(b"%PDF-1.4 fixture")
        binary_result = analyze_task("apply", [
            {"path": str(binary_resume), "name": "resume.pdf", "role": "resume"},
            {"path": str(task_jd), "name": "jd.txt", "role": "jd"},
        ], task_root, "test-binary")
        if not binary_result["skipped"] or not binary_result["missing"]:
            raise ValueError("selftest: unreadable binary input was not reported")

        public_file = task_root / "portfolio.txt"
        public_file.write_text("Local draft: C:\\Us" + "ers\\Alice\\project.md\n", encoding="utf-8")
        public_result = analyze_task("portfolio", [
            {"path": str(public_file), "name": "portfolio.txt", "role": "project"},
        ], task_root, "test-public")
        if public_result["verdict"] != "BLOCKED":
            raise ValueError("selftest: local path in public material was not blocked")
    return {"verdict": "READY", "tests": 9, "message": "Finance guard selftest passed."}


def write_result(result: dict, output: str | None) -> None:
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scan_parser = commands.add_parser("scan", help="Scan text artifacts for privacy risks.")
    scan_parser.add_argument("--input", required=True)
    scan_parser.add_argument("--output")
    scan_parser.add_argument("--config")
    route_parser = commands.add_parser("route", help="Route a user file and write a receipt.")
    route_parser.add_argument("--input", required=True)
    route_parser.add_argument("--type", required=True, choices=sorted(ROUTES))
    route_parser.add_argument("--workspace", required=True)
    route_parser.add_argument("--output")
    preflight_parser = commands.add_parser("preflight", help="Validate a share or send manifest.")
    preflight_parser.add_argument("--manifest", required=True)
    preflight_parser.add_argument("--output")
    preflight_parser.add_argument("--config")
    commands.add_parser("selftest", help="Run isolated deterministic smoke tests.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "scan":
            target = Path(args.input)
            if not target.exists():
                raise ValueError(f"Input not found: {target}")
            config, source = load_operating_config(args.config)
            result = scan(target, config, source)
        elif args.command == "route":
            result = route_file(Path(args.input), args.type, Path(args.workspace))
        elif args.command == "preflight":
            config, source = load_operating_config(args.config)
            result = preflight(Path(args.manifest), config, source)
        else:
            result = selftest()
        write_result(result, getattr(args, "output", None))
        return 2 if result["verdict"] == "BLOCKED" else 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        write_result({"verdict": "BLOCKED", "error": str(error)}, getattr(args, "output", None))
        return 2


if __name__ == "__main__":
    sys.exit(main())
