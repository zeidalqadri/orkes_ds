"""Bloomberg terminal palette and status color map."""

from rich.console import Console
from rich.theme import Theme

HARGA_THEME = Theme({
    # Structural
    "header":        "bold bright_cyan",
    "header.sub":    "cyan",
    "header.dim":    "dim cyan",
    "label":         "bold white",
    "dim":           "dim white",
    "muted":         "bright_black",

    # Data types
    "amount":        "bold bright_green",
    "amount.zero":   "dim white",
    "id":            "bright_yellow",
    "reference":     "bright_yellow",
    "title":         "white",
    "entity":        "bright_magenta",
    "entity.slug":   "bright_magenta",
    "entity.label":  "dim magenta",
    "date":          "white",
    "date.urgent":   "bold bright_red",
    "date.soon":     "bold bright_yellow",
    "date.safe":     "green",
    "date.past":     "dim red",

    # Status — v9 bid lifecycle
    "status.open":       "bold bright_green",
    "status.active":     "bold bright_green",
    "status.draft":      "dim white",
    "status.priced":     "bright_cyan",
    "status.in_progress":"bold bright_yellow",
    "status.submitted":  "bold bright_blue",
    "status.won":        "bold bright_green on green",
    "status.lost":       "dim red",
    "status.overdue":    "bold bright_red",
    "status.closed":     "dim red",
    "status.withdrawn":  "dim yellow",
    "status.nobid":      "dim white",
    "status.deleted":    "dim bright_black",
    "status.pending":    "dim cyan",

    # Workflow phases — v9 bid pipeline
    "phase.pricing":     "bright_yellow",
    "phase.approval":    "bright_cyan",
    "phase.packaging":   "bright_magenta",
    "phase.submitted":   "bright_blue",
    "phase.post_submit": "dim green",

    # Platform badges — ePerolehan, ForSAH, eTimad
    "platform.eperolehan": "bright_blue",
    "platform.forsah":     "bright_magenta",
    "platform.etimad":     "bright_yellow",

    # Levers (margin components)
    "lever.markup":      "bright_green",
    "lever.overhead":    "bright_yellow",
    "lever.contingency": "bright_cyan",
    "lever.risk":        "bright_red",

    # Summary bar
    "summary.count":  "bold bright_white",
    "summary.label":  "dim white",
    "summary.timing": "dim cyan",

    # Alerts
    "alert.high":  "bold bright_red",
    "alert.mid":   "bold bright_yellow",
    "alert.low":   "dim white",
})

STATUS_STYLE_MAP = {
    "open":        "status.open",
    "active":      "status.active",
    "draft":       "status.draft",
    "priced":      "status.priced",
    "in_progress": "status.in_progress",
    "submitted":   "status.submitted",
    "won":         "status.won",
    "lost":        "status.lost",
    "overdue":     "status.overdue",
    "closed":      "status.closed",
    "withdrawn":   "status.withdrawn",
    "nobid":       "status.nobid",
    "deleted":     "status.deleted",
    "pending":     "status.pending",
}

PLATFORM_STYLE_MAP = {
    "eperolehan": "platform.eperolehan",
    "forsah":     "platform.forsah",
    "etimad":     "platform.etimad",
}

PHASE_STYLE_MAP = {
    "pricing":      "phase.pricing",
    "approval":     "phase.approval",
    "packaging":    "phase.packaging",
    "submitted":    "phase.submitted",
    "post_submit":  "phase.post_submit",
}

console = Console(theme=HARGA_THEME)
