"""Project analysis: ranking, branches, file types."""

from __future__ import annotations

from collections import Counter, defaultdict

from ._context import AggContext
from .sessions import _active_sessions


def compute(ctx: AggContext) -> dict:
    active_sessions = _active_sessions(ctx)
    project_rollups = defaultdict(
        lambda: {"project": "", "sessions": 0, "total_tokens": 0, "cost": 0.0, "tool_calls": 0}
    )
    branch_activity = Counter()
    active_session_keys = {(s["source"], s["session_id"]) for s in active_sessions}

    for session in active_sessions:
        meta = ctx.session_meta_map.get((session["source"], session["session_id"]))
        project_name = (meta.project if meta else None) or "unknown"
        project = project_rollups[project_name]
        project["project"] = project_name
        project["sessions"] += 1
        project["total_tokens"] += session["total"]
        project["cost"] += session["cost"]
        project["tool_calls"] += session["tool_calls"]

    for key, meta in ctx.session_meta_map.items():
        if key in active_session_keys and meta.git_branch:
            branch_activity[meta.git_branch] += 1

    project_ranking = sorted(project_rollups.values(), key=lambda i: i["total_tokens"], reverse=True)[:20]

    return {
        "ranking": [
            {
                "project": i["project"],
                "sessions": i["sessions"],
                "total_tokens": i["total_tokens"],
                "cost": round(i["cost"], 4),
                "tool_calls": i["tool_calls"],
            }
            for i in project_ranking
        ],
        "branch_activity": [{"branch": b, "sessions": c} for b, c in branch_activity.most_common(20)],
        "file_types": [{"extension": e, "count": c} for e, c in ctx.file_types.most_common(20)],
        "count": len(project_rollups),
    }
