"""All event, tool-call, and session-meta parsers."""
from __future__ import annotations

import json, re, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import threading

from models import UsageEvent, ToolCall, SessionMeta

CODEX_ROOTS = [Path.home() / ".codex/archived_sessions", Path.home() / ".codex/sessions"]
CLAUDE_ROOT = Path.home() / ".claude/projects"
CURSOR_ROOT = Path.home() / ".cursor/projects"

_FILE_CACHE_LOCK = threading.Lock()
_JSONL_CACHE: dict[str, tuple[tuple[int, int], list[dict]]] = {}


def _file_signature(path: Path) -> tuple[int, int]:
    st = path.stat()
    return st.st_size, int(st.st_mtime_ns)


def _read_json_lines(path: Path) -> list[dict]:
    key = str(path)
    try:
        signature = _file_signature(path)
    except OSError:
        with _FILE_CACHE_LOCK:
            _JSONL_CACHE.pop(key, None)
        return []

    cached = None
    with _FILE_CACHE_LOCK:
        cached = _JSONL_CACHE.get(key)
    if cached is not None and cached[0] == signature:
        return cached[1]

    rows: list[dict] = []
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    except Exception:
        rows = []

    with _FILE_CACHE_LOCK:
        _JSONL_CACHE[key] = (signature, rows)

    return rows


def _ts(raw):
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00")) if raw else None


def _si(v):
    return int(v or 0)


# ── Event Parsers ──────────────────────────────────────────────────────────

def parse_codex_events(start_utc, now_utc):
    ses = defaultdict(list)
    for root in CODEX_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.jsonl"):
            sid, seen, model_name = None, {}, "GPT-5 Codex"
            for obj in _read_json_lines(path):
                pl = obj.get("payload") or {}
                if obj.get("type") == "session_meta":
                    sid = str(pl.get("id") or path.stem)
                    continue
                if obj.get("type") == "turn_context":
                    m = pl.get("model")
                    if isinstance(m, str) and m.strip():
                        model_name = m.strip()
                    cm = pl.get("collaboration_mode")
                    if isinstance(cm, dict):
                        ms = (cm.get("settings") or {}).get("model")
                        if isinstance(ms, str) and ms.strip():
                            model_name = ms.strip()
                    continue
                if obj.get("type") != "event_msg" or pl.get("type") != "token_count":
                    continue
                u = (pl.get("info") or {}).get("total_token_usage")
                if not isinstance(u, dict):
                    continue
                ts = _ts(obj.get("timestamp"))
                if not ts:
                    continue
                cur = {"ts": ts, "input": _si(u.get("input_tokens")),
                       "cached": _si(u.get("cached_input_tokens")),
                       "output": _si(u.get("output_tokens")),
                       "reasoning": _si(u.get("reasoning_output_tokens")),
                       "model": model_name or "GPT-5 Codex"}
                prev = seen.get(ts)
                if prev is None or (cur["input"], cur["cached"], cur["output"], cur["reasoning"]) > (
                        prev["input"], prev["cached"], prev["output"], prev["reasoning"]):
                    seen[ts] = cur
            if seen:
                ses[sid or str(path)].extend(seen.values())
    events = []
    for sid, rows in ses.items():
        bl = {"input": 0, "cached": 0, "output": 0, "reasoning": 0}
        for r in sorted(rows, key=lambda x: x["ts"]):
            if r["ts"] < start_utc:
                bl = r
                continue
            events.append(UsageEvent("Codex", r["ts"], sid, str(r.get("model") or "GPT-5 Codex"),
                                     max(0, r["input"] - bl["input"] - (r["cached"] - bl["cached"])),
                                     max(0, r["cached"] - bl["cached"]),
                                     0, max(0, r["output"] - bl["output"]),
                                     max(0, r["reasoning"] - bl["reasoning"]), 1))
            bl = r
    return events


