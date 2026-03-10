"""PDF generation using ReportLab -- 8-section home operating manual."""
from __future__ import annotations

import os
import re
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle, Flowable, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

from app.models.profile import Profile
from app.rules.engine import select_modules
from app.templates.narrative import TemplateWriter, Block

SECTION_TITLES = [
    "Emergency Quick Start",
    "Home Profile",
    "Emergency Playbooks",
    "Guest & Sitter Mode",
    "Maintenance & Seasonal Care",
    "Home Inventory & Checklists",
    "Contacts & Vendors",
    "Appendix",
]

# Color scheme
BRAND = HexColor("#1e3a5f")
BRAND_LIGHT = HexColor("#e8eef5")
BRAND_ACCENT = HexColor("#2563eb")
CALLOUT_BG = HexColor("#fff3cd")
TABLE_HEADER_BG = HexColor("#1e3a5f")
TABLE_HEADER_FG = HexColor("#ffffff")
TABLE_ALT_ROW = HexColor("#f5f7fa")
GRAY_600 = HexColor("#4b5563")
GRAY_400 = HexColor("#9ca3af")

# Formatting constants
SUBSTEP_INDENT = "     "  # Indentation for substeps in numbered lists

# Vertical spacing constants (points)
SPACE_SECTION = 16       # Before major sections
SPACE_SUBSECTION = 14    # Before subsections
SPACE_SUBSECTION3 = 10   # Before level-3 subheadings
SPACE_PARAGRAPH = 6      # Between paragraphs
SPACE_LIST_ITEM = 4      # Between list items
SPACE_AFTER_HEADING = 8  # After any heading
SPACE_BLOCK_GAP = 10     # Standard spacer block height
SPACE_CALLOUT_V = 8      # Vertical padding inside callouts

# Layout constants
PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 0.75 * inch
RIGHT_MARGIN = 0.75 * inch
TOP_MARGIN = 0.85 * inch
BOTTOM_MARGIN = 0.85 * inch
AVAIL_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN  # ~7.0 inches


class SectionTracker(Flowable):
    """Invisible flowable that updates the current section name for page headers."""

    def __init__(self, section_name: str):
        Flowable.__init__(self)
        self.section_name = section_name
        self.width = 0
        self.height = 0

    def draw(self):
        self.canv._current_section = self.section_name


