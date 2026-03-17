"""All event, tool-call, and session-meta parsers."""
from __future__ import annotations

import json, re, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import threading

from .models import UsageEvent, ToolCall, SessionMeta, TurnDuration, TaskEvent, CodeGenRecord, ScoredCommit

CODEX_ROOTS = [Path.home() / ".codex/archived_sessions", Path.home() / ".codex/sessions"]
CODEX_HOME = Path.home() / ".codex"
CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_ROOT = CLAUDE_HOME / "projects"
CURSOR_ROOT = Path.home() / ".cursor/projects"
CURSOR_DB = Path.home() / ".cursor/ai-tracking/ai-code-tracking.db"

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
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
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


# ── Codex: single-pass parser ─────────────────────────────────────────────
_ECR = re.compile(r"Process exited with code (\d+)")


def parse_codex_all(start_utc, now_utc):
    """Single-pass Codex parser: returns (events, tool_calls, session_metas, task_events, turn_durations)."""
    ses = defaultdict(list)
    calls = []
    metas, meta_seen = [], set()
    task_events = []
    turn_durations = []

    # SQLite meta + session durations (fast, separate source)
    for root in CODEX_ROOTS:
        db = root.parent / "codex.db"
        if db.exists():
            try:
                for r in sqlite3.connect(str(db)).execute(
                        "SELECT id,cwd,git_branch FROM threads").fetchall():
                    sid, cwd, br = str(r[0]), r[1], r[2]
                    metas.append(SessionMeta("Codex", sid, cwd,
                                             Path(cwd).name if cwd else None, br))
                    meta_seen.add(sid)
            except Exception:
                pass
    # state_5.sqlite has richer thread metadata
    state_db = CODEX_HOME / "state_5.sqlite"
    if state_db.exists():
        try:
            conn = sqlite3.connect(str(state_db))
            for r in conn.execute(
                    "SELECT id, cwd, git_branch, created_at, updated_at, tokens_used, source "
                    "FROM threads").fetchall():
                sid = str(r[0])
                if sid not in meta_seen:
                    cwd, br = r[1], r[2]
                    metas.append(SessionMeta("Codex", sid, cwd,
                                             Path(cwd).name if cwd else None, br))
                    meta_seen.add(sid)
                # Derive session duration as a TurnDuration (total session time)
                created, updated = r[3], r[4]
                if created and updated:
                    try:
                        t0 = _ts(created)
                        t1 = _ts(updated)
                        if t0 and t1 and t1 > t0 and start_utc <= t0 <= now_utc:
                            dur_ms = int((t1 - t0).total_seconds() * 1000)
                            if dur_ms > 0:
                                turn_durations.append(TurnDuration("Codex", t0, sid, dur_ms))
                    except Exception:
                        pass
            conn.close()
        except Exception:
            pass

    # Single iteration over each JSONL file
    for root in CODEX_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.jsonl"):
            sid, token_seen, model_name = None, {}, "GPT-5 Codex"
            pending_calls = {}
            file_has_meta = False

            for obj in _read_json_lines(path):
                obj_type = obj.get("type")
                pl = obj.get("payload") or {}

                # ── session_meta (shared by events + meta)
                if obj_type == "session_meta":
                    sid = str(pl.get("id") or path.stem)
                    if sid not in meta_seen:
                        cwd = pl.get("cwd")
                        metas.append(SessionMeta("Codex", sid, cwd,
                                                 Path(cwd).name if cwd else None,
                                                 pl.get("git_branch")))
                        meta_seen.add(sid)
                    file_has_meta = True
                    continue

                # ── turn_context (model tracking for events)
                if obj_type == "turn_context":
                    m = pl.get("model")
                    if isinstance(m, str) and m.strip():
                        model_name = m.strip()
                    cm = pl.get("collaboration_mode")
                    if isinstance(cm, dict):
                        ms = (cm.get("settings") or {}).get("model")
                        if isinstance(ms, str) and ms.strip():
                            model_name = ms.strip()
                    continue

                if obj_type != "event_msg":
                    continue

                pl_type = pl.get("type")
                ts = _ts(obj.get("timestamp"))
                if not ts:
                    continue
                s = sid or path.stem

                # ── token_count (events)
                if pl_type == "token_count":
                    u = (pl.get("info") or {}).get("total_token_usage")
                    if isinstance(u, dict):
                        cur = {"ts": ts, "input": _si(u.get("input_tokens")),
                               "cached": _si(u.get("cached_input_tokens")),
                               "output": _si(u.get("output_tokens")),
                               "reasoning": _si(u.get("reasoning_output_tokens")),
                               "model": model_name or "GPT-5 Codex"}
                        prev = token_seen.get(ts)
                        if prev is None or (cur["input"], cur["cached"], cur["output"], cur["reasoning"]) > (
                                prev["input"], prev["cached"], prev["output"], prev["reasoning"]):
                            token_seen[ts] = cur

                # ── response_item (tool calls)
                elif pl_type == "response_item":
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
                            pending_calls[cid] = tc
                        if start_utc <= ts <= now_utc:
                            calls.append(tc)
                    elif it == "function_call_output":
                        m = _ECR.search(str(item.get("output", "")))
                        cid = item.get("call_id", "")
                        if m and cid in pending_calls:
                            pending_calls[cid].exit_code = int(m.group(1))
                    elif it == "web_search_call":
                        if start_utc <= ts <= now_utc:
                            calls.append(ToolCall("Codex", ts, s, "web_search"))

                elif pl_type == "custom_tool_call":
                    cid = pl.get("id", "")
                    tc = ToolCall("Codex", ts, s, pl.get("name", "custom_tool"))
                    if cid:
                        pending_calls[cid] = tc
                    if start_utc <= ts <= now_utc:
                        calls.append(tc)

                elif pl_type == "custom_tool_call_output":
                    cid, md = pl.get("id", ""), pl.get("metadata")
                    if isinstance(md, dict) and cid in pending_calls:
                        ec = md.get("exit_code")
                        if ec is not None:
                            try:
                                pending_calls[cid].exit_code = int(ec)
                            except (ValueError, TypeError):
                                pass

                elif pl_type in ("task_started", "task_complete"):
                    if start_utc <= ts <= now_utc:
                        etype = "started" if pl_type == "task_started" else "complete"
                        task_events.append(TaskEvent("Codex", ts, s, etype))

            if token_seen:
                ses[sid or str(path)].extend(token_seen.values())

    # Build cumulative-delta events
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

    return events, calls, metas, task_events, turn_durations


