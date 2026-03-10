"""Output builders for binder, sitter packet, and fill-in checklist.

Usage:
    from app.outputs import (
        generate_sitter_packet,
        generate_fill_in_checklist,
        collect_unknowns_from_render,
    )
"""

from app.outputs.sitter_packet import (
    generate_sitter_packet,
    generate_sitter_packet_markdown,
)
from app.outputs.fill_in_checklist import (
    generate_fill_in_checklist,
    generate_fill_in_checklist_markdown,
    collect_unknowns_from_render,
    UnknownItem,
)

__all__ = [
    "generate_sitter_packet",
    "generate_sitter_packet_markdown",
    "generate_fill_in_checklist",
    "generate_fill_in_checklist_markdown",
    "collect_unknowns_from_render",
    "UnknownItem",
]
