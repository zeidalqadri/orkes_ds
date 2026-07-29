"""Entity configuration command (list and notify settings)."""

from ..db import query_entities, set_entity_notification
from ..formatters import format_entities
from ..theme import console


def handle_entities_list(as_json: bool = False) -> None:
    entities = query_entities()
    data = {"entities": entities}
    format_entities(data, as_json=as_json)


def handle_entities_config(entity_slug: str, channel: str) -> None:
    set_entity_notification(entity_slug, channel)
    console.print(f"[green]Updated {entity_slug} \u2192 {channel}[/green]")
