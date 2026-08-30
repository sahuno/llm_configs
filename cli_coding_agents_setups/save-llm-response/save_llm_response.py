#!/usr/bin/env python3
"""Save the last assistant reply to docs/llm_responses/ without the model re-emitting it.

Harness-agnostic:
  python3 save_llm_response.py last [--cwd DIR] [--harness auto|claude|grok|codex|opencode]
  python3 save_llm_response.py response --question TEXT [--cwd DIR]

Also a hook (JSON on stdin): Claude UserPromptExpansion/UserPromptSubmit/Stop
and Grok UserPromptSubmit/Stop (camelCase envelope).

Author: Samuel Ahuno
Date: 2026-08-22
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional
from urllib.parse import quote

OUT_SUBDIR = Path("docs") / "llm_responses"
STATE_DIR = Path.home() / ".llm_configs" / "cache"
MARKER_DIR = STATE_DIR / "save-response"
DEDUP_PATH = STATE_DIR / "last-save.json"
DEDUP_SECONDS = 120
MAX_SLUG_WORDS = 6
MAX_SLUG_CHARS = 50
_NON_SLUG = re.compile(r"[^\w\s-]+", re.UNICODE)
_SPACES = re.compile(r"[\s_]+")
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
HARNESSES = ("claude", "grok", "codex", "opencode")


def marker_path(session_id: str) -> Path:
    safe = _SAFE_ID.sub("_", session_id or "unknown")[:80] or "unknown"
    return MARKER_DIR / f"{safe}.json"


def emit(payload: Mapping[str, Any], exit_code: int = 0) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(exit_code)


def yaml_quote(value: str) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def slugify(text: str, max_words: int = MAX_SLUG_WORDS, max_chars: int = MAX_SLUG_CHARS) -> str:
    source = (text or "").strip()
    heading = ""
    first_line = ""
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not heading and stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
        if not first_line:
            first_line = stripped.lstrip("-* ").strip()
        if heading and first_line:
            break
    source = heading or first_line or source
    source = _NON_SLUG.sub("", source.lower()).strip()
    words = [w for w in _SPACES.split(source) if w][:max_words]
    slug = "-".join(words)[:max_chars].strip("-")
    return slug or "response"


def topic_from_slug(slug: str) -> str:
    return slug.replace("-", " ").strip() or "response"


def unique_output_path(directory: Path, stamp: str, slug: str) -> Path:
    candidate = directory / f"{stamp}_{slug}.md"
    if not candidate.exists():
        return candidate
    for index in range(2, 100):
        alt = directory / f"{stamp}_{slug}_{index}.md"
        if not alt.exists():
            return alt
    return directory / f"{stamp}_{slug}_{os.getpid()}.md"


def build_document(
    *,
    source: str,
    cwd: str,
    topic: str,
    body: str,
    question: Optional[str] = None,
    now: Optional[datetime] = None,
    harness: str = "",
) -> str:
    when = now or datetime.now().astimezone()
    date_str = when.strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    lines = [
        "---",
        f"date: {yaml_quote(date_str)}",
        f"topic: {yaml_quote(topic)}",
        f"cwd: {yaml_quote(cwd)}",
        f"source: {yaml_quote(source)}",
    ]
    if harness:
        lines.append(f"harness: {yaml_quote(harness)}")
    lines.extend(["---", "", f"# {topic}", ""])
    if question is not None:
        lines.extend(["## Question", question, "", "## Answer", body.rstrip(), ""])
    else:
        lines.extend([body.rstrip(), ""])
    return "\n".join(lines)


def _body_hash(cwd: str, body: str) -> str:
    return hashlib.sha256(f"{cwd}\n{body}".encode("utf-8", errors="replace")).hexdigest()


def dedup_hit(cwd: str, body: str) -> Optional[Path]:
    if not DEDUP_PATH.is_file():
        return None
    try:
        rec = json.loads(DEDUP_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if rec.get("hash") != _body_hash(cwd, body):
        return None
    try:
        age = datetime.now(timezone.utc).timestamp() - float(rec.get("ts") or 0)
    except (TypeError, ValueError):
        return None
    if age > DEDUP_SECONDS:
        return None
    path = Path(rec.get("path") or "")
    return path if path.is_file() else None


def remember_save(cwd: str, body: str, path: Path) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    DEDUP_PATH.write_text(
        json.dumps(
            {
                "hash": _body_hash(cwd, body),
                "path": str(path),
                "ts": datetime.now(timezone.utc).timestamp(),
            }
        ),
        encoding="utf-8",
    )


def write_response_file(
    *,
    cwd: str,
    slug: str,
    topic: str,
    source: str,
    body: str,
    question: Optional[str] = None,
    now: Optional[datetime] = None,
    harness: str = "",
) -> Path:
    resolved = str(Path(cwd).expanduser().resolve())
    hit = dedup_hit(resolved, body)
    if hit is not None:
        return hit
    when = now or datetime.now().astimezone()
    directory = Path(resolved) / OUT_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    path = unique_output_path(directory, when.strftime("%Y%m%d_%H%M%S"), slug)
    path.write_text(
        build_document(
            source=source,
            cwd=resolved,
            topic=topic,
            body=body,
            question=question,
            now=when,
            harness=harness,
        ),
        encoding="utf-8",
    )
    remember_save(resolved, body, path)
    return path


def extract_text_blocks(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    texts: list[str] = []
    for block in content:
        if isinstance(block, str) and block.strip():
            texts.append(block)
            continue
        if not isinstance(block, Mapping):
            continue
        kind = block.get("type")
        if kind in ("text", "output_text", "input_text") or kind is None:
            text = block.get("text") or ""
            if str(text).strip():
                texts.append(str(text))
    return texts


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        return records
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                records.append(obj)
    return records


def sniff_jsonl(records: list[Mapping[str, Any]]) -> str:
    if not records:
        return "claude"
    first = records[0]
    if first.get("type") == "session_meta" or (first.get("type") == "response_item"):
        return "codex"
    if isinstance(first.get("message"), Mapping) or first.get("sessionId") or first.get("type") in {"file-history-snapshot", "progress"}:
        return "claude"
    if first.get("type") in {"system", "user", "assistant", "reasoning"}:
        return "grok"
    if isinstance(first.get("message"), Mapping):
        return "claude"
    return "claude"


def _message_content(record: Mapping[str, Any]) -> Any:
    message = record.get("message")
    if isinstance(message, Mapping):
        return message.get("content")
    return None


def claude_last_text(records: Iterable[Mapping[str, Any]]) -> str:
    chunks: list[str] = []
    saw_assistant = False
    for record in reversed(list(records)):
        if record.get("isSidechain"):
            continue
        if record.get("type") == "assistant":
            texts = extract_text_blocks(_message_content(record))
            if texts:
                chunks.append("\n\n".join(texts))
            saw_assistant = True
            continue
        if record.get("type") != "user":
            continue
        content = _message_content(record)
        is_tool = isinstance(content, list) and content and all(
            isinstance(block, Mapping) and block.get("type") == "tool_result" for block in content
        )
        if is_tool:
            continue
        if saw_assistant:
            break
    chunks.reverse()
    return "\n\n".join(chunks).strip()


def grok_last_text(records: Iterable[Mapping[str, Any]]) -> str:
    chunks: list[str] = []
    saw_assistant = False
    for record in reversed(list(records)):
        kind = record.get("type")
        if kind == "assistant":
            texts = extract_text_blocks(record.get("content"))
            if texts:
                chunks.append("\n\n".join(texts))
            saw_assistant = True
            continue
        if kind in {"tool_result", "backend_tool_call", "reasoning", "system"}:
            continue
        if kind == "user":
            if record.get("synthetic_reason"):
                continue
            if saw_assistant:
                break
    chunks.reverse()
    return "\n\n".join(chunks).strip()


def codex_last_text(records: Iterable[Mapping[str, Any]]) -> str:
    chunks: list[str] = []
    saw_assistant = False
    for record in reversed(list(records)):
        if record.get("type") != "response_item":
            continue
        payload = record.get("payload") or {}
        if not isinstance(payload, Mapping):
            continue
        if payload.get("type") == "message" and payload.get("role") == "assistant":
            texts = extract_text_blocks(payload.get("content"))
            if texts:
                chunks.append("\n\n".join(texts))
            saw_assistant = True
            continue
        if payload.get("type") == "message" and payload.get("role") == "user" and saw_assistant:
            break
    chunks.reverse()
    return "\n\n".join(chunks).strip()


def last_text_from_jsonl(path: Path, harness: str = "") -> str:
    records = load_jsonl(path)
    kind = harness or sniff_jsonl(records)
    if kind == "grok":
        return grok_last_text(records)
    if kind == "codex":
        return codex_last_text(records)
    return claude_last_text(records)


def claude_project_dir(cwd: str) -> Path:
    encoded = str(Path(cwd).resolve()).replace("/", "-")
    if not encoded.startswith("-"):
        encoded = "-" + encoded.lstrip("-")
    return Path.home() / ".claude" / "projects" / encoded


def latest_file(paths: Iterable[Path]) -> Optional[Path]:
    files = [path for path in paths if path.is_file()]
    if not files:
        return None
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files[0]


def find_claude_transcript(cwd: str, session_id: str = "") -> Optional[Path]:
    folder = claude_project_dir(cwd)
    if session_id:
        candidate = folder / f"{session_id}.jsonl"
        if candidate.is_file():
            return candidate
    if not folder.is_dir():
        return None
    return latest_file(folder.glob("*.jsonl"))


def find_grok_transcript(cwd: str, session_id: str = "") -> Optional[Path]:
    root = Path.home() / ".grok" / "sessions"
    resolved = str(Path(cwd).resolve())
    group = root / quote(resolved, safe="")
    if session_id:
        candidate = group / session_id / "chat_history.jsonl"
        if candidate.is_file():
            return candidate
    if group.is_dir():
        found = latest_file(p / "chat_history.jsonl" for p in group.iterdir() if p.is_dir())
        if found:
            return found
    if not root.is_dir():
        return None
    matches: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        cwd_file = child / ".cwd"
        if cwd_file.is_file():
            try:
                if cwd_file.read_text(encoding="utf-8").strip() == resolved:
                    matches.extend(p / "chat_history.jsonl" for p in child.iterdir() if p.is_dir())
            except OSError:
                continue
    return latest_file(matches)


def find_codex_transcript(cwd: str, session_id: str = "") -> Optional[Path]:
    root = Path.home() / ".codex" / "sessions"
    if not root.is_dir():
        return None
    resolved = str(Path(cwd).resolve())
    files = sorted(root.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    if session_id:
        for path in files:
            if session_id in path.name:
                return path
    for path in files[:40]:
        try:
            with path.open(encoding="utf-8") as handle:
                first = handle.readline()
            rec = json.loads(first)
        except (OSError, json.JSONDecodeError):
            continue
        payload = rec.get("payload") if rec.get("type") == "session_meta" else {}
        if isinstance(payload, Mapping) and str(Path(str(payload.get("cwd") or "")).expanduser()) in {resolved, cwd}:
            return path
        if not payload:
            continue
        try:
            if str(Path(str(payload.get("cwd"))).resolve()) == resolved:
                return path
        except (OSError, TypeError, ValueError):
            continue
    return None


def _json_field(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def opencode_db_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "opencode" / "opencode.db"
    return Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def opencode_last_text(cwd: str, session_id: str = "") -> str:
    db = opencode_db_path()
    if not db.is_file():
        return ""
    resolved = str(Path(cwd).resolve())
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return ""
    try:
        sid = session_id
        if not sid:
            row = con.execute(
                "SELECT id FROM session WHERE directory = ? OR directory = ? ORDER BY time_updated DESC LIMIT 1",
                (resolved, cwd),
            ).fetchone()
            if not row:
                return ""
            sid = row[0]
        messages = con.execute(
            "SELECT id, data FROM message WHERE session_id = ? ORDER BY time_created ASC",
            (sid,),
        ).fetchall()
        last_ids: list[str] = []
        for mid, raw in reversed(messages):
            data = _json_field(raw)
            role = data.get("role") if isinstance(data, Mapping) else ""
            if role == "assistant":
                last_ids.append(mid)
                continue
            if role == "user":
                if last_ids:
                    break
        last_ids.reverse()
        chunks: list[str] = []
        for mid in last_ids:
            parts = con.execute(
                "SELECT data FROM part WHERE message_id = ? ORDER BY time_created ASC",
                (mid,),
            ).fetchall()
            for (raw,) in parts:
                data = _json_field(raw)
                if isinstance(data, Mapping) and data.get("type") == "text":
                    text = str(data.get("text") or "")
                    if text.strip():
                        chunks.append(text)
        return "\n\n".join(chunks).strip()
    except sqlite3.Error:
        return ""
    finally:
        con.close()


def extract_last(
    *,
    cwd: str,
    harness: str = "auto",
    session_id: str = "",
    transcript_path: str = "",
) -> tuple[str, str]:
    """Return (text, harness_used)."""
    if transcript_path:
        path = Path(transcript_path)
        kind = harness if harness in HARNESSES else sniff_jsonl(load_jsonl(path)[:3])
        return last_text_from_jsonl(path, kind), kind

    order = list(HARNESSES) if harness == "auto" else [harness]
    best = ("", "", -1.0)

    def consider(kind: str, text: str, mtime: float) -> None:
        nonlocal best
        if text and mtime >= best[2]:
            best = (text, kind, mtime)

    for kind in order:
        if kind == "claude":
            path = find_claude_transcript(cwd, session_id)
            if path:
                consider(kind, last_text_from_jsonl(path, "claude"), path.stat().st_mtime)
        elif kind == "grok":
            path = find_grok_transcript(cwd, session_id)
            if path:
                consider(kind, last_text_from_jsonl(path, "grok"), path.stat().st_mtime)
        elif kind == "codex":
            path = find_codex_transcript(cwd, session_id)
            if path:
                consider(kind, last_text_from_jsonl(path, "codex"), path.stat().st_mtime)
        elif kind == "opencode":
            text = opencode_last_text(cwd, session_id)
            db = opencode_db_path()
            mtime = db.stat().st_mtime if db.is_file() else 0.0
            consider(kind, text, mtime)
        if harness != "auto" and best[0]:
            break
    return best[0], best[1]


def save_body(
    *,
    body: str,
    cwd: str,
    source: str,
    question: Optional[str] = None,
    slug_hint: str = "",
    harness: str = "",
) -> Path:
    if not body.strip():
        raise ValueError("No previous assistant reply to save (empty or missing turn).")
    slug = slugify(slug_hint or question or body)
    topic = slug_hint.strip() if slug_hint.strip() else topic_from_slug(slug)
    return write_response_file(
        cwd=cwd,
        slug=slug,
        topic=topic,
        source=source,
        body=body,
        question=question,
        harness=harness,
    )


def getv(payload: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return default


def normalize_event(event: str) -> str:
    return str(event or "").replace("-", "_").lower()


def handle_save_last_hook(payload: Mapping[str, Any], args: str = "") -> None:
    cwd = str(getv(payload, "cwd", default=os.getcwd()))
    session_id = str(getv(payload, "session_id", "sessionId", default="") or "")
    transcript = str(getv(payload, "transcript_path", "transcriptPath", default="") or "")
    body, harness = extract_last(cwd=cwd, session_id=session_id, transcript_path=transcript)
    if not body:
        emit(
            {
                "decision": "block",
                "reason": "No previous assistant reply to save (empty or missing turn).",
                "systemMessage": "No previous assistant reply to save.",
            }
        )
    path = save_body(
        body=body,
        cwd=cwd,
        source="save-last (previous assistant turn)",
        slug_hint=args,
        harness=harness,
    )
    message = f"Saved to {path}"
    emit({"decision": "block", "reason": message, "systemMessage": message})


def handle_save_response_start(payload: Mapping[str, Any], args: str) -> None:
    args = args.strip()
    if not args:
        emit(
            {
                "decision": "block",
                "reason": "Usage: /save-response <question>",
                "systemMessage": "Usage: /save-response <question>",
            }
        )
    session_id = str(getv(payload, "session_id", "sessionId", default="") or "")
    path = marker_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "cwd": getv(payload, "cwd", default=os.getcwd()),
                "question": args,
                "session_id": session_id,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    raise SystemExit(0)


def parse_slash(prompt: str) -> tuple[str, str]:
    text = (prompt or "").strip()
    if text.startswith("/save-last"):
        return "save-last", text[len("/save-last") :].strip()
    if text.startswith("/save-response"):
        return "save-response", text[len("/save-response") :].strip()
    return "", ""


def handle_expansion(payload: Mapping[str, Any]) -> None:
    name = str(getv(payload, "command_name", "commandName", default="") or "").strip()
    args = str(getv(payload, "command_args", "commandArgs", default="") or "")
    if name == "save-last":
        handle_save_last_hook(payload, args)
    if name == "save-response":
        handle_save_response_start(payload, args)
    raise SystemExit(0)


def handle_prompt_submit(payload: Mapping[str, Any]) -> None:
    name, args = parse_slash(str(getv(payload, "prompt", default="") or ""))
    if name == "save-last":
        handle_save_last_hook(payload, args)
    if name == "save-response":
        handle_save_response_start(payload, args)
    raise SystemExit(0)


def handle_stop(payload: Mapping[str, Any]) -> None:
    if getv(payload, "stop_hook_active", "stopHookActive"):
        raise SystemExit(0)
    reason = str(getv(payload, "reason", default="end_turn") or "end_turn")
    if reason not in {"end_turn", ""}:
        raise SystemExit(0)
    tasks = getv(payload, "background_tasks", "backgroundTasks", default=[]) or []
    if tasks:
        raise SystemExit(0)
    session_id = str(getv(payload, "session_id", "sessionId", default="") or "")
    path = marker_path(session_id)
    if not path.is_file():
        raise SystemExit(0)
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        try:
            path.unlink()
        except OSError:
            pass
        raise SystemExit(0)
    body = str(getv(payload, "last_assistant_message", "lastAssistantMessage", default="") or "").strip()
    if not body:
        raise SystemExit(0)
    question = str(marker.get("question") or "").strip()
    cwd = str(marker.get("cwd") or getv(payload, "cwd", default=os.getcwd()))
    saved = save_body(
        body=body,
        cwd=cwd,
        source="save-response",
        question=question,
    )
    try:
        path.unlink()
    except OSError:
        pass
    emit({"systemMessage": f"Saved to {saved}"})


def dispatch(payload: Mapping[str, Any]) -> None:
    event = normalize_event(str(getv(payload, "hook_event_name", "hookEventName", default="") or ""))
    if event in {"userpromptexpansion", "user_prompt_expansion"}:
        handle_expansion(payload)
    if event in {"userpromptsubmit", "user_prompt_submit"}:
        handle_prompt_submit(payload)
    if event == "stop":
        handle_stop(payload)
    raise SystemExit(0)


def hook_main(raw: str) -> None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(0)
    if not isinstance(payload, dict):
        raise SystemExit(0)
    event = str(getv(payload, "hook_event_name", "hookEventName", default="") or "")
    try:
        dispatch(payload)
    except SystemExit:
        raise
    except Exception as exc:
        if normalize_event(event) == "stop":
            raise SystemExit(0)
        emit(
            {
                "decision": "block",
                "reason": f"save-last/save-response hook failed: {exc}",
                "systemMessage": f"save-last/save-response hook failed: {exc}",
            }
        )


def cli(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Save the last assistant reply to docs/llm_responses/ without re-emitting it."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    last = sub.add_parser("last", help="Extract the previous assistant turn from the active harness session")
    last.add_argument("--cwd", default=os.getcwd())
    last.add_argument("--harness", choices=("auto",) + HARNESSES, default="auto")
    last.add_argument("--session", default="")
    last.add_argument("--transcript", default="")
    last.add_argument("--slug", default="")
    last.add_argument("--question", default="")
    resp = sub.add_parser("response", help="Same as last, tagging the file as an answer to --question")
    resp.add_argument("--question", required=True)
    resp.add_argument("--cwd", default=os.getcwd())
    resp.add_argument("--harness", choices=("auto",) + HARNESSES, default="auto")
    resp.add_argument("--session", default="")
    resp.add_argument("--transcript", default="")
    args = parser.parse_args(argv)
    body, harness = extract_last(
        cwd=args.cwd,
        harness=args.harness,
        session_id=args.session,
        transcript_path=args.transcript,
    )
    question = args.question.strip() or None
    source = "save-response" if args.cmd == "response" or question else "save-last (previous assistant turn)"
    try:
        path = save_body(
            body=body,
            cwd=args.cwd,
            source=source,
            question=question,
            slug_hint=getattr(args, "slug", "") or "",
            harness=harness,
        )
    except ValueError as exc:
        sys.stderr.write(str(exc) + "\n")
        raise SystemExit(1)
    sys.stdout.write(str(path) + "\n")


def main() -> None:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("{"):
        cli()
        return
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if raw.strip().startswith("{"):
        hook_main(raw)
        return
    sys.stderr.write("Usage: save_llm_response.py last|response [options]\nAlso accepts hook JSON on stdin.\n")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
