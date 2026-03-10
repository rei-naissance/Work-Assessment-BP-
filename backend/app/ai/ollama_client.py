"""Stage 1: Local LLM generates draft binder content with confidence scores."""

import json
import logging

import httpx

from app.models.profile import Profile
from app.library.region import get_region

logger = logging.getLogger(__name__)

# When using the custom homebinder model, the system prompt is baked into the Modelfile.
# This fallback is only used if running a non-custom model.
SYSTEM_PROMPT = "You are HomeBinder AI, a home maintenance expert. Output valid JSON only. No markdown fences or text outside the JSON."


# Map regions to their top concerns for prompt context
REGION_CONCERNS = {
    "northeast": "winter freeze damage, ice dams, nor'easters, pipe insulation, coastal flooding, old home infrastructure, heating efficiency",
    "southeast": "hurricanes, extreme humidity, mold/mildew, termites, lightning, AC reliability, flooding",
    "midwest": "tornadoes, basement flooding, foundation cracking, extreme temperature swings, sump pump reliability, ice storms, hard water",
    "southwest": "extreme heat, monsoon flash floods, dust storms, UV roof damage, water conservation, slab shifting, AC stress",
    "west": "wildfires, earthquakes, mudslides, radon, drought, defensible space, foundation retrofitting",
}

SECTION_DESCRIPTIONS = {
    "section_1": ("Emergency Quick Start", "At-a-glance emergency reference cards — gas leaks, water shutoffs, fire, power outages. The first thing someone grabs in a crisis."),
    "section_2": ("Home Profile", "The home's identity — address, type, year built, features, and household composition. The reference snapshot of the property."),
    "section_3": ("Emergency Playbooks", "Step-by-step action plans for fire, water leaks, power outages, HVAC failure, severe storms, and security incidents. Three phases: immediate, during, after."),
    "section_4": ("Guest & Sitter Mode", "Everything a guest, house sitter, or pet sitter needs — alarm codes, general instructions, escalation contacts, pet care details."),
    "section_5": ("Maintenance & Seasonal Care", "Seasonal checklists, cleaning schedules, system-specific maintenance, region-specific guides, and feature-specific care."),
    "section_6": ("Home Inventory & Checklists", "Equipment and systems inventory templates, plus emergency supply kit checklists with region-specific supplements."),
    "section_7": ("Contacts & Vendors", "Emergency contacts, neighbors, service providers (plumber, electrician, HVAC, etc.), utility companies, and insurance details."),
}


def _summarize_modules(sections: dict) -> str:
    """Build a detailed summary of what modules each section contains, including content."""
    lines = []
    for sec_key in sorted(sections.keys()):
        mods = sections[sec_key]
        if not mods:
            continue
        sec_info = SECTION_DESCRIPTIONS.get(sec_key)
        sec_label = sec_info[0] if sec_info else sec_key
        lines.append(f"\n### {sec_key} — {sec_label}")
        for mod_key, mod in mods.items():
            title = mod.get("title", mod_key)
            lines.append(f"  Module: {title}")
            # Include first few content items so Ollama knows what it's introducing
            content = mod.get("content", [])
            phases = mod.get("phases", {})
            if content:
                for item in content[:3]:
                    lines.append(f"    - {item}")
                if len(content) > 3:
                    lines.append(f"    ... and {len(content) - 3} more items")
            elif phases:
                for phase_name, items in phases.items():
                    lines.append(f"    {phase_name}: {len(items)} steps")
            cards = mod.get("cards", {})
            if cards:
                for card_key, card in cards.items():
                    lines.append(f"    Card: {card.get('title', card_key)} ({len(card.get('actions', []))} actions)")
            region_tag = mod.get("region_tag")
            if region_tag:
                lines.append(f"    [Region-tagged: {region_tag}]")
    return "\n".join(lines)