def draw_cover_page(canvas, profile: Profile):
    """Draw a professional cover page directly on the canvas."""
    from reportlab.lib.pagesizes import letter

    c = canvas
    hi = profile.home_identity
    h = profile.household

    page_width, page_height = letter

    # === TOP BANNER (navy background) ===
    banner_height = 2.2 * inch
    c.setFillColor(BRAND)
    c.rect(0, page_height - banner_height, page_width, banner_height, fill=1, stroke=0)

    # House icon (simple geometric)
    icon_x = page_width / 2
    icon_y = page_height - 0.9 * inch
    c.setFillColor(white)
    c.setStrokeColor(white)
    # Roof triangle
    c.setLineWidth(2)
    roof_size = 0.35 * inch
    c.line(icon_x - roof_size, icon_y - roof_size * 0.6,
           icon_x, icon_y + roof_size * 0.4)
    c.line(icon_x, icon_y + roof_size * 0.4,
           icon_x + roof_size, icon_y - roof_size * 0.6)
    # House body
    c.rect(icon_x - roof_size * 0.7, icon_y - roof_size * 1.2,
           roof_size * 1.4, roof_size * 0.7, fill=0, stroke=1)

    # Title text
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 32)
    nickname = hi.home_nickname or "Your Home"
    c.drawCentredString(page_width / 2, page_height - 1.6 * inch, nickname)

    c.setFont("Helvetica", 14)
    c.drawCentredString(page_width / 2, page_height - 1.95 * inch, "Operating Manual")

    # === ADDRESS SECTION ===
    y = page_height - banner_height - 0.6 * inch

    c.setFillColor(BRAND)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(page_width / 2, y, "PROPERTY ADDRESS")

    y -= 0.35 * inch
    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica", 16)
    address = hi.address_line1 or ""
    c.drawCentredString(page_width / 2, y, address)

    y -= 0.3 * inch
    city_state_zip = ", ".join(filter(None, [hi.city, hi.state])) + (f" {hi.zip_code}" if hi.zip_code else "")
    c.drawCentredString(page_width / 2, y, city_state_zip)

    # === PROPERTY DETAILS BOX ===
    y -= 0.7 * inch
    box_width = 5 * inch
    box_height = 1.6 * inch
    box_x = (page_width - box_width) / 2

    # Box background
    c.setFillColor(BRAND_LIGHT)
    c.setStrokeColor(BRAND)
    c.setLineWidth(1)
    c.roundRect(box_x, y - box_height, box_width, box_height, 8, fill=1, stroke=1)

    # Property details in 2 columns
    col1_x = box_x + 0.4 * inch
    col2_x = box_x + box_width / 2 + 0.2 * inch
    row_y = y - 0.35 * inch
    row_height = 0.35 * inch

    details = [
        ("Home Type", (hi.home_type or "").replace("_", " ").title() or "\u2014"),
        ("Year Built", str(hi.year_built) if hi.year_built else "\u2014"),
        ("Square Feet", f"{hi.square_feet:,}" if hi.square_feet else "\u2014"),
        ("Status", "Owner" if hi.owner_renter == "owner" else "Renter"),
    ]

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GRAY_600)

    for i, (label, value) in enumerate(details):
        x = col1_x if i % 2 == 0 else col2_x
        if i == 2:
            row_y -= row_height
        c.drawString(x, row_y, label.upper())
        c.setFont("Helvetica", 12)
        c.setFillColor(HexColor("#111827"))
        c.drawString(x, row_y - 0.2 * inch, value)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(GRAY_600)

    # === HOUSEHOLD INFO (if applicable) ===
    y = y - box_height - 0.5 * inch

    household_parts = []
    if h.num_adults:
        household_parts.append(f"{h.num_adults} Adult{'s' if h.num_adults > 1 else ''}")
    if h.num_children:
        household_parts.append(f"{h.num_children} Child{'ren' if h.num_children > 1 else ''}")
    if h.has_pets and h.pet_types:
        household_parts.append(f"Pets: {h.pet_types}")
    elif h.has_pets:
        household_parts.append("Pets")

    if household_parts:
        c.setFont("Helvetica", 10)
        c.setFillColor(GRAY_600)
        c.drawCentredString(page_width / 2, y, "Household: " + " \u2022 ".join(household_parts))

    # === BOTTOM INFO ===
    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY_400)
    c.drawCentredString(page_width / 2, 1.2 * inch,
                       f"Generated {datetime.now().strftime('%B %d, %Y')}")

    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(page_width / 2, 0.9 * inch,
                       "Keep this binder in an accessible location for all household members.")

    # Bottom accent line
    c.setStrokeColor(BRAND)
    c.setLineWidth(3)
    c.line(page_width / 2 - 1 * inch, 0.5 * inch,
           page_width / 2 + 1 * inch, 0.5 * inch)


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "CoverTitle", parent=styles["Title"],
        fontSize=28, spaceAfter=20, textColor=BRAND,
    ))
    styles.add(ParagraphStyle(
        "SectionNumber", parent=styles["Heading1"],
        fontSize=14, spaceBefore=0, spaceAfter=2,
        textColor=HexColor("#6b7280"),
    ))
    styles.add(ParagraphStyle(
        "SectionTitle", parent=styles["Heading1"],
        fontSize=20, spaceBefore=SPACE_SECTION // 4, spaceAfter=SPACE_AFTER_HEADING + 4,
        textColor=BRAND,
    ))
    styles.add(ParagraphStyle(
        "SubsectionTitle", parent=styles["Heading2"],
        fontSize=14, spaceBefore=SPACE_SUBSECTION, spaceAfter=SPACE_AFTER_HEADING,
        textColor=BRAND,
    ))
    styles.add(ParagraphStyle(
        "SubsectionTitle3", parent=styles["Heading3"],
        fontSize=12, spaceBefore=SPACE_SUBSECTION3, spaceAfter=SPACE_LIST_ITEM,
        textColor=HexColor("#374151"),
    ))
    styles.add(ParagraphStyle(
        "StepItem", parent=styles["BodyText"],
        fontSize=11, leftIndent=24, spaceBefore=SPACE_LIST_ITEM, spaceAfter=SPACE_LIST_ITEM,
        leading=15, wordWrap='CJK',
    ))
    styles.add(ParagraphStyle(
        "CalloutText", parent=styles["BodyText"],
        fontSize=11, spaceBefore=SPACE_PARAGRAPH, spaceAfter=SPACE_PARAGRAPH,
        backColor=CALLOUT_BG, borderPadding=8,
        fontName="Helvetica-Bold",
        leading=15, leftIndent=8, wordWrap='CJK',
    ))
    styles.add(ParagraphStyle(
        "ChecklistItem", parent=styles["BodyText"],
        fontSize=11, leftIndent=24, spaceBefore=3, spaceAfter=3,
        bulletIndent=10, bulletFontSize=10,
        leading=15, wordWrap='CJK',
    ))
    styles.add(ParagraphStyle(
        "TableCell", parent=styles["BodyText"],
        fontSize=10, spaceBefore=1, spaceAfter=1,
        leading=13, wordWrap='CJK',
    ))
    styles.add(ParagraphStyle(
        "TableHeader", parent=styles["BodyText"],
        fontSize=10, spaceBefore=1, spaceAfter=1,
        textColor=TABLE_HEADER_FG, fontName="Helvetica-Bold",
        leading=13,
    ))
    styles.add(ParagraphStyle(
        "TOCEntry", parent=styles["BodyText"],
        fontSize=12, spaceBefore=4, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "AIText", parent=styles["BodyText"],
        fontSize=11, fontName="Helvetica-Oblique",
        leftIndent=8, borderPadding=4,
        textColor=HexColor("#374151"), wordWrap='CJK',
    ))
    styles.add(ParagraphStyle(
        "AICallout", parent=styles["CalloutText"],
        fontName="Helvetica-Oblique",
        backColor=HexColor("#e8f4f8"),
    ))
    # Override default BodyText to include wordWrap
    styles["BodyText"].wordWrap = 'CJK'
    return styles


