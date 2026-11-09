"""JSON schemas for deadline-guard Hermes tools."""

CHECK_DEADLINES = {
    "name": "check_deadlines",
    "description": (
        "Scan a local markdown deadlines table (DEADLINES.md-style). Returns ERROR and WARN "
        "counts plus line items: missing owners are errors; missing founder-step dates, "
        "past-due open rows, and founder steps due within 3 days are warnings. "
        "Includes open_row_count for open statuses."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Optional path to the markdown file. Defaults to plugin config deadlines_path "
                    "or examples/hackathon-deadlines.md."
                ),
            },
            "today": {
                "type": "string",
                "description": "Optional ISO date YYYY-MM-DD for deterministic checks (tests/demos).",
            },
        },
    },
}

NEXT_FOUNDER_STEPS = {
    "name": "next_founder_steps",
    "description": (
        "List open rows whose founder-step-by date falls within the next N hours and whose "
        "status is not already founder-done or submitted."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "within_hours": {
                "type": "integer",
                "description": "Look-ahead window in hours (default 48).",
            },
            "path": {"type": "string", "description": "Optional deadlines markdown path."},
            "today": {"type": "string", "description": "Optional ISO date YYYY-MM-DD."},
        },
    },
}

PROPOSE_STATUS_UPDATE = {
    "name": "propose_status_update",
    "description": (
        "Validate a proposed status change for one row by item name. Refuses submitted / "
        "submission confirmed without an http(s) receipt_url. Does not write the file."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "row": {"type": "string", "description": "Item column text (substring match allowed)."},
            "status": {"type": "string", "description": "Proposed new status cell value."},
            "receipt_url": {
                "type": "string",
                "description": "Required when status implies submission (http or https URL).",
            },
            "path": {"type": "string", "description": "Optional deadlines markdown path."},
        },
        "required": ["row", "status"],
    },
}

DEADLINE_GUARD_CRON = {
    "name": "deadline_guard_cron",
    "description": (
        "Unattended cron helper: run check_deadlines and return a one-screen summary. "
        "Action run executes immediately; action install writes a stdlib script under "
        "HERMES_HOME/scripts for hermes cron --script."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["run", "install"]},
            "path": {"type": "string", "description": "Optional deadlines markdown path."},
            "today": {"type": "string", "description": "Optional ISO date YYYY-MM-DD."},
        },
        "required": ["action"],
    },
}

TOOLS = {
    "check_deadlines": CHECK_DEADLINES,
    "next_founder_steps": NEXT_FOUNDER_STEPS,
    "propose_status_update": PROPOSE_STATUS_UPDATE,
    "deadline_guard_cron": DEADLINE_GUARD_CRON,
}