# ── Claude: single-pass parser ────────────────────────────────────────────

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


def parse_claude_all(start_utc, now_utc):
    """Single-pass Claude parser: returns (events, tool_calls, session_metas, turn_durations)."""
    if not CLAUDE_ROOT.exists():
        return [], [], [], []

    event_dedup = {}
    calls = []
    metas, meta_seen = [], set()
    turn_durations = []

    for path in CLAUDE_ROOT.rglob("*.jsonl"):
        if path.name == "sessions-index.json":
            continue
        objs = _read_json_lines(path)

        # First pass for err_map (needed for tool call exit codes)
        err_map = {}
        for obj in objs:
            if obj.get("type") == "user":
                for blk in (obj.get("message") or {}).get("content") or []:
                    if isinstance(blk, dict) and blk.get("type") == "tool_result":
                        err_map[blk.get("tool_use_id", "")] = bool(blk.get("is_error"))

        # Main pass: extract events + tool_calls + session_meta simultaneously
        for obj in objs:
            obj_type = obj.get("type")

            # ── session meta (from "user" objects)
            if obj_type == "user":
                sid = str(obj.get("sessionId") or path.stem)
                if sid not in meta_seen:
                    meta_seen.add(sid)
                    cwd = obj.get("cwd")
                    br = obj.get("gitBranch")
                    proj = (Path(cwd).name if cwd and "/" in str(cwd)
                            else str(cwd).rsplit("-", 1)[-1] if cwd else None)
                    metas.append(SessionMeta("Claude", sid, cwd, proj, br))

            # ── turn duration (from "system" objects)
            if obj_type == "system" and obj.get("subtype") == "turn_duration":
                dur = obj.get("durationMs")
                ts = _ts(obj.get("timestamp"))
                if dur and ts and start_utc <= ts <= now_utc:
                    sid = str(obj.get("sessionId") or path.stem)
                    turn_durations.append(TurnDuration("Claude", ts, sid, int(dur)))

            # ── events (from messages with usage)
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
                prev = event_dedup.get(key)
                if prev is None or (ev.uncached_input, ev.cache_read, ev.cache_write, ev.output) > (
                        prev.uncached_input, prev.cache_read, prev.cache_write, prev.output):
                    event_dedup[key] = ev

            # ── tool calls (from assistant messages)
            msg = None
            if obj_type == "assistant":
                msg = obj.get("message", {})
            else:
                m = obj.get("message")
                if isinstance(m, dict) and m.get("role") == "assistant":
                    msg = m
            if not isinstance(msg, dict):
                continue
            ts = _ts(obj.get("timestamp"))
            if not ts or ts < start_utc or ts > now_utc:
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

    return list(event_dedup.values()), calls, metas, turn_durations