def _build_prompt(profile: Profile, sections: dict, tier: str) -> str:
    hi = profile.home_identity
    h = profile.household
    cl = profile.critical_locations.model_dump()
    cv = profile.contacts_vendors.model_dump()
    feat = profile.features.model_dump()
    tone = profile.output_tone.tone
    detail = profile.output_tone.detail_level
    prefs = profile.preferences

    # Gather context
    address = ", ".join(filter(None, [hi.address_line1, hi.city, hi.state, hi.zip_code]))
    home_type = (hi.home_type or "home").replace("_", " ")
    year_built = hi.year_built or "unknown"
    sqft = hi.square_feet or "unknown"
    region = get_region(hi.zip_code) if hi.zip_code else ""
    region_concerns = REGION_CONCERNS.get(region, "general home maintenance")

    active_features = [k.replace("has_", "").replace("_", " ") for k, v in feat.items() if v is True]
    hvac_type = feat.get("hvac_type", "")

    # Unknown locations with their keys preserved for JSON output
    unknown_locations = {}
    location_labels = {
        "water_shutoff": "Water Shutoff Valve",
        "gas_shutoff": "Gas Shutoff Valve",
        "electrical_panel": "Electrical Panel",
        "hvac_unit": "HVAC Unit",
        "sump_pump": "Sump Pump",
        "attic_access": "Attic Access",
        "crawlspace_access": "Crawlspace Access",
    }
    for key, val in cl.items():
        if val.get("status") == "unknown" and key in location_labels:
            unknown_locations[key] = location_labels[key]

    # Known locations for context
    known_locations = {}
    for key, val in cl.items():
        if val.get("status") == "known" and key in location_labels:
            loc_text = val.get("location", "")
            known_locations[location_labels[key]] = loc_text if loc_text else "location known"

    # Missing providers
    provider_labels = {
        "plumber": "Plumber", "electrician": "Electrician",
        "hvac_tech": "HVAC Technician", "handyman": "Handyman", "locksmith": "Locksmith",
    }
    missing_providers = {}
    for key, label in provider_labels.items():
        if not cv.get(key, {}).get("name"):
            missing_providers[key] = label

    # Household details
    household_lines = [f"- {h.num_adults} adult(s)"]
    if h.num_children > 0:
        household_lines.append(f"- {h.num_children} child{'ren' if h.num_children > 1 else ''} — child safety is a priority")
    if h.has_pets:
        pet_desc = h.pet_types if h.pet_types else "pets (type unspecified)"
        household_lines.append(f"- Pets: {pet_desc} — pet safety considerations apply")
    if h.has_elderly:
        household_lines.append("- Elderly household member(s) — accessibility and fall prevention matter")
    if h.has_allergies:
        household_lines.append("- Allergies/sensitivities present — air quality and filtration important")
    household_block = "\n".join(household_lines)

    # Guest/sitter context
    gm = profile.guest_sitter_mode
    guest_context = []
    if gm.instructions:
        guest_context.append("General instructions: provided")
    else:
        guest_context.append("General instructions: NOT provided — suggest what to include")
    if gm.alarm_instructions:
        guest_context.append("Alarm instructions: provided")
    elif not gm.skip_alarm:
        guest_context.append("Alarm instructions: NOT provided")
    if gm.escalation_contacts:
        guest_context.append(f"Escalation contacts: {len(gm.escalation_contacts)} listed")
    else:
        guest_context.append("Escalation contacts: NONE listed")
    if h.has_pets:
        ps = gm.pet_sitter_info
        if ps.feeding_instructions or ps.pet_names:
            guest_context.append("Pet sitter info: provided")
        else:
            guest_context.append("Pet sitter info: NOT provided — suggest what to include")
    guest_block = "\n".join(f"  - {g}" for g in guest_context)

    # Insurance and emergency contacts
    ins = cv.get("insurance", {})
    has_insurance = bool(ins.get("provider"))
    emergency_count = len(cv.get("emergency_contacts", []))
    neighbor_count = len(cv.get("neighbors", []))

    # Module content summary
    modules_summary = _summarize_modules(sections)

    # Build the unknown locations instruction
    if unknown_locations:
        location_instructions = "\n".join(
            f"  - location_{key}: Write a 2-3 sentence guide for finding the {label} in a {home_type}"
            f"{' built around ' + str(year_built) if year_built != 'unknown' else ''}."
            f" Be specific to this home type and region ({region or 'general'})."
            for key, label in unknown_locations.items()
        )
    else:
        location_instructions = "  (none — all critical locations are known)"

    # Build the missing providers instruction
    if missing_providers:
        provider_instructions = "\n".join(
            f"  - provider_{key}: Write a 2-3 sentence tip for finding a reliable {label}"
            f" in {hi.city + ', ' + hi.state if hi.city and hi.state else 'your area'}."
            f" Include what to look for and how to vet them."
            for key, label in missing_providers.items()
        )
    else:
        provider_instructions = "  (none — all providers are filled in)"

    # Pre-build pieces used in both guidance and f-string template
    known_locations_block = "\n".join(
        f"  - {k}: {v}" for k, v in known_locations.items()
    ) if known_locations else "  (none marked as known)"
    features_list = ", ".join(active_features) if active_features else "basic home systems only"
    hvac_display = hvac_type.replace("_", " ") if hvac_type else "not specified"
    missing_list = ", ".join(missing_providers.values()) if missing_providers else "all filled"
    notes = profile.free_notes.notes or "(none)"
    nickname = hi.home_nickname or "not set"
    region_display = region or "unknown"
    address_display = address or "Not provided"
    insurance_status = "on file" if has_insurance else "not provided"
    city_st = f"{hi.city}, {hi.state}" if hi.city else region_display
    nick_or_type = hi.home_nickname if hi.home_nickname else f"your {home_type}"

    tone_desc = {
        "friendly": 'Warm, approachable, encouraging. Use "your home" and "you." Like a knowledgeable friend helping out.',
        "professional": "Clear, authoritative, precise. Like a home inspector's written report. Use proper terminology.",
        "concise": "Short, direct, no fluff. Bullet-point mentality in prose form. Get to the point fast.",
    }.get(tone, "Neutral and helpful.")

    location_example = '"location_<key>": {"text": "...", "confidence": 0.70},' if unknown_locations else ""
    provider_example = '"provider_<key>": {"text": "...", "confidence": 0.60},' if missing_providers else ""

    # Section intro instructions with specific guidance
    intro_guidance = []
    for sec_key, (sec_title, sec_desc) in SECTION_DESCRIPTIONS.items():
        sec_mods = sections.get(sec_key, {})
        mod_count = len(sec_mods)
        mod_titles = [m.get("title", k) for k, m in sec_mods.items()]
        context_note = ""

        if sec_key == "section_1":
            context_note = f"Mention the home is in {city_st} ({region_display} region). "
            context_note += f"Reference the emergency cards: {', '.join(mod_titles[:3]) if mod_titles else 'quick-reference cards'}. "
            if unknown_locations:
                unk_list = ", ".join(unknown_locations.values())
                context_note += f"Note that {unk_list} still need to be located. "
        elif sec_key == "section_2":
            context_note = f"Describe {nick_or_type} specifically: {home_type} built in {year_built}, {sqft} sq ft in {city_st}. "
            if active_features:
                context_note += f"Highlight features: {', '.join(active_features[:5])}. "
        elif sec_key == "section_3":
            context_note = f"Mention {nick_or_type} in {city_st} faces {region_display} risks. "
            context_note += f"Name the playbooks: {', '.join(mod_titles[:4])}. "
            if region == "northeast":
                context_note += "Emphasize frozen pipes, nor'easters, ice storms. "
            elif region == "southeast":
                context_note += "Emphasize hurricanes, flooding, humidity damage. "
            elif region == "midwest":
                context_note += "Emphasize tornadoes, basement flooding, ice storms. "
            elif region == "southwest":
                context_note += "Emphasize extreme heat, monsoon floods, dust storms. "
            elif region == "west":
                context_note += "Emphasize wildfires, earthquakes, mudslides. "
            if notes != "(none)":
                context_note += f"The homeowner mentioned: \"{notes}\" — reference this if relevant. "
        elif sec_key == "section_4":
            if h.has_pets:
                context_note = f"Mention {nick_or_type} has {h.pet_types or 'pets'} that need care instructions. "
            else:
                context_note = f"Explain what a guest or sitter at {nick_or_type} will find here. "
            if h.num_children > 0:
                context_note += f"Note child safety info since there are {h.num_children} children. "
            if not gm.instructions:
                context_note += "Encourage the homeowner to add their own instructions. "
        elif sec_key == "section_5":
            context_note = f"For {nick_or_type} in the {region_display}, focus on "
            if region == "northeast":
                context_note += "winterization, ice dam prevention, heating efficiency. "
            elif region == "southeast":
                context_note += "hurricane prep, mold prevention, AC maintenance. "
            elif region == "midwest":
                context_note += "tornado readiness, basement waterproofing, freeze protection. "
            elif region == "southwest":
                context_note += "extreme heat prep, AC maintenance, UV roof protection, water conservation. "
            elif region == "west":
                context_note += "wildfire defensible space, earthquake prep, drought management. "
            else:
                context_note += "seasonal maintenance priorities. "
            context_note += f"Style: {prefs.maintenance_style}, DIY comfort: {prefs.diy_comfort}. "
            context_note += f"Covers {mod_count} topics. "
        elif sec_key == "section_6":
            context_note = f"For {nick_or_type}, mention documenting "
            if active_features:
                context_note += f"systems like {', '.join(active_features[:4])}. "
            else:
                context_note += "all home equipment and systems. "
            if region:
                region_kit = {"northeast": "winter storm", "southeast": "hurricane", "midwest": "tornado", "southwest": "heat emergency", "west": "wildfire/earthquake"}
                context_note += f"Include {region_kit.get(region, 'emergency')} supply kit needs. "
        elif sec_key == "section_7":
            parts = []
            if emergency_count:
                parts.append(f"has {emergency_count} emergency contact(s)")
            else:
                parts.append("has no emergency contacts yet — stress importance")
            if missing_providers:
                missing_names = ", ".join(missing_providers.values())
                parts.append(f"still needs: {missing_names}")
            if not has_insurance:
                parts.append("insurance not yet added")
            context_note = f"{nick_or_type} {'; '.join(parts)}. Personalize the encouragement. "

        intro_guidance.append(f"  {sec_key} ({sec_title}):\n    {context_note}")

    intro_block = "\n".join(intro_guidance)

    return f"""Generate personalized content for a home operating manual (binder).

═══════════════════════════════════════
HOME PROFILE
═══════════════════════════════════════
Address: {address_display}
Home Type: {home_type}
Year Built: {year_built}
Square Feet: {sqft}
Owner/Renter: {hi.owner_renter}
Nickname: {nickname}
Region: {region_display}
Region Concerns: {region_concerns}
HVAC Type: {hvac_display}
Tier: {tier}

Active Features: {features_list}

Known Critical Locations:
{known_locations_block}

Household:
{household_block}

Guest/Sitter Status:
{guest_block}

Contacts Status:
  - Emergency contacts: {emergency_count}
  - Neighbors listed: {neighbor_count}
  - Missing service providers: {missing_list}
  - Insurance: {insurance_status}

Preferences:
  - Maintenance style: {prefs.maintenance_style} (minimal/balanced/thorough)
  - DIY comfort: {prefs.diy_comfort} (none/moderate/advanced)
  - Budget priority: {prefs.budget_priority} (budget/balanced/premium)

Free-form notes from homeowner: {notes}

═══════════════════════════════════════
BINDER MODULES INCLUDED
═══════════════════════════════════════
{modules_summary}

═══════════════════════════════════════
WRITING INSTRUCTIONS
═══════════════════════════════════════

TONE: {tone} ({tone_desc})
DETAIL LEVEL: {detail}

TASK 1 — SECTION INTROS (write one per section):
Write a personalized intro paragraph (2-3 sentences) for each section.

CRITICAL RULES FOR INTROS:
- NEVER copy or paraphrase the section descriptions I gave you above. Write ORIGINAL content.
- ALWAYS mention the specific home: city/state, home type, year built, or nickname.
- ALWAYS connect to the region's specific concerns (e.g., "In the southwest, your AC system is critical" not "seasonal checklists and maintenance guides").
- If the household has children, pets, elderly, or allergies — weave that into relevant sections.
- If the homeowner left free-form notes, reference their specific concern in the relevant section intro.
- Each intro must sound like it was written FOR THIS SPECIFIC HOME, not a template.
- BAD example: "Step-by-step action plans for fire, water leaks, power outages."
- GOOD example: "Your 1962 colonial in Montclair faces northeast winter risks — here are action plans for frozen pipes, nor'easters, and power outages that hit this area."

{intro_block}

TASK 2 — LOCATION GAP-FILLS (for each unknown critical location):
{location_instructions}

TASK 3 — PROVIDER GAP-FILLS (for each missing service provider):
{provider_instructions}

TASK 4 — CONFIDENCE SCORING:
Rate each piece of content 0.0-1.0:
- 1.0: Factually certain, specific to this home type/region, safety-verified
- 0.8-0.9: High confidence, good personalization, standard advice
- 0.5-0.7: Reasonable but somewhat generic, could use enhancement
- Below 0.5: Uncertain, speculative, or placeholder quality

═══════════════════════════════════════
OUTPUT FORMAT (strict JSON, no other text)
═══════════════════════════════════════
{{
  "intros": {{
    "section_1": {{"text": "...", "confidence": 0.85}},
    "section_2": {{"text": "...", "confidence": 0.90}},
    "section_3": {{"text": "...", "confidence": 0.85}},
    "section_4": {{"text": "...", "confidence": 0.80}},
    "section_5": {{"text": "...", "confidence": 0.88}},
    "section_6": {{"text": "...", "confidence": 0.82}},
    "section_7": {{"text": "...", "confidence": 0.75}}
  }},
  "gaps": {{
    {location_example}
    {provider_example}
  }}
}}"""


