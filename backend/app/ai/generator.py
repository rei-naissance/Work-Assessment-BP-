"""Orchestrates the multi-stage AI content generation pipeline."""

import logging
import time

from app.config import settings
from app.models.profile import Profile
from app.ai.ollama_client import OllamaClient
from app.ai.enhancer import ClaudeEnhancer
from app.ai.module_enhancer import ModuleEnhancer, ENHANCE_SECTIONS
from app.templates.narrative import Block

logger = logging.getLogger(__name__)

# Total enhancement timeout: 10 minutes
MAX_ENHANCEMENT_TIME = 600


class AIContentGenerator:
    """Orchestrates Stage 1 (Ollama), Stage 2 (Claude), and Stage 3 (module enhancement)."""

    async def generate(self, profile: Profile, sections: dict, tier: str) -> tuple[dict, dict]:
        """Run the two-stage intro/gap pipeline.

        Returns:
            (ai_content, ai_draft) — final enhanced content and raw Ollama draft.
        """
        # Stage 1: Ollama draft
        ollama = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        draft = await ollama.generate_draft(profile, sections, tier)

        if not draft:
            logger.info("No AI draft generated — binder will use templates only")
            return {}, {}

        logger.info("Stage 1 complete — Ollama draft generated with %d intros, %d gaps",
                     len(draft.get("intros", {})), len(draft.get("gaps", {})))

        # Stage 2: Claude enhancement (only if API key configured)
        if settings.anthropic_api_key:
            enhancer = ClaudeEnhancer(settings.anthropic_api_key)
            enhanced = await enhancer.enhance(draft, profile)
            logger.info("Stage 2 complete — Claude enhancement applied")
            return enhanced, draft

        logger.info("No Anthropic API key — using Ollama draft as final content")
        return draft, draft

    async def enhance_modules(
        self,
        section_blocks: dict[str, list[Block]],
        profile: Profile,
        tier: str,
    ) -> tuple[dict[str, list[Block]], dict[str, list[str]]]:
        """Stage 3: AI-enhance template-rendered blocks.

        Claude-primary, Ollama as fallback. Only runs for premium tier.
        Returns (enhanced_blocks, missing_items_by_section).
        """
        if not settings.ai_enhancement_enabled:
            logger.info("AI enhancement disabled via config")
            return section_blocks, {}

        if tier != "premium":
            logger.info("AI enhancement skipped — standard tier")
            return section_blocks, {}

        # Determine provider
        provider = settings.ai_enhancement_provider
        use_claude = False
        use_ollama = False

        if provider == "claude" and settings.anthropic_api_key:
            use_claude = True
        elif provider == "ollama":
            use_ollama = True
        elif provider == "auto":
            if settings.anthropic_api_key:
                use_claude = True
            else:
                use_ollama = True
        elif provider == "none":
            return section_blocks, {}

        enhancer = ModuleEnhancer(
            ollama_url=settings.ollama_base_url if use_ollama else "",
            ollama_model=settings.ollama_model if use_ollama else "",
            anthropic_key=settings.anthropic_api_key if use_claude else "",
        )

        provider_name = "Claude" if use_claude else "Ollama"
        logger.info("Stage 3: Enhancing modules with %s", provider_name)

        enhanced = dict(section_blocks)
        all_missing: dict[str, list[str]] = {}
        start_time = time.time()
        sections_enhanced = 0

        for section_key in sorted(ENHANCE_SECTIONS):
            # Timeout guard
            elapsed = time.time() - start_time
            if elapsed > MAX_ENHANCEMENT_TIME:
                logger.warning("Enhancement timeout (%.0fs) — skipping remaining sections", elapsed)
                break

            blocks = section_blocks.get(section_key, [])
            if not blocks:
                continue

            try:
                result = await enhancer.enhance_section(section_key, blocks, profile, tier)
                if result.enhanced:
                    enhanced[section_key] = result.blocks
                    sections_enhanced += 1
                if result.missing_items:
                    all_missing[section_key] = result.missing_items
            except Exception as e:
                logger.warning("Enhancement failed for %s: %s — using original", section_key, e)

        elapsed = time.time() - start_time
        logger.info("Stage 3 complete — %d sections enhanced in %.1fs, %d missing items total",
                     sections_enhanced, elapsed,
                     sum(len(v) for v in all_missing.values()))

        return enhanced, all_missing