def _claude_msgs(obj):
    out = []
    m = obj.get("message")
    if isinstance(m, dict) and isinstance(m.get("usage"), dict):
        out.append({"message": m, "timestamp": obj.get("timestamp"), "sessionId": obj.get("sessionId")})
    d = obj.get("data")
    if isinstance(d, dict):
        mw = d.get("message")
        if isinstance(mw, dict):
            nm = mw.get("message")
            if isinstance(nm, dict) and isinstance(nm.get("usage"), dict):
                out.append({"message": nm, "timestamp": mw.get("timestamp") or obj.get("timestamp"),
                            "sessionId": obj.get("sessionId")})
    return out


def parse_claude_events(start_utc, now_utc):
    dedup = {}
    if not CLAUDE_ROOT.exists():
        return []
    for path in CLAUDE_ROOT.rglob("*.jsonl"):
        if path.name == "sessions-index.json":
            continue
        for obj in _read_json_lines(path):
            for pl in _claude_msgs(obj):
                msg, u = pl["message"], pl["message"].get("usage", {})
                ts = _ts(pl.get("timestamp"))
                if not ts or ts < start_utc or ts > now_utc:
                    continue
                mid = str(msg.get("id") or obj.get("uuid") or pl.get("timestamp"))
                sid = str(pl.get("sessionId") or obj.get("sessionId") or path.stem)
                ev = UsageEvent("Claude", ts, sid, str(msg.get("model") or "Claude"),
                                _si(u.get("input_tokens")), _si(u.get("cache_read_input_tokens")),
                                _si(u.get("cache_creation_input_tokens")), _si(u.get("output_tokens")), 0, 1)
                key = (sid, mid)
                prev = dedup.get(key)
                if prev is None or (ev.uncached_input, ev.cache_read, ev.cache_write, ev.output) > (
                        prev.uncached_input, prev.cache_read, prev.cache_write, prev.output):
                    dedup[key] = ev
    return list(dedup.values())


def parse_cursor_events(start_utc, now_utc, local_tz):
    events = []
    if not CURSOR_ROOT.exists():
        return events
    for path in CURSOR_ROOT.rglob("*.jsonl"):
        if "agent-transcripts" not in str(path):
            continue
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=local_tz).astimezone(timezone.utc)
        except Exception:
            continue
        if mtime < start_utc or mtime > now_utc:
            continue
        uc, ac = 0, 0
        for obj in _read_json_lines(path):
            r = obj.get("role") if isinstance(obj, dict) else None
            if r == "user":
                uc += 1
            elif r == "assistant":
                ac += 1
        if uc or ac:
            events.append(UsageEvent("Cursor", mtime, path.stem, "Cursor Agent", activity_messages=uc + ac))
    return events


# ── Tool Call Parsers ──────────────────────────────────────────────────────
_ECR = re.compile(r"Process exited with code (\d+)")


def parse_codex_tool_calls():
    calls = []
    for root in CODEX_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.jsonl"):
            sid, pending = None, {}
            for obj in _read_json_lines(path):
                pl = obj.get("payload") or {}
                if obj.get("type") == "session_meta":
                    sid = str(pl.get("id") or path.stem)
                    continue
                ts = _ts(obj.get("timestamp"))
                if not ts:
                    continue
                s = sid or path.stem
                if obj.get("type") == "event_msg" and pl.get("type") == "response_item":
                    item = pl.get("item") or pl
                    it = item.get("type", "")
                    if it == "function_call":
                        cid = item.get("call_id") or item.get("id", "")
                        try:
                            args = json.loads(item.get("arguments", "") or "{}")
                        except Exception:
                            args = {}
                        tc = ToolCall("Codex", ts, s, item.get("name", "unknown"),
                                     command=args.get("command") or args.get("cmd"),
                                     file_path=args.get("file_path") or args.get("path"))
                        if cid:
                            pending[cid] = tc
                        calls.append(tc)
                    elif it == "function_call_output":
                        m = _ECR.search(str(item.get("output", "")))
                        cid = item.get("call_id", "")
                        if m and cid in pending:
                            pending[cid].exit_code = int(m.group(1))
                    elif it == "web_search_call":
                        calls.append(ToolCall("Codex", ts, s, "web_search"))
                if obj.get("type") == "event_msg" and pl.get("type") == "custom_tool_call":
                    cid = pl.get("id", "")
                    tc = ToolCall("Codex", ts, s, pl.get("name", "custom_tool"))
                    if cid:
                        pending[cid] = tc
                    calls.append(tc)
                if obj.get("type") == "event_msg" and pl.get("type") == "custom_tool_call_output":
                    cid, md = pl.get("id", ""), pl.get("metadata")
                    if isinstance(md, dict) and cid in pending:
                        ec = md.get("exit_code")
                        if ec is not None:
                            try:
                                pending[cid].exit_code = int(ec)
                            except (ValueError, TypeError):
                                pass
    return calls


