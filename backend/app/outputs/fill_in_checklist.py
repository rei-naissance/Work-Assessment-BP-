"""Fill-In Checklist Generator.

Produces a checklist of all UNKNOWN placeholders found during binder generation,
grouped by category with hints for how to find each piece of information.
"""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle,
)

from app.models.profile import Profile
from app.library.validation import PlaceholderRegistry
from app.templates.narrative import get_unknown_placeholders, clear_unknown_placeholders


@dataclass
class UnknownItem:
    """An unknown placeholder item for the checklist."""
    token: str
    label: str
    hint: str
    category: str
    category_id: str
    locations: list[str]  # Where it appeared (chapter/module)


def collect_unknowns_from_render() -> dict[str, UnknownItem]:
    """Collect unknown placeholders from the most recent render.

    Returns:
        Dict of token -> UnknownItem with metadata from registry.
    """
    registry = PlaceholderRegistry()
    unknowns = get_unknown_placeholders()

    items = {}
    for token in unknowns:
        items[token] = UnknownItem(
            token=token,
            label=registry.get_label(token),
            hint=registry.get_hint(token),
            category=registry.get_category(token),
            category_id=registry.get_category_id(token),
            locations=[],  # We'll enhance this later with module tracking
        )

    return items


def generate_fill_in_checklist(
    profile: Profile,
    output_path: str,
    unknowns: Optional[dict[str, UnknownItem]] = None,
    ai_missing_items: Optional[dict[str, list[str]]] = None,
) -> str:
    """Generate a fill-in checklist PDF.

    Args:
        profile: User profile (for header info).
        output_path: Path for output PDF.
        unknowns: Optional pre-collected unknowns. If None, collects from recent render.
        ai_missing_items: Optional AI-identified missing items per section.

    Returns:
        Path to generated PDF.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if unknowns is None:
        unknowns = collect_unknowns_from_render()

    # Group by category
    by_category: dict[str, list[UnknownItem]] = defaultdict(list)
    for item in unknowns.values():
        by_category[item.category].append(item)

    # Sort categories in preferred order
    category_order = ["Home & Access", "People", "Vendors", "Systems & Inventory", "Other"]

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "ChecklistTitle", parent=styles["Title"],
        fontSize=24, spaceAfter=16, textColor=HexColor("#1e3a5f"),
    ))
    styles.add(ParagraphStyle(
        "CategoryTitle", parent=styles["Heading1"],
        fontSize=16, spaceBefore=16, spaceAfter=8, textColor=HexColor("#1e3a5f"),
    ))
    styles.add(ParagraphStyle(
        "ItemLabel", parent=styles["BodyText"],
        fontSize=12, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "ItemHint", parent=styles["BodyText"],
        fontSize=10, textColor=HexColor("#6b7280"), leftIndent=20,
    ))
    styles.add(ParagraphStyle(
        "Checkbox", parent=styles["BodyText"],
        fontSize=12, spaceBefore=6,
    ))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    story = []

    # Title
    hi = profile.home_identity
    nickname = hi.home_nickname or "Home"
    story.append(Paragraph(f"{nickname} — Fill-In Checklist", styles["ChecklistTitle"]))
    story.append(Spacer(1, 8))

    if not unknowns:
        story.append(Paragraph(
            "All information is complete. No items to fill in.",
            styles["BodyText"]
        ))
    else:
        story.append(Paragraph(
            f"The following {len(unknowns)} items need to be filled in to complete your binder. "
            "Check off each item as you gather the information.",
            styles["BodyText"]
        ))
        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="100%", thickness=2, color=HexColor("#1e3a5f")))
        story.append(Spacer(1, 8))

        # Render by category
        for cat_name in category_order:
            items = by_category.get(cat_name, [])
            if not items:
                continue

            story.append(Paragraph(f"{cat_name} ({len(items)} items)", styles["CategoryTitle"]))

            for item in sorted(items, key=lambda x: x.label):
                # Checkbox + Label
                story.append(Paragraph(f"☐  {item.label}", styles["Checkbox"]))
                # Hint
                story.append(Paragraph(f"How to find: {item.hint}", styles["ItemHint"]))
                # Space for writing
                story.append(Paragraph(
                    "Your value: _________________________________________________",
                    styles["ItemHint"]
                ))
                story.append(Spacer(1, 8))

            story.append(Spacer(1, 12))

    # AI-identified missing items
    if ai_missing_items:
        all_ai_items = []
        for section_key, items in ai_missing_items.items():
            all_ai_items.extend(items)

        if all_ai_items:
            story.append(Spacer(1, 12))
            story.append(HRFlowable(width="100%", thickness=2, color=HexColor("#1e3a5f")))
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                f"AI-Identified Items ({len(all_ai_items)} items)",
                styles["CategoryTitle"]
            ))
            story.append(Paragraph(
                "These items were identified by AI analysis as missing or incomplete "
                "in your binder content.",
                styles["BodyText"]
            ))
            story.append(Spacer(1, 8))

            SECTION_LABELS = {
                "section_1": "Emergency Quick Start",
                "section_3": "Emergency Playbooks",
                "section_4": "Guest & Sitter Mode",
                "section_5": "Maintenance & Seasonal",
            }

            for section_key, items in ai_missing_items.items():
                if not items:
                    continue
                section_label = SECTION_LABELS.get(section_key, section_key)
                story.append(Paragraph(f"{section_label}:", styles["ItemLabel"]))
                for item in items:
                    story.append(Paragraph(f"☐  {item}", styles["Checkbox"]))
                    story.append(Paragraph(
                        "Your value: _________________________________________________",
                        styles["ItemHint"]
                    ))
                    story.append(Spacer(1, 6))
                story.append(Spacer(1, 8))

    # Footer
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#d1d5db")))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Once you've gathered this information, update your profile and regenerate your binder.",
        styles["BodyText"]
    ))

    doc.build(story)
    return output_path


def generate_fill_in_checklist_markdown(
    profile: Profile,
    unknowns: Optional[dict[str, UnknownItem]] = None,
) -> str:
    """Generate fill-in checklist as Markdown.

    Args:
        profile: User profile.
        unknowns: Optional pre-collected unknowns.

    Returns:
        Markdown string.
    """
    if unknowns is None:
        unknowns = collect_unknowns_from_render()

    # Group by category
    by_category: dict[str, list[UnknownItem]] = defaultdict(list)
    for item in unknowns.values():
        by_category[item.category].append(item)

    category_order = ["Home & Access", "People", "Vendors", "Systems & Inventory", "Other"]

    lines = []
    hi = profile.home_identity
    nickname = hi.home_nickname or "Home"

    lines.append(f"# {nickname} — Fill-In Checklist\n")

    if not unknowns:
        lines.append("All information is complete. No items to fill in.\n")
    else:
        lines.append(
            f"The following {len(unknowns)} items need to be filled in. "
            "Check off each item as you gather the information.\n"
        )
        lines.append("---\n")

        for cat_name in category_order:
            items = by_category.get(cat_name, [])
            if not items:
                continue

            lines.append(f"\n## {cat_name} ({len(items)} items)\n")

            for item in sorted(items, key=lambda x: x.label):
                lines.append(f"- [ ] **{item.label}**")
                lines.append(f"  - *How to find:* {item.hint}")
                lines.append(f"  - Your value: _______________")
                lines.append("")

    lines.append("\n---\n")
    lines.append(
        "*Once you've gathered this information, update your profile and regenerate your binder.*\n"
    )

    return "\n".join(lines)