class OllamaClient:
    """Stage 1: Local LLM generates draft content with confidence scores."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_draft(self, profile: Profile, sections: dict, tier: str) -> dict:
        prompt = _build_prompt(profile, sections, tier)

        # Quick connectivity check first (5 second timeout)
        try:
            async with httpx.AsyncClient(timeout=5.0) as check_client:
                await check_client.get(f"{self.base_url}/api/tags")
        except Exception:
            logger.warning("Ollama not reachable at %s — skipping AI draft", self.base_url)
            return {}

        logger.info("Ollama is reachable, generating draft (this may take 30-60 seconds)...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": SYSTEM_PROMPT,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_ctx": 16384,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw = data.get("response", "")
                if not raw:
                    logger.warning("Ollama returned empty response")
                    return {}
                result = json.loads(raw)
                # Validate structure
                if "intros" not in result:
                    result["intros"] = {}
                if "gaps" not in result:
                    result["gaps"] = {}
                return result
        except httpx.ConnectError:
            logger.warning("Ollama not reachable at %s — skipping AI draft", self.base_url)
            return {}
        except httpx.ReadTimeout:
            logger.warning("Ollama timed out (300s) — try a smaller model or shorter prompt")
            return {}
        except json.JSONDecodeError as e:
            logger.warning("Ollama returned invalid JSON: %s — raw start: %.300s", e, raw[:300] if raw else "(empty)")
            return {}
        except Exception as e:
            logger.warning("Ollama draft generation failed [%s]: %s", type(e).__name__, e)
            return {}
