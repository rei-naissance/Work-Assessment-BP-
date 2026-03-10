"""Stage 3: AI-enhanced module content — personalizes template-rendered blocks."""

import json
import logging
import re
import time
from dataclasses import dataclass, field

import httpx
from anthropic import AsyncAnthropic

from app.models.profile import Profile
from app.library.region import get_region
from app.templates.narrative import Block

logger = logging.getLogger(__name__)

# Sections worth enhancing (prose-heavy, benefit from personalization)
ENHANCE_SECTIONS = {"section_1", "section_3", "section_4", "section_5"}

# Sections to skip (pure data tables, blank forms, no prose to personalize)
SKIP_SECTIONS = {"section_2", "section_6", "section_7", "section_8"}

REGION_CONCERNS = {
    "northeast": "winter freeze damage, ice dams, nor'easters, pipe insulation, heating efficiency",
    "southeast": "hurricanes, extreme humidity, mold/mildew, termites, AC reliability, flooding",
    "midwest": "tornadoes, basement flooding, foundation cracking, extreme temperature swings, ice storms",
    "southwest": "extreme heat, monsoon flash floods, dust storms, UV roof damage, water conservation",
    "west": "wildfires, earthquakes, mudslides, drought, defensible space",
}

# Block type markers for serialization
MARKER_MAP = {
    "paragraph": "paragraph",
    "numbered_list": "numbered",
    "callout_box": "callout",
    "table": "table",
    "checklist": "checklist",
    "subheading": "subheading",
}


@dataclass
class EnhancementResult:
    blocks: list[Block]
    missing_items: list[str] = field(default_factory=list)
    enhanced: bool = False


