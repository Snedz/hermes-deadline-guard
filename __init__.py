"""deadline-guard — Hermes plugin for markdown deadline tables and receipt-gated submit."""

from __future__ import annotations

import logging
from pathlib import Path

import schemas
import tools

LOG = logging.getLogger(__name__)


def register(ctx) -> None:
    root = Path(__file__).resolve().parent

    def get_config(key: str, default=None):
        return ctx.get_config(key, default)

    for name, schema in schemas.TOOLS.items():
        ctx.register_tool(
            name=name,
            schema=schema,
            handler=lambda args, _name=name, **_kw: tools.handle(_name, args, get_config),
            toolset="deadline-guard",
        )

    try:
        ctx.register_automation_blueprint(
            "daily-check",
            title="Deadline Guard daily scan",
            description=(
                "Scan the configured deadlines markdown table and summarize ERROR/WARN lines "
                "plus founder steps due in the next 48 hours."
            ),
            schedule_template="0 8 * * *",
            prompt_template=(
                "Use check_deadlines on the configured deadlines table, then next_founder_steps "
                "with within_hours=48. Post a short summary if anything is ERROR or WARN."
            ),
            category="automation",
            tags=["deadlines", "deadline-guard"],
        )
    except Exception as exc:  # older Hermes builds may lack blueprint registration
        LOG.debug("deadline-guard: automation blueprint skipped: %s", exc)

    skill = root / "skills" / "deadline-guard" / "SKILL.md"
    if skill.is_file():
        try:
            ctx.register_skill("deadline-guard", skill)
        except Exception as exc:
            LOG.debug("deadline-guard: skill registration skipped: %s", exc)