def _safe_text(text: str) -> str:
    """Escape text for safe use in ReportLab Paragraph XML markup.

    Escapes <, >, &, and quotes to prevent XML parsing errors.
    Then converts markdown-style **bold** to ReportLab <b> tags.
    This is critical for user-provided content that may contain special characters.
    """
    if not text:
        return ""
    escaped = xml_escape(str(text), entities={'"': '&quot;', "'": '&apos;'})
    # Convert markdown bold **text** to ReportLab XML bold <b>text</b>
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped)
    return escaped


def _plain_text(cell) -> str:
    """Extract plain text from a Paragraph or string for length measurement."""
    if isinstance(cell, str):
        return cell
    if hasattr(cell, 'text'):
        return re.sub(r'<[^>]+>', '', cell.text if isinstance(cell.text, str) else '')
    return str(cell)


def _compute_col_widths(data: list[list], avail_width: float) -> list[float]:
    """Compute column widths proportional to content length.

    - 2-column label-value tables get a ~30/70 split
    - General tables get proportional sizing with min/max constraints
    - Total always sums to avail_width
    """
    if not data:
        return []

    col_count = len(data[0])
    MIN_COL = 0.8 * inch
    MAX_COL = 4.5 * inch

    # Detect label-value pattern (2 columns, short left, long right)
    if col_count == 2:
        col0_max = max(len(_plain_text(row[0])) for row in data)
        col1_max = max(len(_plain_text(row[1])) for row in data)
        if col0_max < 25 and col1_max > col0_max:
            label_width = min(2.2 * inch, max(1.5 * inch, col0_max * 0.09 * inch))
            return [label_width, avail_width - label_width]

    # General proportional sizing
    col_lengths = []
    for ci in range(col_count):
        max_len = 0
        for row in data:
            if ci < len(row):
                text_len = len(_plain_text(row[ci]))
                max_len = max(max_len, text_len)
        col_lengths.append(max(max_len, 1))

    total = sum(col_lengths)
    raw_widths = [(l / total) * avail_width for l in col_lengths]

    # Clamp to min/max
    widths = [max(MIN_COL, min(MAX_COL, w)) for w in raw_widths]

    # Normalize to fill available width
    scale = avail_width / sum(widths)
    return [w * scale for w in widths]