class BlockSerializer:
    """Converts Block lists to/from a simple markup format for AI processing."""

    def serialize(self, blocks: list[Block]) -> str:
        lines = []
        for block in blocks:
            if block.type == "heading":
                lines.append(f"# {block.text}")
            elif block.type == "subheading":
                prefix = "#" * min(block.level + 1, 4)
                lines.append(f"{prefix} {block.text}")
            elif block.type == "paragraph":
                lines.append(f"[paragraph] {block.text}")
            elif block.type == "numbered_list":
                items = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(block.items))
                lines.append(f"[numbered]\n{items}")
            elif block.type == "callout_box":
                lines.append(f"[callout] {block.text}")
            elif block.type == "table":
                header_row = " | ".join(block.headers) if block.headers else ""
                data_rows = "\n".join("  " + " | ".join(str(c) for c in row) for row in block.rows)
                if header_row:
                    lines.append(f"[table] {header_row}\n{data_rows}")
                else:
                    lines.append(f"[table]\n{data_rows}")
            elif block.type == "checklist":
                items = "\n".join(f"  * {item}" for item in block.items)
                lines.append(f"[checklist]\n{items}")
            elif block.type in ("spacer", "page_break"):
                continue  # Skip structural blocks
        return "\n\n".join(lines)

    def deserialize(self, text: str, original_blocks: list[Block]) -> list[Block]:
        """Parse AI-enhanced markup back into Block objects.

        Falls back to original blocks on parse failure.
        """
        try:
            return self._parse_markup(text, original_blocks)
        except Exception as e:
            logger.warning("Block deserialization failed: %s — using originals", e)
            return original_blocks

    def _parse_markup(self, text: str, original_blocks: list[Block]) -> list[Block]:
        blocks: list[Block] = []
        # Split on double newlines but preserve [marker] boundaries
        segments = re.split(r'\n\n+', text.strip())

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            if segment.startswith("# ") and not segment.startswith("## "):
                blocks.append(Block(type="heading", text=segment[2:].strip()))
            elif segment.startswith("#### "):
                blocks.append(Block(type="subheading", text=segment[5:].strip(), level=3))
            elif segment.startswith("### "):
                blocks.append(Block(type="subheading", text=segment[4:].strip(), level=3))
            elif segment.startswith("## "):
                blocks.append(Block(type="subheading", text=segment[3:].strip(), level=2))
                blocks.append(Block(type="spacer"))
            elif segment.startswith("[paragraph]"):
                text_content = segment[len("[paragraph]"):].strip()
                blocks.append(Block(type="paragraph", text=text_content))
            elif segment.startswith("[callout]"):
                text_content = segment[len("[callout]"):].strip()
                blocks.append(Block(type="callout_box", text=text_content))
            elif segment.startswith("[numbered]"):
                content = segment[len("[numbered]"):].strip()
                items = []
                for line in content.split("\n"):
                    line = line.strip()
                    # Strip leading number + dot
                    line = re.sub(r'^\d+\.\s*', '', line)
                    if line:
                        items.append(line)
                if items:
                    blocks.append(Block(type="numbered_list", items=items))
            elif segment.startswith("[table]"):
                content = segment[len("[table]"):].strip()
                lines = [l.strip() for l in content.split("\n") if l.strip()]
                if not lines:
                    continue
                # First line is headers if it has pipe separators
                if "|" in lines[0]:
                    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
                    rows = []
                    for row_line in lines[1:]:
                        cells = [c.strip() for c in row_line.split("|") if c.strip()]
                        if cells:
                            rows.append(cells)
                    blocks.append(Block(type="table", headers=headers, rows=rows))
                else:
                    rows = []
                    for row_line in lines:
                        cells = [c.strip() for c in row_line.split("|") if c.strip()]
                        if cells:
                            rows.append(cells)
                    blocks.append(Block(type="table", rows=rows))
            elif segment.startswith("[checklist]"):
                content = segment[len("[checklist]"):].strip()
                items = []
                for line in content.split("\n"):
                    line = line.strip()
                    line = re.sub(r'^\*\s*', '', line)
                    if line:
                        items.append(line)
                if items:
                    blocks.append(Block(type="checklist", items=items))
            else:
                # Unrecognized — treat as paragraph
                blocks.append(Block(type="paragraph", text=segment))

        if not blocks:
            return original_blocks

        # Re-insert spacers and page_breaks from originals at appropriate positions
        result = self._restore_structural_blocks(blocks, original_blocks)
        return result

    def _restore_structural_blocks(self, new_blocks: list[Block], original_blocks: list[Block]) -> list[Block]:
        """Re-insert spacers and page_breaks to match original structure."""
        result: list[Block] = []
        for block in new_blocks:
            result.append(block)
            # Add spacer after subheadings, tables, paragraphs (matching original pattern)
            if block.type in ("subheading", "table", "callout_box"):
                result.append(Block(type="spacer"))

        # Ensure page_breaks are preserved — check if originals ended with page_break
        if original_blocks and original_blocks[-1].type == "page_break":
            if not result or result[-1].type != "page_break":
                result.append(Block(type="page_break"))

        return result

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token for English."""
        return len(text) // 4


class ModuleEnhancer:
    """Orchestrates per-section AI enhancement of template-rendered blocks."""

    def __init__(self, *, ollama_url: str = "", ollama_model: str = "", anthropic_key: str = ""):
        self.serializer = BlockSerializer()
        self.ollama_url = ollama_url.rstrip("/")
        self.ollama_model = ollama_model
        self.anthropic_key = anthropic_key

    async def enhance_section(
        self, section_key: str, blocks: list[Block], profile: Profile, tier: str
    ) -> EnhancementResult:
        if section_key not in ENHANCE_SECTIONS:
            return EnhancementResult(blocks=blocks, enhanced=False)

        serialized = self.serializer.serialize(blocks)
        if not serialized.strip():
            return EnhancementResult(blocks=blocks, enhanced=False)

        home_context = self._build_home_context(profile)

        # Choose AI backend
        if self.anthropic_key:
            return await self._enhance_with_claude(section_key, serialized, blocks, home_context)
        elif self.ollama_url:
            return await self._enhance_with_ollama(section_key, serialized, blocks, home_context)
        else:
            return EnhancementResult(blocks=blocks, enhanced=False)

    def _build_home_context(self, profile: Profile) -> str:
        hi = profile.home_identity
        h = profile.household
        prefs = profile.preferences
        feat = profile.features.model_dump()

        home_type = (hi.home_type or "home").replace("_", " ")
        region = get_region(hi.zip_code) if hi.zip_code else ""
        region_concerns = REGION_CONCERNS.get(region, "general home maintenance")
        active_features = [k.replace("has_", "").replace("_", " ") for k, v in feat.items() if v is True]

        parts = [
            f"HOME: {home_type} in {hi.city or '?'}, {hi.state or '?'} ({region or 'unknown'} region)",
            f"Year: {hi.year_built or '?'} | {hi.square_feet or '?'} sq ft | Features: {', '.join(active_features[:8]) or 'basic'}",
            f"Household: {h.num_adults} adults, {h.num_children} children, {'pets: ' + (h.pet_types or 'yes') if h.has_pets else 'no pets'}",
        ]
        if h.has_elderly:
            parts[-1] += ", elderly members"
        if h.has_allergies:
            parts[-1] += ", allergies/sensitivities"

        parts.append(
            f"Preferences: {prefs.maintenance_style} maintenance, {prefs.diy_comfort} DIY | Tone: {profile.output_tone.tone}"
        )
        parts.append(f"Region concerns: {region_concerns}")

        if hi.home_nickname:
            parts.append(f"Nickname: {hi.home_nickname}")

        return "\n".join(parts)

    def _build_section_prompt(self, section_key: str, serialized_content: str, home_context: str) -> str:
        return f"""Personalize this home manual section for a specific homeowner.

{home_context}

CONTENT TO ENHANCE:
{serialized_content}