# ── Cursor parser (unchanged — already single-pass) ──────────────────────

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


# ── Cursor: AI code tracking DB ──────────────────────────────────────────

def parse_cursor_codegen(start_utc, now_utc):
    """Parse Cursor ai-code-tracking.db for code generation records and scored commits."""
    code_gen: list[CodeGenRecord] = []
    scored: list[ScoredCommit] = []
    if not CURSOR_DB.exists():
        return code_gen, scored
    try:
        conn = sqlite3.connect(str(CURSOR_DB))
        # ai_code_hashes
        for r in conn.execute(
                "SELECT timestamp, model, fileExtension, conversationId, source "
                "FROM ai_code_hashes WHERE timestamp IS NOT NULL").fetchall():
            try:
                ts_ms = int(r[0])
                ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                continue
            if ts < start_utc or ts > now_utc:
                continue
            model = r[1] or "unknown"
            ext = r[2] or ""
            cid = r[3] or ""
            src = r[4] or "composer"
            code_gen.append(CodeGenRecord("Cursor", ts, model, ext, cid, src))
        # scored_commits
        for r in conn.execute(
                "SELECT commitHash, commitDate, linesAdded, linesDeleted, "
                "composerLinesAdded, composerLinesDeleted, "
                "humanLinesAdded, humanLinesDeleted, "
                "tabLinesAdded, tabLinesDeleted "
                "FROM scored_commits").fetchall():
            commit_date = None
            if r[1]:
                try:
                    commit_date = _ts(r[1])
                except Exception:
                    pass
            if commit_date and (commit_date < start_utc or commit_date > now_utc):
                continue
            scored.append(ScoredCommit(
                commit_hash=r[0] or "",
                commit_date=commit_date,
                lines_added=_si(r[2]), lines_deleted=_si(r[3]),
                composer_added=_si(r[4]), composer_deleted=_si(r[5]),
                human_added=_si(r[6]), human_deleted=_si(r[7]),
                tab_added=_si(r[8]), tab_deleted=_si(r[9]),
            ))
        conn.close()
    except Exception:
        pass
    return code_gen, scored


# ── Claude: stats-cache.json ─────────────────────────────────────────────

def parse_claude_stats_cache():
    """Parse ~/.claude/stats-cache.json for daily activity and model token stats."""
    cache_path = CLAUDE_HOME / "stats-cache.json"
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}
    return {
        "daily_activity": raw.get("dailyActivity", []),
        "daily_model_tokens": raw.get("dailyModelTokens", []),
        "model_usage": raw.get("modelUsage", {}),
        "longest_session": raw.get("longestSession"),
        "hour_counts": raw.get("hourCounts", []),
        "total_sessions": raw.get("totalSessions", 0),
        "total_messages": raw.get("totalMessages", 0),
        "first_session_date": raw.get("firstSessionDate"),
    }


# ── Legacy wrappers (for backward compatibility) ─────────────────────────

def parse_codex_events(start_utc, now_utc):
    events, _, _, _, _ = parse_codex_all(start_utc, now_utc)
    return events


def parse_codex_tool_calls():
    _, calls, _, _, _ = parse_codex_all(datetime.min.replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc))
    return calls


def parse_codex_session_meta():
    _, _, metas, _, _ = parse_codex_all(datetime.min.replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc))
    return metas


def parse_claude_events(start_utc, now_utc):
    events, _, _, _ = parse_claude_all(start_utc, now_utc)
    return events


def parse_claude_tool_calls():
    _, calls, _, _ = parse_claude_all(datetime.min.replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc))
    return calls


def parse_claude_session_meta():
    _, _, metas, _ = parse_claude_all(datetime.min.replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc))
    return metas