def parse_claude_tool_calls():
    calls = []
    if not CLAUDE_ROOT.exists():
        return calls
    for path in CLAUDE_ROOT.rglob("*.jsonl"):
        if path.name == "sessions-index.json":
            continue
        objs = _read_json_lines(path)
        err_map = {}
        for obj in objs:
            if obj.get("type") == "user":
                for blk in (obj.get("message") or {}).get("content") or []:
                    if isinstance(blk, dict) and blk.get("type") == "tool_result":
                        err_map[blk.get("tool_use_id", "")] = bool(blk.get("is_error"))
        for obj in objs:
            msg = None
            if obj.get("type") == "assistant":
                msg = obj.get("message", {})
            else:
                m = obj.get("message")
                if isinstance(m, dict) and m.get("role") == "assistant":
                    msg = m
            if not isinstance(msg, dict):
                continue
            ts = _ts(obj.get("timestamp"))
            if not ts:
                continue
            sid = str(obj.get("sessionId") or path.stem)
            for blk in msg.get("content") or []:
                if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                    continue
                tn, inp = blk.get("name", "unknown"), blk.get("input") or {}
                if not isinstance(inp, dict):
                    inp = {}
                cmd = inp.get("command") if tn in ("Bash", "bash") else None
                fp = (inp.get("file_path") if tn in ("Read", "Write", "Edit")
                      else inp.get("path") if tn in ("Grep", "Glob") else None)
                ec = 1 if err_map.get(blk.get("id", "")) else None
                calls.append(ToolCall("Claude", ts, sid, tn, ec, fp, cmd))
    return calls


# ── Session Meta Parsers ──────────────────────────────────────────────────

def parse_codex_session_meta():
    metas, seen = [], set()
    for root in CODEX_ROOTS:
        db = root.parent / "codex.db"
        if db.exists():
            try:
                for r in sqlite3.connect(str(db)).execute(
                        "SELECT id,cwd,git_branch FROM threads").fetchall():
                    sid, cwd, br = str(r[0]), r[1], r[2]
                    metas.append(SessionMeta("Codex", sid, cwd,
                                             Path(cwd).name if cwd else None, br))
                    seen.add(sid)
            except Exception:
                pass
        if not root.exists():
            continue
        for path in root.rglob("*.jsonl"):
            for obj in _read_json_lines(path):
                if isinstance(obj, dict) and obj.get("type") == "session_meta":
                    pl = obj.get("payload") or {}
                    sid = str(pl.get("id") or path.stem)
                    if sid not in seen:
                        cwd = pl.get("cwd")
                        metas.append(SessionMeta("Codex", sid, cwd,
                                                 Path(cwd).name if cwd else None,
                                                 pl.get("git_branch")))
                        seen.add(sid)
    return metas


def parse_claude_session_meta():
    metas, seen = [], set()
    if not CLAUDE_ROOT.exists():
        return metas
    for path in CLAUDE_ROOT.rglob("*.jsonl"):
        if path.name == "sessions-index.json":
            continue
        for obj in _read_json_lines(path):
            if not isinstance(obj, dict) or obj.get("type") != "user":
                continue
            sid = str(obj.get("sessionId") or path.stem)
            if sid in seen:
                continue
            seen.add(sid)
            cwd = obj.get("cwd")
            br = obj.get("gitBranch")
            proj = (Path(cwd).name if cwd and "/" in str(cwd)
                    else str(cwd).rsplit("-", 1)[-1] if cwd else None)
            metas.append(SessionMeta("Claude", sid, cwd, proj, br))
    return metas
