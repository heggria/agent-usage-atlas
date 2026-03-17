"""Cursor log parser."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..models import CodeGenRecord, ParseResult, ScoredCommit, UsageEvent
from ._base import _read_json_lines, _si, _ts

CURSOR_ROOT = Path.home() / ".cursor/projects"
CURSOR_DB = Path.home() / ".cursor/ai-tracking/ai-code-tracking.db"


def parse(start_utc, now_utc, local_tz=None) -> ParseResult:
    """Parse Cursor agent transcripts and AI code tracking DB."""
    events = []
    if CURSOR_ROOT.exists():
        for path in CURSOR_ROOT.rglob("*.jsonl"):
            if "agent-transcripts" not in str(path):
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=local_tz or timezone.utc).astimezone(
                    timezone.utc
                )
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

    code_gen, scored = _parse_codegen(start_utc, now_utc)

    return ParseResult(
        events=events,
        code_gen=code_gen,
        scored_commits=scored,
    )


def _parse_codegen(start_utc, now_utc):
    """Parse Cursor ai-code-tracking.db for code generation records and scored commits."""
    code_gen: list[CodeGenRecord] = []
    scored: list[ScoredCommit] = []
    if not CURSOR_DB.exists():
        return code_gen, scored
    try:
        conn = sqlite3.connect(str(CURSOR_DB))
        for r in conn.execute(
            "SELECT timestamp, model, fileExtension, conversationId, source "
            "FROM ai_code_hashes WHERE timestamp IS NOT NULL"
        ).fetchall():
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
        for r in conn.execute(
            "SELECT commitHash, commitDate, linesAdded, linesDeleted, "
            "composerLinesAdded, composerLinesDeleted, "
            "humanLinesAdded, humanLinesDeleted, "
            "tabLinesAdded, tabLinesDeleted "
            "FROM scored_commits"
        ).fetchall():
            commit_date = None
            if r[1]:
                try:
                    commit_date = _ts(r[1])
                except Exception:
                    pass
            if commit_date and (commit_date < start_utc or commit_date > now_utc):
                continue
            scored.append(
                ScoredCommit(
                    commit_hash=r[0] or "",
                    commit_date=commit_date,
                    lines_added=_si(r[2]),
                    lines_deleted=_si(r[3]),
                    composer_added=_si(r[4]),
                    composer_deleted=_si(r[5]),
                    human_added=_si(r[6]),
                    human_deleted=_si(r[7]),
                    tab_added=_si(r[8]),
                    tab_deleted=_si(r[9]),
                )
            )
        conn.close()
    except Exception:
        pass
    return code_gen, scored