def _render_single_block(block: Block, styles, avail_width: float = AVAIL_WIDTH) -> list:
    """Render a single Block to a list of flowables (no KeepTogether wrapping).

    Used by the KeepTogether grouping logic to preview-render a block
    for inclusion with its preceding heading.
    """
    flowables = []

    if block.type == "paragraph":
        style = styles["AIText"] if block.ai_generated else styles["BodyText"]
        flowables.append(Paragraph(_safe_text(block.text), style))

    elif block.type == "callout_box":
        style = styles["AICallout"] if block.ai_generated else styles["CalloutText"]
        callout_para = Paragraph(_safe_text(block.text), style)
        accent_color = HexColor("#3b82f6") if block.ai_generated else HexColor("#d97706")
        callout_table = Table([[callout_para]], colWidths=[avail_width])
        callout_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), SPACE_CALLOUT_V),
            ("BOTTOMPADDING", (0, 0), (-1, -1), SPACE_CALLOUT_V),
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fefce8") if not block.ai_generated else HexColor("#eff6ff")),
            ("LINEBEFOREDECAY", (0, 0), (0, -1), 3, accent_color),
            ("LINEBEFORE", (0, 0), (0, -1), 3, accent_color),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
        ]))
        flowables.append(callout_table)

    elif block.type == "numbered_list":
        step_num = 0
        for item in block.items:
            safe_item = _safe_text(item.strip())
            is_substep = item.strip().startswith("\u2022") or item.strip().startswith("    \u2022")
            if is_substep:
                flowables.append(Paragraph(f"{SUBSTEP_INDENT}{safe_item}", styles["StepItem"]))
            else:
                step_num += 1
                flowables.append(Paragraph(f"<b>{step_num}.</b>  {safe_item}", styles["StepItem"]))

    elif block.type == "checklist":
        for item in block.items:
            flowables.append(Paragraph(f"\u2610  {_safe_text(item)}", styles["ChecklistItem"]))

    elif block.type == "table":
        data = []
        if block.headers:
            data.append([Paragraph(_safe_text(h), styles["TableHeader"]) for h in block.headers])
        for row in block.rows:
            data.append([Paragraph(_safe_text(str(cell)), styles["TableCell"]) for cell in row])
        if data:
            col_widths = _compute_col_widths(data, avail_width)
            t = Table(data, colWidths=col_widths, repeatRows=1 if block.headers else 0)
            style_cmds = [
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
            if block.headers:
                style_cmds.append(("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG))
                for ri in range(1, len(data)):
                    if ri % 2 == 0:
                        style_cmds.append(("BACKGROUND", (0, ri), (-1, ri), TABLE_ALT_ROW))
            t.setStyle(TableStyle(style_cmds))
            flowables.append(t)

    elif block.type == "spacer":
        flowables.append(Spacer(1, SPACE_BLOCK_GAP))

    return flowables


def render_blocks(blocks: list[Block], styles, avail_width: float = AVAIL_WIDTH) -> list:
    """Convert Block objects to ReportLab flowables."""
    story = []
    i = 0
    while i < len(blocks):
        block = blocks[i]

        if block.type == "heading":
            safe_text = _safe_text(block.text)
            story.append(Paragraph(safe_text, styles["CoverTitle"] if block.level == 1 else styles["SectionTitle"]))

        elif block.type == "subheading":
            style = styles["SubsectionTitle"] if block.level <= 2 else styles["SubsectionTitle3"]
            safe_text = _safe_text(block.text)
            heading_para = Paragraph(safe_text, style)

            # KeepTogether: heading + first content block to prevent orphaned headings
            keep_group = [heading_para]

            # Look ahead: skip spacers, grab first content block
            lookahead = i + 1
            skipped_spacers = 0
            while lookahead < len(blocks) and blocks[lookahead].type == "spacer":
                keep_group.append(Spacer(1, SPACE_BLOCK_GAP))
                lookahead += 1
                skipped_spacers += 1

            consumed_next = False
            if lookahead < len(blocks):
                next_block = blocks[lookahead]
                # Keep heading with next content block if it's small enough
                if next_block.type in ("paragraph", "callout_box"):
                    next_flowables = _render_single_block(next_block, styles, avail_width)
                    keep_group.extend(next_flowables)
                    consumed_next = True
                elif next_block.type == "table" and len(next_block.rows) <= 8:
                    next_flowables = _render_single_block(next_block, styles, avail_width)
                    keep_group.extend(next_flowables)
                    consumed_next = True
                elif next_block.type in ("checklist", "numbered_list") and len(next_block.items) <= 5:
                    next_flowables = _render_single_block(next_block, styles, avail_width)
                    keep_group.extend(next_flowables)
                    consumed_next = True
                elif next_block.type not in ("page_break", "subheading", "heading"):
                    # Large content: just keep heading with a small spacer
                    keep_group.append(Spacer(1, 6))

            story.append(KeepTogether(keep_group))

            if consumed_next:
                i = lookahead  # skip the block we consumed
            elif skipped_spacers:
                i = lookahead - 1  # skip the spacers we consumed

        elif block.type == "paragraph":
            style = styles["AIText"] if block.ai_generated else styles["BodyText"]
            safe_text = _safe_text(block.text)
            story.append(Paragraph(safe_text, style))

        elif block.type == "numbered_list":
            list_items = []
            step_num = 0
            for item in block.items:
                safe_item = _safe_text(item.strip())
                is_substep = item.strip().startswith("\u2022") or item.strip().startswith("    \u2022")
                if is_substep:
                    list_items.append(Paragraph(f"{SUBSTEP_INDENT}{safe_item}", styles["StepItem"]))
                else:
                    step_num += 1
                    list_items.append(Paragraph(f"<b>{step_num}.</b>  {safe_item}", styles["StepItem"]))
            # Keep at least first 3 items together to avoid awkward page breaks
            if len(list_items) >= 3:
                story.append(KeepTogether(list_items[:3]))
                story.extend(list_items[3:])
            else:
                story.append(KeepTogether(list_items))

        elif block.type == "callout_box":
            style = styles["AICallout"] if block.ai_generated else styles["CalloutText"]
            safe_text = _safe_text(block.text)
            callout_para = Paragraph(safe_text, style)
            accent_color = HexColor("#3b82f6") if block.ai_generated else HexColor("#d97706")
            callout_table = Table([[callout_para]], colWidths=[avail_width])
            callout_table.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), SPACE_CALLOUT_V),
                ("BOTTOMPADDING", (0, 0), (-1, -1), SPACE_CALLOUT_V),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fefce8") if not block.ai_generated else HexColor("#eff6ff")),
                ("LINEBEFOREDECAY", (0, 0), (0, -1), 3, accent_color),
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent_color),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
            ]))
            story.append(callout_table)

        elif block.type == "checklist":
            checklist_items = []
            for item in block.items:
                safe_item = _safe_text(item)
                checklist_items.append(Paragraph(f"\u2610  {safe_item}", styles["ChecklistItem"]))
            # Keep checklist items together if reasonable
            if len(checklist_items) <= 5:
                story.append(KeepTogether(checklist_items))
            else:
                story.extend(checklist_items)

        elif block.type == "table":
            data = []
            if block.headers:
                data.append([Paragraph(_safe_text(h), styles["TableHeader"]) for h in block.headers])
            for row in block.rows:
                data.append([Paragraph(_safe_text(str(cell)), styles["TableCell"]) for cell in row])
            if data:
                col_widths = _compute_col_widths(data, avail_width)
                t = Table(data, colWidths=col_widths, repeatRows=1 if block.headers else 0)
                style_cmds = [
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
                if block.headers:
                    style_cmds.append(("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG))
                    for ri in range(1, len(data)):
                        if ri % 2 == 0:
                            style_cmds.append(("BACKGROUND", (0, ri), (-1, ri), TABLE_ALT_ROW))
                t.setStyle(TableStyle(style_cmds))
                # Only KeepTogether for small tables
                if len(data) <= 8:
                    story.append(KeepTogether([t]))
                else:
                    story.append(t)

        elif block.type == "spacer":
            story.append(Spacer(1, SPACE_BLOCK_GAP))
        elif block.type == "page_break":
            story.append(PageBreak())

        i += 1
    return story


def generate_binder_pdf(
    profile: Profile,
    output_path: str,
    tier: str = "premium",
    ai_content: dict | None = None,
    section_blocks: dict[str, list[Block]] | None = None,
) -> str:
    """Generate a PDF binder and return the file path.

    Args:
        section_blocks: Pre-rendered (and optionally AI-enhanced) blocks per section.
                        When provided, skips TemplateWriter rendering.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
    )

    styles = _build_styles()
    writer = TemplateWriter()
    sections = select_modules(profile, tier=tier)

    # Create callback for cover page (draws directly on canvas with absolute coords)
    def first_page_callback(canvas, doc):
        draw_cover_page(canvas, profile)

    def later_pages_callback(canvas, doc):
        """Draw page numbers and running section header on content pages."""
        page_num = doc.page

        # Skip footer on cover page (page 1) and TOC (page 2)
        if page_num <= 2:
            return

        canvas.saveState()

        # Footer: centered page number
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(GRAY_400)
        canvas.drawCentredString(PAGE_WIDTH / 2, 0.4 * inch, f"Page {page_num - 2}")

        # Footer: branding right
        canvas.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, 0.4 * inch, "MyBinderPro.com")

        # Header: section name + separator line
        section_name = getattr(canvas, '_current_section', '')
        if section_name:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(GRAY_400)
            canvas.drawString(LEFT_MARGIN, PAGE_HEIGHT - 0.5 * inch, section_name)
            canvas.setStrokeColor(HexColor("#e5e7eb"))
            canvas.setLineWidth(0.5)
            canvas.line(LEFT_MARGIN, PAGE_HEIGHT - 0.55 * inch,
                       PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - 0.55 * inch)

        canvas.restoreState()

    story = []

    # -- Cover page is drawn via callback, just add a page break to move to next page --
    story.append(PageBreak())

    # -- Table of Contents --
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Table of Contents", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND))
    story.append(Spacer(1, 0.3 * inch))

    toc_data = []
    for i, title in enumerate(SECTION_TITLES, 1):
        toc_data.append([
            Paragraph(f"<b>{i}</b>", styles["TOCEntry"]),
            Paragraph(title, styles["TOCEntry"]),
        ])

    toc_table = Table(toc_data, colWidths=[0.5 * inch, 6 * inch])
    toc_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # -- Section methods mapped to section data keys --
    ac = ai_content
    section_map = [
        (lambda m, p: writer.write_quick_start(m, p, ai_content=ac), "section_1"),
        (lambda m, p: writer.write_home_profile(p, ai_content=ac), "section_2"),
        (lambda m, p: writer.write_playbooks(m, p, ai_content=ac), "section_3"),
        (lambda m, p: writer.write_guest_mode(p, ai_content=ac), "section_4"),
        (lambda m, p: writer.write_maintenance(m, p, ai_content=ac), "section_5"),
        (lambda m, p: writer.write_inventory(m, p, ai_content=ac), "section_6"),
        (lambda m, p: writer.write_contacts(p, ai_content=ac), "section_7"),
        (lambda m, p: writer.write_appendix(sections, p, ai_content=ac), "section_8"),
    ]

    for i, (method, section_key) in enumerate(section_map):
        section_num = i + 1
        title = SECTION_TITLES[i]

        # Track section name for running headers
        story.append(SectionTracker(f"Section {section_num}: {title}"))

        # Section header
        story.append(Paragraph(f"Section {section_num}", styles["SectionNumber"]))
        story.append(Paragraph(title, styles["SectionTitle"]))
        story.append(HRFlowable(width="100%", thickness=2, color=BRAND))
        story.append(Spacer(1, 12))

        # Section content — use pre-enhanced blocks if available
        if section_blocks and section_key in section_blocks:
            blocks = section_blocks[section_key]
        else:
            section_data = sections.get(section_key, {})
            blocks = method(section_data, profile)
        story += render_blocks(blocks, styles, avail_width=AVAIL_WIDTH)
        story.append(PageBreak())

    doc.build(story, onFirstPage=first_page_callback, onLaterPages=later_pages_callback)
    return output_path
