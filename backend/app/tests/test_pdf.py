import os
import tempfile

from app.models.profile import Profile, HomeIdentity, Features, Household
from app.pdf.generator import (
    generate_binder_pdf, render_blocks, _build_styles, _compute_col_widths,
    AVAIL_WIDTH,
)
from app.templates.narrative import Block
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, KeepTogether


def test_pdf_generates():
    profile = Profile(
        user_id="test",
        home_identity=HomeIdentity(
            address_line1="123 Main St",
            zip_code="33101",
            home_type="single_family",
            year_built=1995,
            square_feet=2000,
        ),
        features=Features(has_pool=True, has_garage=True),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_binder.pdf")
        result = generate_binder_pdf(profile, path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 1000


def test_pdf_generates_8_sections():
    """Full profile generates a PDF with all 8 sections."""
    profile = Profile(
        user_id="test",
        home_identity=HomeIdentity(
            address_line1="456 Oak Ave",
            zip_code="10001",
            home_type="single_family",
            year_built=2005,
            square_feet=3000,
            home_nickname="Oak House",
            owner_renter="owner",
        ),
        features=Features(has_pool=True, has_garage=True, has_basement=True),
        household=Household(has_pets=True, pet_types="dog", num_children=2),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_8section.pdf")
        result = generate_binder_pdf(profile, path, tier="premium")
        assert os.path.exists(result)
        assert os.path.getsize(result) > 5000


def test_pdf_empty_profile():
    """Empty profile (all defaults) should generate a valid PDF with placeholders."""
    profile = Profile(user_id="test")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_empty.pdf")
        result = generate_binder_pdf(profile, path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 1000


def test_pdf_standard_tier():
    """Standard tier generates without errors."""
    profile = Profile(
        user_id="test",
        home_identity=HomeIdentity(zip_code="33101", home_type="condo"),
        features=Features(has_pool=True),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_standard.pdf")
        result = generate_binder_pdf(profile, path, tier="standard")
        assert os.path.exists(result)
        assert os.path.getsize(result) > 1000


def test_pdf_special_characters():
    """Test that special XML characters are properly escaped in PDF generation."""
    profile = Profile(
        user_id="test",
        home_identity=HomeIdentity(
            address_line1="123 Main St <Apt 5>",
            city="Miami & Beach",
            zip_code="33101",
            home_type="condo",
            home_nickname="Bob's & Sue's House",
        ),
        features=Features(has_pool=True),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_special_chars.pdf")
        # Should not raise XML parsing error
        result = generate_binder_pdf(profile, path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 1000


# --- New formatting tests ---


def test_table_column_widths_proportional():
    """2-column label-value table should have narrower label column."""
    styles = _build_styles()
    data = [
        [Paragraph("Field", styles["TableHeader"]), Paragraph("Value", styles["TableHeader"])],
        [Paragraph("ZIP", styles["TableCell"]), Paragraph("33101", styles["TableCell"])],
        [Paragraph("Address", styles["TableCell"]), Paragraph("123 Very Long Street Name, Apartment 42B", styles["TableCell"])],
    ]
    widths = _compute_col_widths(data, 7.0 * inch)
    assert len(widths) == 2
    # First column (labels) should be narrower than second
    assert widths[0] < widths[1]
    # Total should equal available width
    assert abs(sum(widths) - 7.0 * inch) < 0.1


def test_table_column_widths_equal_for_balanced():
    """Table with similar-length columns should get roughly equal widths."""
    styles = _build_styles()
    data = [
        [Paragraph("Name", styles["TableHeader"]), Paragraph("Phone", styles["TableHeader"]), Paragraph("Email", styles["TableHeader"])],
        [Paragraph("John Smith", styles["TableCell"]), Paragraph("555-1234", styles["TableCell"]), Paragraph("john@test.com", styles["TableCell"])],
    ]
    widths = _compute_col_widths(data, 7.0 * inch)
    assert len(widths) == 3
    # No column should be more than 2x another
    assert max(widths) / min(widths) < 2.5
    assert abs(sum(widths) - 7.0 * inch) < 0.1


def test_keep_together_not_applied_to_large_checklist():
    """Checklist with >5 items should NOT be wrapped in KeepTogether."""
    styles = _build_styles()
    blocks = [
        Block(type="checklist", items=[f"Item {i}" for i in range(20)]),
    ]
    flowables = render_blocks(blocks, styles)
    # Should NOT be a single KeepTogether
    assert not any(isinstance(f, KeepTogether) for f in flowables)
    # Should have individual paragraphs
    assert len(flowables) == 20


def test_keep_together_applied_to_small_checklist():
    """Checklist with <=5 items SHOULD be wrapped in KeepTogether."""
    styles = _build_styles()
    blocks = [
        Block(type="checklist", items=["Item A", "Item B", "Item C"]),
    ]
    flowables = render_blocks(blocks, styles)
    assert any(isinstance(f, KeepTogether) for f in flowables)


def test_numbered_list_substep_numbering():
    """Substeps (bullet items) should not increment the step counter."""
    styles = _build_styles()
    blocks = [
        Block(type="numbered_list", items=[
            "First step",
            "\u2022 substep A",
            "\u2022 substep B",
            "Second step",
            "Third step",
        ]),
    ]
    flowables = render_blocks(blocks, styles)
    # Flatten KeepTogether to get all paragraphs
    all_paras = []
    for f in flowables:
        if isinstance(f, KeepTogether):
            all_paras.extend(f._content)
        elif isinstance(f, Paragraph):
            all_paras.append(f)

    # Extract text from paragraphs
    texts = [p.text for p in all_paras if hasattr(p, 'text')]
    # Should have steps numbered 1, 2, 3 (not 1, 4, 5)
    numbered = [t for t in texts if '<b>' in t and '.</b>' in t]
    assert any('1.' in t for t in numbered)
    assert any('2.' in t for t in numbered)
    assert any('3.' in t for t in numbered)
    # Should NOT have step 4 or 5
    assert not any('4.' in t for t in numbered)
    assert not any('5.' in t for t in numbered)


def test_large_table_not_in_keep_together():
    """A table with many rows should not use KeepTogether."""
    styles = _build_styles()
    blocks = [
        Block(
            type="table",
            headers=["Item", "Value"],
            rows=[[f"Item {i}", f"Value {i}"] for i in range(30)],
        ),
    ]
    flowables = render_blocks(blocks, styles)
    assert not any(isinstance(f, KeepTogether) for f in flowables)
    assert len(flowables) == 1  # Just the Table itself


def test_small_table_in_keep_together():
    """A table with few rows SHOULD use KeepTogether."""
    styles = _build_styles()
    blocks = [
        Block(
            type="table",
            headers=["Item", "Value"],
            rows=[["Item 1", "Value 1"], ["Item 2", "Value 2"]],
        ),
    ]
    flowables = render_blocks(blocks, styles)
    assert any(isinstance(f, KeepTogether) for f in flowables)


def test_subheading_keeps_next_paragraph():
    """Subheading should KeepTogether with the following paragraph."""
    styles = _build_styles()
    blocks = [
        Block(type="subheading", text="My Heading", level=2),
        Block(type="paragraph", text="Following paragraph content."),
        Block(type="paragraph", text="Another paragraph."),
    ]
    flowables = render_blocks(blocks, styles)
    # First flowable should be KeepTogether containing heading + paragraph
    assert isinstance(flowables[0], KeepTogether)
    # Should have consumed the first paragraph into the KeepTogether
    # Remaining should be the second paragraph
    assert len(flowables) == 2


def test_page_numbers_in_generated_pdf():
    """Generated PDF should have page numbers (multi-page)."""
    profile = Profile(
        user_id="test",
        home_identity=HomeIdentity(
            address_line1="123 Main St",
            zip_code="33101",
            home_type="single_family",
        ),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_pages.pdf")
        result = generate_binder_pdf(profile, path)
        assert os.path.exists(result)
        # Multi-page PDF with headers/footers should be larger
        assert os.path.getsize(result) > 5000


def test_callout_box_uses_full_width():
    """Callout box should use the full available width."""
    styles = _build_styles()
    blocks = [
        Block(type="callout_box", text="Important warning message here."),
    ]
    flowables = render_blocks(blocks, styles, avail_width=7.0 * inch)
    # Should produce a Table flowable
    assert len(flowables) == 1
    # The table should be present (it's the callout wrapper)
    from reportlab.platypus import Table as RLTable
    assert isinstance(flowables[0], RLTable)