RULES:
1. PERSONALIZE generic phrases like "your home" with specifics (home type, age, region, nickname if available)
2. ADD region-specific emphasis where advice is currently generic
3. ADD household safety notes (children/pets/elderly) where relevant to the content
4. SMOOTH transitions between template sections so it reads naturally
5. KEEP all [markers] intact — [paragraph], [numbered], [callout], [table], [checklist] — only modify text content within them
6. KEEP ## and ### headings with their exact marker format
7. KEEP procedures factually accurate — do not change safety steps or invent new ones
8. DO NOT invent brand names, model numbers, phone numbers, or contacts
9. Items marked "UNKNOWN" must stay as-is but list them in MISSING_ITEMS
10. Keep total length within 120% of original — enhance quality, not quantity

Output the enhanced content with the same markers, then on a new line:
## MISSING_ITEMS
- [list each missing/UNKNOWN item that the homeowner should fill in]

If no missing items, write:
## MISSING_ITEMS
- None"""

    def _chunk_content(self, serialized: str, max_tokens: int = 6000) -> list[str]:
        """Split serialized content at ## SUBHEADING boundaries for Ollama's context limit."""
        if self.serializer.estimate_tokens(serialized) <= max_tokens:
            return [serialized]

        # Split at ## boundaries
        parts = re.split(r'(?=\n## )', serialized)
        chunks: list[str] = []
        current_chunk = ""

        for part in parts:
            if self.serializer.estimate_tokens(current_chunk + part) > max_tokens and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = part
            else:
                current_chunk += part

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [serialized]

    async def _enhance_with_claude(
        self, section_key: str, serialized: str, original_blocks: list[Block], home_context: str
    ) -> EnhancementResult:
        """Enhance with Claude — send full section (no chunking needed)."""
        prompt = self._build_section_prompt(section_key, serialized, home_context)

        try:
            client = AsyncAnthropic(api_key=self.anthropic_key)
            message = await client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
                timeout=60.0,
            )
            response_text = message.content[0].text
            return self._parse_enhancement_response(response_text, original_blocks)
        except Exception as e:
            logger.warning("Claude module enhancement failed for %s: %s", section_key, e)
            return EnhancementResult(blocks=original_blocks, enhanced=False)

    async def _enhance_with_ollama(
        self, section_key: str, serialized: str, original_blocks: list[Block], home_context: str
    ) -> EnhancementResult:
        """Enhance with Ollama — chunk content to fit context window."""
        # Quick connectivity check
        try:
            async with httpx.AsyncClient(timeout=5.0) as check:
                await check.get(f"{self.ollama_url}/api/tags")
        except Exception:
            logger.warning("Ollama not reachable for module enhancement")
            return EnhancementResult(blocks=original_blocks, enhanced=False)

        chunks = self._chunk_content(serialized)
        all_enhanced_text = []
        all_missing: list[str] = []

        for i, chunk in enumerate(chunks):
            prompt = self._build_section_prompt(section_key, chunk, home_context)
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": self.ollama_model,
                            "prompt": prompt,
                            "system": "You are a home maintenance expert. Enhance the content as instructed, preserving all formatting markers.",
                            "stream": False,
                            "options": {
                                "temperature": 0.5,
                                "num_ctx": 16384,
                            },
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    response_text = data.get("response", "")
                    if response_text:
                        content, missing = self._split_response(response_text)
                        all_enhanced_text.append(content)
                        all_missing.extend(missing)
                    else:
                        all_enhanced_text.append(chunk)
            except Exception as e:
                logger.warning("Ollama chunk %d/%d failed for %s: %s", i + 1, len(chunks), section_key, e)
                all_enhanced_text.append(chunk)

        combined = "\n\n".join(all_enhanced_text)
        enhanced_blocks = self.serializer.deserialize(combined, original_blocks)
        return EnhancementResult(blocks=enhanced_blocks, missing_items=all_missing, enhanced=True)

    def _parse_enhancement_response(self, response_text: str, original_blocks: list[Block]) -> EnhancementResult:
        content, missing = self._split_response(response_text)
        enhanced_blocks = self.serializer.deserialize(content, original_blocks)
        return EnhancementResult(blocks=enhanced_blocks, missing_items=missing, enhanced=True)

    def _split_response(self, text: str) -> tuple[str, list[str]]:
        """Split AI response into enhanced content and missing items list."""
        missing: list[str] = []
        content = text

        # Find ## MISSING_ITEMS section
        missing_match = re.search(r'##\s*MISSING_ITEMS\s*\n(.*)', text, re.DOTALL | re.IGNORECASE)
        if missing_match:
            content = text[:missing_match.start()].strip()
            missing_text = missing_match.group(1).strip()
            for line in missing_text.split("\n"):
                line = line.strip().lstrip("- ").strip()
                if line and line.lower() != "none":
                    missing.append(line)

        return content, missing
