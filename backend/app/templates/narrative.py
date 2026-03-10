"""Section-based template writer for the 8-section home operating manual."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List, Set

from app.models.profile import Profile
from app.library.validation import PlaceholderRegistry


@dataclass
class Block:
    """Semantic block for the PDF renderer."""
    type: str  # heading, subheading, paragraph, numbered_list, callout_box, table, checklist, spacer, page_break
    text: str = ""
    items: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    level: int = 1  # for heading depth
    ai_generated: bool = False


# Global set to track unknowns encountered during rendering
_unknown_placeholders: Set[str] = set()


def get_unknown_placeholders() -> Set[str]:
    """Get all unknown placeholders encountered during rendering."""
    return _unknown_placeholders.copy()


def clear_unknown_placeholders():
    """Clear the unknown placeholders tracker."""
    _unknown_placeholders.clear()


def _ai_intro_blocks(ai_content: dict | None, section_key: str) -> list["Block"]:
    """Return AI intro paragraph block for a section if available."""
    if not ai_content:
        return []
    intro = ai_content.get("intros", {}).get(section_key, {})
    text = intro.get("text", "")
    if text:
        return [Block(type="paragraph", text=text, ai_generated=True), Block(type="spacer")]
    return []


def _ai_gap_blocks(ai_content: dict | None, gap_prefix: str) -> list["Block"]:
    """Return AI gap-filling callout blocks matching a prefix (e.g., 'location_' or 'provider_')."""
    if not ai_content:
        return []
    blocks = []
    for key, val in ai_content.get("gaps", {}).items():
        if key.startswith(gap_prefix) and val.get("text"):
            blocks.append(Block(type="callout_box", text=val["text"], ai_generated=True))
            blocks.append(Block(type="spacer"))
    return blocks


def _unknown_with_hint(token: str) -> str:
    """Generate standardized UNKNOWN output with hint from registry."""
    registry = PlaceholderRegistry()
    hint = registry.get_hint(token)
    _unknown_placeholders.add(token)
    return f"UNKNOWN — {hint}"


def _or_unknown(value: str, token: str) -> str:
    """Return value if present, otherwise UNKNOWN with hint."""
    if value and value.strip():
        return value.strip()
    return _unknown_with_hint(token)


def _or_placeholder(value: str, label: str = None) -> str:
    """Return value if present, otherwise a simple placeholder.

    Use for free-text fields (not registered placeholders).
    Shows "Not provided" or "—" for empty values.
    """
    if value and str(value).strip():
        return str(value).strip()
    if label:
        return f"{label}: Not provided"
    return "—"


def _substitute_placeholders(text: str, profile: Profile) -> str:
    """Replace [PLACEHOLDER] tokens with actual profile values.

    Missing values render as: UNKNOWN — <hint from registry>
    """
    hi = profile.home_identity
    cv = profile.contacts_vendors
    cl = profile.critical_locations
    gm = profile.guest_sitter_mode
    sd = profile.system_details

    # Build value map from profile
    def val(v):
        """Return value if truthy, else empty string."""
        return v if v else ""

    # Profile value mappings
    value_map = {
        # Home & Address
        "HOME_ADDRESS": ", ".join(filter(None, [hi.address_line1, hi.city, hi.state, hi.zip_code])),
        "HOME_NICKNAME": hi.home_nickname,
        # Critical locations
        "WATER_SHUTOFF_LOCATION": cl.water_shutoff.location if cl.water_shutoff.status == "known" else "",
        "GAS_SHUTOFF_LOCATION": cl.gas_shutoff.location if cl.gas_shutoff.status == "known" else "",
        "ELECTRICAL_PANEL_LOCATION": cl.electrical_panel.location if cl.electrical_panel.status == "known" else "",
        "HVAC_UNIT_LOCATION": cl.hvac_unit.location if cl.hvac_unit.status == "known" else "",
        "SUMP_PUMP_LOCATION": cl.sump_pump.location if cl.sump_pump.status == "known" else "",
        "ATTIC_ACCESS_LOCATION": cl.attic_access.location if cl.attic_access.status == "known" else "",
        "CRAWLSPACE_ACCESS_LOCATION": cl.crawlspace_access.location if cl.crawlspace_access.status == "known" else "",
        # Safety & Access (now in profile!)
        "FIRE_MEETING_POINT": gm.fire_meeting_point,
        "SAFE_ROOM_LOCATION": gm.safe_room_location,
        "ALARM_CODE": gm.alarm_instructions if gm.alarm_instructions else "",
        "WIFI_PASSWORD": gm.wifi_password,
        "GARAGE_CODE": gm.garage_code,
        # People
        "PRIMARY_CONTACT_NAME": cv.emergency_contacts[0].name if cv.emergency_contacts else "",
        "PRIMARY_CONTACT_PHONE": cv.emergency_contacts[0].phone if cv.emergency_contacts else "",
        "SECONDARY_CONTACT_NAME": cv.emergency_contacts[1].name if len(cv.emergency_contacts) > 1 else "",
        "SECONDARY_CONTACT_PHONE": cv.emergency_contacts[1].phone if len(cv.emergency_contacts) > 1 else "",
        "NEIGHBOR_NAME": cv.neighbors[0].name if cv.neighbors else "",
        "NEIGHBOR_PHONE": cv.neighbors[0].phone if cv.neighbors else "",
        "TRUSTED_NEIGHBOR_NAME": cv.neighbors[0].name if cv.neighbors else "",
        "TRUSTED_NEIGHBOR_PHONE": cv.neighbors[0].phone if cv.neighbors else "",
        "PET_NAMES": gm.pet_sitter_info.pet_names if gm.pet_sitter_info else "",
        "VET_NAME": gm.pet_sitter_info.vet_name if gm.pet_sitter_info else "",
        "VET_PHONE": gm.pet_sitter_info.vet_phone if gm.pet_sitter_info else "",
        # Core service providers
        "PLUMBER_NAME": cv.plumber.name,
        "PLUMBER_PHONE": cv.plumber.phone,
        "ELECTRICIAN_NAME": cv.electrician.name,
        "ELECTRICIAN_PHONE": cv.electrician.phone,
        "HVAC_NAME": cv.hvac_tech.name,
        "HVAC_PHONE": cv.hvac_tech.phone,
        "HVAC_TECH_NAME": cv.hvac_tech.name,
        "HVAC_TECH_PHONE": cv.hvac_tech.phone,
        "HANDYMAN_NAME": cv.handyman.name,
        "HANDYMAN_PHONE": cv.handyman.phone,
        "LOCKSMITH_NAME": cv.locksmith.name,
        "LOCKSMITH_PHONE": cv.locksmith.phone,
        # Feature-dependent providers (now in profile!)
        "ROOFER_NAME": cv.roofer.name,
        "ROOFER_PHONE": cv.roofer.phone,
        "LANDSCAPER_NAME": cv.landscaper.name,
        "LANDSCAPER_PHONE": cv.landscaper.phone,
        "POOL_SERVICE_COMPANY": cv.pool_service.name,
        "POOL_SERVICE_PHONE": cv.pool_service.phone,
        "PEST_CONTROL_COMPANY": cv.pest_control.name,
        "PEST_CONTROL_PHONE": cv.pest_control.phone,
        "RESTORATION_COMPANY": cv.restoration_company.name,
        "RESTORATION_PHONE": cv.restoration_company.phone,
        "APPLIANCE_REPAIR_COMPANY": cv.appliance_repair.name,
        "APPLIANCE_REPAIR_PHONE": cv.appliance_repair.phone,
        "GARAGE_DOOR_COMPANY": cv.garage_door.name,
        "GARAGE_DOOR_PHONE": cv.garage_door.phone,
        # Utilities
        "POWER_COMPANY": cv.power.company,
        "POWER_PHONE": cv.power.phone,
        "POWER_COMPANY_PHONE": cv.power.phone,
        "GAS_COMPANY": cv.gas.company,
        "GAS_PHONE": cv.gas.phone,
        "GAS_COMPANY_PHONE": cv.gas.phone,
        "WATER_COMPANY": cv.water.company,
        "WATER_PHONE": cv.water.phone,
        # Insurance
        "INSURANCE_PROVIDER": cv.insurance.provider,
        "INSURANCE_POLICY_NUMBER": cv.insurance.policy_number,
        "INSURANCE_CLAIM_PHONE": cv.insurance.claim_phone,
        # System details (now in profile!)
        "HVAC_FILTER_SIZE": sd.hvac_filter_size,
        "HVAC_FILTER_LOCATION": sd.hvac_filter_location,
        "HVAC_MODEL": sd.hvac_model,
        "WATER_HEATER_TYPE": sd.water_heater_type,
        "WATER_HEATER_LOCATION": sd.water_heater_location,
        "GENERATOR_LOCATION": sd.generator_location,
        "GENERATOR_FUEL_TYPE": sd.generator_fuel_type,
        "GENERATOR_WATTAGE": sd.generator_wattage,
        "POOL_TYPE": sd.pool_type,
        "POOL_EQUIPMENT_LOCATION": sd.pool_equipment_location,
        "ALARM_COMPANY": sd.alarm_company,
        "ALARM_COMPANY_PHONE": sd.alarm_company_phone,
        "ALARM_PANEL_LOCATION": sd.alarm_panel_location,
    }

    # Substitute all placeholders
    result = text
    placeholder_pattern = re.compile(r'\[([A-Z][A-Z0-9_]*)\]')

    def replace_placeholder(match):
        token = match.group(1)
        value = value_map.get(token, "")
        if value:
            return value
        else:
            return _unknown_with_hint(token)

    result = placeholder_pattern.sub(replace_placeholder, result)
    return result


class TemplateWriter:
    """Template-based writer producing structured Block lists per section."""

    def write_cover(self, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        hi = profile.home_identity
        nickname = hi.home_nickname or "Your Home"
        blocks = [
            Block(type="heading", text=f"{nickname} Operating Manual", level=1),
            Block(type="spacer"),
        ]
        full_address = ", ".join(filter(None, [hi.address_line1, hi.address_line2, hi.city, hi.state, hi.zip_code]))
        if full_address:
            blocks.append(Block(type="paragraph", text=f"Property: {full_address}"))
        if hi.home_type:
            label = hi.home_type.replace("_", " ").title()
            blocks.append(Block(type="paragraph", text=f"Home Type: {label}"))
        if hi.year_built:
            blocks.append(Block(type="paragraph", text=f"Year Built: {hi.year_built}"))
        if hi.square_feet:
            blocks.append(Block(type="paragraph", text=f"Size: {hi.square_feet:,} sq ft"))
        owner_label = "Owner" if hi.owner_renter == "owner" else "Renter"
        blocks.append(Block(type="paragraph", text=f"Status: {owner_label}"))
        blocks.append(Block(type="spacer"))
        blocks.append(Block(type="paragraph",
            text="This binder contains standard operating procedures customized "
                 "for your home. Use it as your go-to reference for maintenance, "
                 "emergencies, and seasonal care."))
        return blocks

    def write_quick_start(self, modules: dict, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        blocks = _ai_intro_blocks(ai_content, "section_1")

        # Critical locations summary
        cl = profile.critical_locations
        location_items = {
            "Water Shutoff": cl.water_shutoff,
            "Gas Shutoff": cl.gas_shutoff,
            "Electrical Panel": cl.electrical_panel,
            "HVAC Unit": cl.hvac_unit,
            "Sump Pump": cl.sump_pump,
            "Attic Access": cl.attic_access,
            "Crawlspace Access": cl.crawlspace_access,
        }
        blocks.append(Block(type="subheading", text="Critical Locations"))
        rows = []
        for name, loc in location_items.items():
            status = loc.status.title()
            location_text = loc.location if loc.location else "Not specified"
            rows.append([name, status, location_text])
        blocks.append(Block(type="table", headers=["System", "Status", "Location"], rows=rows))
        blocks.append(Block(type="spacer"))

        # AI gap-filling for unknown locations
        blocks += _ai_gap_blocks(ai_content, "location_")

        # Quick-ref cards from module
        qs = modules.get("emergency_quick_start", {})
        cards = qs.get("cards", {})
        for card_key, card in cards.items():
            blocks.append(Block(type="callout_box", text=card.get("title", card_key)))

            # Handle actions - can be strings or dicts with step/details
            actions = card.get("actions", [])
            action_items = []
            for action in actions:
                if isinstance(action, str):
                    action_items.append(_substitute_placeholders(action, profile))
                elif isinstance(action, dict):
                    step = action.get("step", "")
                    details = action.get("details", "")
                    if step:
                        item = _substitute_placeholders(step, profile)
                        if details:
                            item += f" — {_substitute_placeholders(details, profile)}"
                        action_items.append(item)

            if action_items:
                blocks.append(Block(type="numbered_list", items=action_items))
            blocks.append(Block(type="spacer"))
        return blocks

    def write_home_profile(self, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        hi = profile.home_identity
        f = profile.features
        h = profile.household
        blocks = _ai_intro_blocks(ai_content, "section_2")

        # Home details
        blocks.append(Block(type="subheading", text="Property Details"))
        addr = ", ".join(filter(None, [hi.address_line1, hi.address_line2]))
        city_state = ", ".join(filter(None, [hi.city, hi.state]))
        rows = [
            ["Address", _or_placeholder(addr)],
            ["City / State", _or_placeholder(city_state)],
            ["ZIP Code", _or_placeholder(hi.zip_code)],
            ["Home Type", hi.home_type.replace("_", " ").title() if hi.home_type else "Not specified"],
            ["Year Built", str(hi.year_built) if hi.year_built else "Not specified"],
            ["Square Feet", f"{hi.square_feet:,}" if hi.square_feet else "Not specified"],
        ]
        blocks.append(Block(type="table", headers=["Field", "Value"], rows=rows))
        blocks.append(Block(type="spacer"))

        # Features summary
        blocks.append(Block(type="subheading", text="Home Features"))
        feature_items = []
        feature_dump = f.model_dump()
        for key, val in feature_dump.items():
            if key == "hvac_type":
                if val:
                    feature_items.append(f"HVAC: {val.replace('_', ' ').title()}")
            elif val is True:
                feature_items.append(key.replace("has_", "").replace("_", " ").title())
        if feature_items:
            blocks.append(Block(type="checklist", items=feature_items))
        else:
            blocks.append(Block(type="paragraph", text="No features selected."))
        blocks.append(Block(type="spacer"))

        # Household
        blocks.append(Block(type="subheading", text="Household"))
        household_rows = [
            ["Adults", str(h.num_adults)],
            ["Children", str(h.num_children)],
            ["Pets", f"Yes ({h.pet_types})" if h.has_pets else "No"],
            ["Elderly Members", "Yes" if h.has_elderly else "No"],
            ["Allergies", "Yes" if h.has_allergies else "No"],
        ]
        blocks.append(Block(type="table", headers=["", ""], rows=household_rows))
        return blocks

    def write_playbooks(self, modules: dict, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        """Render emergency playbooks with full detail."""
        blocks = _ai_intro_blocks(ai_content, "section_3")

        for key, mod in modules.items():
            title = mod.get("title", key.replace("_", " ").title())
            overview = mod.get("overview", "")
            severity = mod.get("severity", "")
            key_principle = mod.get("key_principle", "")

            # Playbook header
            blocks.append(Block(type="subheading", text=title))

            if severity:
                blocks.append(Block(type="callout_box", text=f"Severity: {severity}"))

            if overview:
                blocks.append(Block(type="paragraph", text=_substitute_placeholders(overview, profile)))

            if key_principle:
                blocks.append(Block(type="callout_box", text=f"Key Principle: {key_principle}"))

            blocks.append(Block(type="spacer"))

            # Render phases (new structure: phase_1_immediate, phase_2_stabilization, phase_3_recovery)
            phases = mod.get("phases", {})
            for phase_key in sorted(phases.keys()):
                phase = phases[phase_key]
                if not isinstance(phase, dict):
                    continue

                phase_title = phase.get("title", phase_key.replace("_", " ").title())
                priority = phase.get("priority", "")

                blocks.append(Block(type="subheading", text=phase_title, level=3))

                if priority:
                    blocks.append(Block(type="callout_box", text=priority))

                # Actions
                actions = phase.get("actions", [])
                if actions:
                    action_items = []
                    for action in actions:
                        if isinstance(action, str):
                            action_items.append(_substitute_placeholders(action, profile))
                        elif isinstance(action, dict):
                            step = action.get("step", "")
                            details = action.get("details", "")
                            details_2 = action.get("details_2", "")
                            if step:
                                item = f"**{_substitute_placeholders(step, profile)}**"
                                if details:
                                    item += f" — {_substitute_placeholders(details, profile)}"
                                if details_2:
                                    item += f" {_substitute_placeholders(details_2, profile)}"
                                action_items.append(item)
                    if action_items:
                        blocks.append(Block(type="numbered_list", items=action_items))

                # Do NOT list
                do_not = phase.get("do_not", [])
                if do_not:
                    blocks.append(Block(type="subheading", text="Do NOT:", level=4))
                    do_not_items = [f"❌ {_substitute_placeholders(item, profile)}" for item in do_not]
                    blocks.append(Block(type="checklist", items=do_not_items))

                # If trapped
                if_trapped = phase.get("if_trapped", [])
                if if_trapped:
                    blocks.append(Block(type="subheading", text="If Trapped:", level=4))
                    trapped_items = [_substitute_placeholders(item, profile) for item in if_trapped]
                    blocks.append(Block(type="numbered_list", items=trapped_items))

                # Source-specific scenarios
                source_specific = phase.get("source_specific", {})
                if source_specific:
                    for scenario_key, scenario_items in source_specific.items():
                        scenario_title = scenario_key.replace("_", " ").title()
                        blocks.append(Block(type="subheading", text=f"If {scenario_title}:", level=4))
                        scenario_list = [_substitute_placeholders(item, profile) for item in scenario_items]
                        blocks.append(Block(type="numbered_list", items=scenario_list))

                # Insurance tips
                insurance_tips = phase.get("insurance_tips", [])
                if insurance_tips:
                    blocks.append(Block(type="subheading", text="Insurance Tips:", level=4))
                    tips = [_substitute_placeholders(tip, profile) for tip in insurance_tips]
                    blocks.append(Block(type="checklist", items=tips))

                blocks.append(Block(type="spacer"))

            # Prevention checklist
            prevention = mod.get("prevention_checklist", [])
            if prevention:
                blocks.append(Block(type="subheading", text="Prevention Checklist", level=3))
                prev_items = [_substitute_placeholders(item, profile) for item in prevention]
                blocks.append(Block(type="checklist", items=prev_items))
                blocks.append(Block(type="spacer"))

            # Contacts for this playbook
            contacts = mod.get("contacts", [])
            if contacts:
                blocks.append(Block(type="subheading", text="Key Contacts", level=3))
                contact_items = [_substitute_placeholders(c, profile) for c in contacts]
                blocks.append(Block(type="checklist", items=contact_items))

            # Fallback: old-style phases (immediate/during/after)
            if not phases:
                old_phases = {}
                for phase_name in ["immediate", "during", "after"]:
                    items = mod.get(phase_name, [])
                    if items:
                        old_phases[phase_name] = items

                for phase_name, items in old_phases.items():
                    phase_label = {"immediate": "Immediate Actions", "during": "During the Event", "after": "After / Recovery"}
                    blocks.append(Block(type="subheading", text=phase_label.get(phase_name, phase_name.title()), level=3))
                    blocks.append(Block(type="numbered_list", items=[_substitute_placeholders(i, profile) for i in items]))

                # Fallback: simple content list
                content = mod.get("content", [])
                if content and not old_phases:
                    blocks.append(Block(type="numbered_list", items=[_substitute_placeholders(c, profile) for c in content]))

            blocks.append(Block(type="page_break"))

        return blocks

    def write_guest_mode(self, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        gm = profile.guest_sitter_mode
        blocks = _ai_intro_blocks(ai_content, "section_4")

        blocks.append(Block(type="subheading", text="General Instructions"))
        blocks.append(Block(type="paragraph", text=_or_placeholder(gm.instructions)))
        blocks.append(Block(type="spacer"))

        blocks.append(Block(type="subheading", text="Alarm System"))
        blocks.append(Block(type="paragraph", text=_or_placeholder(gm.alarm_instructions, "Alarm instructions")))
        blocks.append(Block(type="spacer"))

        blocks.append(Block(type="subheading", text="Escalation Contacts"))
        if gm.escalation_contacts:
            rows = [[c.name or "—", c.phone or "—", c.relationship or "—"] for c in gm.escalation_contacts]
            blocks.append(Block(type="table", headers=["Name", "Phone", "Relationship"], rows=rows))
        else:
            blocks.append(Block(type="paragraph", text="To be filled in"))
        blocks.append(Block(type="spacer"))

        # Pet sitter info
        if profile.household.has_pets:
            ps = gm.pet_sitter_info
            blocks.append(Block(type="subheading", text="Pet Sitter Information"))
            rows = [
                ["Pet Names", _or_placeholder(ps.pet_names)],
                ["Feeding Instructions", _or_placeholder(ps.feeding_instructions)],
                ["Medications", _or_placeholder(ps.medications)],
                ["Vet Name", _or_placeholder(ps.vet_name)],
                ["Vet Phone", _or_placeholder(ps.vet_phone)],
            ]
            blocks.append(Block(type="table", headers=["", ""], rows=rows))
        return blocks

    def write_maintenance(self, modules: dict, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        """Render maintenance modules with full detail."""
        blocks = _ai_intro_blocks(ai_content, "section_5")

        # Group by category
        categories: dict[str, list[tuple[str, dict]]] = {}
        for key, mod in modules.items():
            cat = mod.get("category", "general")
            categories.setdefault(cat, []).append((key, mod))

        cat_labels = {
            "emergency": "Emergency Procedures",
            "seasonal": "Seasonal Maintenance",
            "cleaning": "Cleaning",
            "maintenance": "General Maintenance",
            "landscaping": "Landscaping",
            "systems": "Systems & Equipment",
            "region": "Regional Considerations",
            "home_type": "Home-Type Specific",
            "household": "Household-Specific",
        }

        for cat, mods in categories.items():
            blocks.append(Block(type="subheading", text=cat_labels.get(cat, cat.replace("_", " ").title())))

            for key, mod in mods:
                title = mod.get("title", key.replace("_", " ").title())
                overview = mod.get("overview", "")

                blocks.append(Block(type="subheading", text=title, level=3))

                if overview:
                    blocks.append(Block(type="paragraph", text=_substitute_placeholders(overview, profile)))

                # Render content (simple list)
                content = mod.get("content", [])
                if content:
                    content_items = [_substitute_placeholders(item, profile) for item in content]
                    blocks.append(Block(type="numbered_list", items=content_items))

                # Render steps (detailed)
                steps = mod.get("steps", [])
                if steps:
                    self._render_steps(blocks, steps, profile)

                # Render tasks (seasonal/cleaning)
                tasks = mod.get("tasks", [])
                if tasks:
                    self._render_tasks(blocks, tasks, profile)

                # Render best practices
                best_practices = mod.get("best_practices", [])
                if best_practices:
                    blocks.append(Block(type="subheading", text="Best Practices", level=4))
                    bp_items = [_substitute_placeholders(bp, profile) for bp in best_practices]
                    blocks.append(Block(type="checklist", items=bp_items))

                # Render warning signs
                warning_signs = mod.get("warning_signs", [])
                if warning_signs:
                    blocks.append(Block(type="subheading", text="Warning Signs", level=4))
                    ws_items = [f"⚠️ {_substitute_placeholders(ws, profile)}" for ws in warning_signs]
                    blocks.append(Block(type="checklist", items=ws_items))

                # Render when to call pro
                when_to_call = mod.get("when_to_call_pro", [])
                if when_to_call:
                    blocks.append(Block(type="subheading", text="When to Call a Professional", level=4))
                    wtc_items = [_substitute_placeholders(item, profile) for item in when_to_call]
                    blocks.append(Block(type="checklist", items=wtc_items))

                # Render notes
                notes = mod.get("notes", [])
                if notes:
                    for note in notes:
                        blocks.append(Block(type="callout_box", text=_substitute_placeholders(note, profile)))

                blocks.append(Block(type="spacer"))
        return blocks

    def _render_steps(self, blocks: list[Block], steps: list, profile: Profile):
        """Render detailed steps with substeps."""
        step_items = []
        for step in steps:
            if isinstance(step, str):
                step_items.append(_substitute_placeholders(step, profile))
            elif isinstance(step, dict):
                step_text = step.get("step", step.get("title", ""))
                details = step.get("details", step.get("description", ""))
                if step_text:
                    item = f"**{_substitute_placeholders(step_text, profile)}**"
                    if details:
                        item += f" — {_substitute_placeholders(details, profile)}"
                    step_items.append(item)

                # Handle substeps
                substeps = step.get("substeps", step.get("items", []))
                if substeps:
                    for substep in substeps:
                        if isinstance(substep, str):
                            step_items.append(f"    • {_substitute_placeholders(substep, profile)}")
                        elif isinstance(substep, dict):
                            sub_text = substep.get("step", substep.get("item", ""))
                            sub_details = substep.get("details", "")
                            if sub_text:
                                sub_item = f"    • {_substitute_placeholders(sub_text, profile)}"
                                if sub_details:
                                    sub_item += f": {_substitute_placeholders(sub_details, profile)}"
                                step_items.append(sub_item)

        if step_items:
            blocks.append(Block(type="numbered_list", items=step_items))

    def _render_tasks(self, blocks: list[Block], tasks: list, profile: Profile):
        """Render task lists (seasonal, cleaning, etc.)."""
        for task in tasks:
            if isinstance(task, str):
                blocks.append(Block(type="paragraph", text=_substitute_placeholders(task, profile)))
            elif isinstance(task, dict):
                task_title = task.get("title", task.get("task", ""))
                frequency = task.get("frequency", "")
                items = task.get("items", task.get("steps", []))
                notes = task.get("notes", task.get("note", ""))

                if task_title:
                    title_text = task_title
                    if frequency:
                        title_text += f" ({frequency})"
                    blocks.append(Block(type="subheading", text=title_text, level=4))

                if items:
                    item_list = [_substitute_placeholders(item, profile) for item in items if isinstance(item, str)]
                    if item_list:
                        blocks.append(Block(type="checklist", items=item_list))

                if notes:
                    blocks.append(Block(type="callout_box", text=_substitute_placeholders(notes, profile)))

    def write_inventory(self, modules: dict, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        blocks = _ai_intro_blocks(ai_content, "section_6")

        # Equipment checklist
        equip = modules.get("equipment_checklist", {})
        if equip:
            blocks.append(Block(type="subheading", text="Home Equipment & Systems Inventory"))
            systems = equip.get("systems", [])
            for system in systems:
                name = system.get("name", "")
                fields = system.get("fields", [])
                rows = [[f, ""] for f in fields]
                blocks.append(Block(type="subheading", text=name, level=3))
                blocks.append(Block(type="table", headers=["Field", "Your Information"], rows=rows))
                blocks.append(Block(type="spacer"))

        # Emergency kit
        kit = modules.get("emergency_kit", {})
        if kit:
            blocks.append(Block(type="subheading", text="Emergency Supply Kit"))
            base = kit.get("base_supplies", [])
            if base:
                blocks.append(Block(type="checklist", items=base))
            blocks.append(Block(type="spacer"))

            # Region supplements
            from app.library.region import get_region
            region = get_region(profile.home_identity.zip_code) if profile.home_identity.zip_code else ""
            supplements = kit.get("region_supplements", {})
            region_to_supplement = {
                "northeast": "freeze",
                "midwest": "freeze",
                "southeast": "hurricane",
                "west": "wildfire",
                "southwest": "earthquake",
            }
            supp_key = region_to_supplement.get(region, "")
            if supp_key and supp_key in supplements:
                supp = supplements[supp_key]
                blocks.append(Block(type="subheading", text=supp.get("label", ""), level=3))
                blocks.append(Block(type="checklist", items=supp.get("items", [])))
        return blocks

    def write_contacts(self, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        cv = profile.contacts_vendors
        blocks = _ai_intro_blocks(ai_content, "section_7")

        # Emergency contacts
        blocks.append(Block(type="subheading", text="Emergency Contacts"))
        if cv.emergency_contacts:
            rows = [[c.name or "—", c.phone or "—", c.relationship or "—"] for c in cv.emergency_contacts]
            blocks.append(Block(type="table", headers=["Name", "Phone", "Relationship"], rows=rows))
        else:
            blocks.append(Block(type="paragraph", text="To be filled in"))
        blocks.append(Block(type="spacer"))

        # Neighbors
        blocks.append(Block(type="subheading", text="Neighbors"))
        if cv.neighbors:
            rows = [[c.name or "—", c.phone or "—", c.relationship or "—"] for c in cv.neighbors]
            blocks.append(Block(type="table", headers=["Name", "Phone", "Relationship"], rows=rows))
        else:
            blocks.append(Block(type="paragraph", text="To be filled in"))
        blocks.append(Block(type="spacer"))

        # Service providers
        blocks.append(Block(type="subheading", text="Service Providers"))
        providers = [
            ("Plumber", cv.plumber),
            ("Electrician", cv.electrician),
            ("HVAC Technician", cv.hvac_tech),
            ("Handyman", cv.handyman),
            ("Locksmith", cv.locksmith),
        ]
        rows = []
        for label, sp in providers:
            rows.append([label, _or_placeholder(sp.name), _or_placeholder(sp.phone)])
        blocks.append(Block(type="table", headers=["Service", "Name", "Phone"], rows=rows))
        blocks.append(Block(type="spacer"))

        # AI gap-filling for missing providers
        blocks += _ai_gap_blocks(ai_content, "provider_")

        # Utilities
        blocks.append(Block(type="subheading", text="Utility Providers"))
        utilities = [
            ("Power", cv.power),
            ("Gas", cv.gas),
            ("Water", cv.water),
            ("Internet/ISP", cv.isp),
        ]
        rows = []
        for label, up in utilities:
            rows.append([label, _or_placeholder(up.company), _or_placeholder(up.phone)])
        blocks.append(Block(type="table", headers=["Utility", "Company", "Phone"], rows=rows))
        blocks.append(Block(type="spacer"))

        # Insurance
        blocks.append(Block(type="subheading", text="Insurance"))
        ins = cv.insurance
        rows = [
            ["Provider", _or_placeholder(ins.provider)],
            ["Policy Number", _or_placeholder(ins.policy_number)],
            ["Claims Phone", _or_placeholder(ins.claim_phone)],
        ]
        blocks.append(Block(type="table", headers=["", ""], rows=rows))
        return blocks

    def render_all_sections(self, sections: dict, profile: Profile, ai_content: dict | None = None) -> dict[str, list[Block]]:
        """Render all 8 sections at once and return as a dict keyed by section_key."""
        return {
            "section_1": self.write_quick_start(sections.get("section_1", {}), profile, ai_content=ai_content),
            "section_2": self.write_home_profile(profile, ai_content=ai_content),
            "section_3": self.write_playbooks(sections.get("section_3", {}), profile, ai_content=ai_content),
            "section_4": self.write_guest_mode(profile, ai_content=ai_content),
            "section_5": self.write_maintenance(sections.get("section_5", {}), profile, ai_content=ai_content),
            "section_6": self.write_inventory(sections.get("section_6", {}), profile, ai_content=ai_content),
            "section_7": self.write_contacts(profile, ai_content=ai_content),
            "section_8": self.write_appendix(sections, profile, ai_content=ai_content),
        }

    def write_appendix(self, all_modules: dict, profile: Profile, ai_content: dict | None = None) -> list[Block]:
        blocks = []

        # Profile summary
        blocks.append(Block(type="subheading", text="Profile Summary"))
        hi = profile.home_identity
        addr = ", ".join(filter(None, [hi.address_line1, hi.address_line2, hi.city, hi.state]))
        rows = [
            ["Address", _or_placeholder(addr)],
            ["ZIP Code", _or_placeholder(hi.zip_code)],
            ["Home Type", hi.home_type.replace("_", " ").title() if hi.home_type else "Not specified"],
            ["Nickname", _or_placeholder(hi.home_nickname)],
            ["Owner/Renter", hi.owner_renter.title()],
            ["Maintenance Style", profile.preferences.maintenance_style.title()],
            ["DIY Comfort", profile.preferences.diy_comfort.title()],
            ["Tone", profile.output_tone.tone.title()],
        ]
        blocks.append(Block(type="table", headers=["Field", "Value"], rows=rows))
        blocks.append(Block(type="spacer"))

        # Notes
        if profile.free_notes.notes:
            blocks.append(Block(type="subheading", text="Your Notes"))
            blocks.append(Block(type="paragraph", text=profile.free_notes.notes))
            blocks.append(Block(type="spacer"))

        # Module index
        blocks.append(Block(type="subheading", text="Included Modules"))
        all_flat = {}
        for section_modules in all_modules.values():
            all_flat.update(section_modules)
        module_titles = [mod.get("title", key) for key, mod in all_flat.items()]
        if module_titles:
            blocks.append(Block(type="numbered_list", items=sorted(module_titles)))
        else:
            blocks.append(Block(type="paragraph", text="No modules selected."))

        blocks.append(Block(type="spacer"))
        blocks.append(Block(type="paragraph",
            text="Review and update this binder at least once per year, "
                 "or whenever you make significant changes to your home."))
        return blocks
