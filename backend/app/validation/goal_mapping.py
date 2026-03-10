"""
Goal-to-field mapping for Binder Readiness Review.

Maps each binder goal to the profile fields that power it,
with contextual messages explaining WHY each field matters.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoalField:
    field_path: str        # dot-path into Profile.model_dump()
    display_name: str      # human label
    onboarding_step: int   # step index (0=Home, 1=Goals, 2=Features, 3=Household, 4=Locations, 5=Contacts, 6=Providers, 7=Guest, 8=Prefs, 9=Style, 10=Notes, 11=Review)
    step_label: str        # human label for the step
    weight: str            # "critical" | "important" | "helpful"
    missing_message: str   # persuasive message when field is empty
    value_message: str     # affirmation when field is filled


# ── Goal labels (used in API response) ───────────────────────

GOAL_LABELS: dict[str, str] = {
    "emergency_preparedness": "Emergency Preparedness",
    "guest_handoff": "Guest & Sitter Handoff",
    "maintenance_tracking": "Maintenance Tracking",
    "new_homeowner": "New Homeowner Guide",
    "insurance_docs": "Insurance & Documentation",
    "vendor_organization": "Vendor Organization",
}


# ── Goal → field mappings ────────────────────────────────────

GOAL_FIELD_MAP: dict[str, list[GoalField]] = {

    # ── Emergency Preparedness ───────────────────────────────
    "emergency_preparedness": [
        GoalField(
            field_path="critical_locations.water_shutoff.status",
            display_name="Water shutoff location",
            onboarding_step=4, step_label="Critical Locations",
            weight="critical",
            missing_message="Your Water Leak Playbook will say 'locate your water shutoff' instead of telling you exactly where it is. In a flooding basement at 2 AM, that distinction matters.",
            value_message="Water emergency playbook includes your exact shutoff location.",
        ),
        GoalField(
            field_path="critical_locations.electrical_panel.status",
            display_name="Electrical panel location",
            onboarding_step=4, step_label="Critical Locations",
            weight="critical",
            missing_message="During a power outage, your playbook will tell you to 'check your breaker panel' without saying where it is. That's the one moment you need it most.",
            value_message="Power outage playbook includes your exact panel location.",
        ),
        GoalField(
            field_path="critical_locations.gas_shutoff.status",
            display_name="Gas shutoff location",
            onboarding_step=4, step_label="Critical Locations",
            weight="critical",
            missing_message="If you smell gas, your playbook will say 'turn off the gas supply' — but you won't know where the valve is. This is a life-safety issue.",
            value_message="Gas leak playbook directs you to the exact shutoff valve.",
        ),
        GoalField(
            field_path="guest_sitter_mode.fire_meeting_point",
            display_name="Fire meeting point",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="critical",
            missing_message="Your Fire Playbook says 'go to your designated meeting point' — but nobody in your household will know where that is. Pick a spot now.",
            value_message="Fire playbook directs everyone to your meeting point.",
        ),
        GoalField(
            field_path="contacts_vendors.emergency_contacts",
            display_name="Emergency contacts",
            onboarding_step=5, step_label="Emergency Contacts",
            weight="critical",
            missing_message="Every emergency playbook references 'your emergency contact' — without a name and number, those instructions are incomplete.",
            value_message="All 6 emergency playbooks include your contacts by name and number.",
        ),
        GoalField(
            field_path="contacts_vendors.plumber.name",
            display_name="Plumber contact",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Your Water Leak Playbook will say 'call your plumber' with no number. During an active leak, you don't want to be searching Google.",
            value_message="Water leak playbook has your plumber's number ready.",
        ),
        GoalField(
            field_path="contacts_vendors.electrician.name",
            display_name="Electrician contact",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Power outage and electrical emergency sections reference your electrician — right now that's a blank.",
            value_message="Electrical emergency sections have your electrician's info.",
        ),
        GoalField(
            field_path="contacts_vendors.insurance.provider",
            display_name="Insurance provider",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Every emergency playbook ends with 'contact your insurance' — but your binder won't have the provider name, policy number, or claims line.",
            value_message="Insurance claim info included in all recovery sections.",
        ),
        GoalField(
            field_path="contacts_vendors.hvac_tech.name",
            display_name="HVAC technician",
            onboarding_step=6, step_label="Service Providers",
            weight="helpful",
            missing_message="Your HVAC Failure Playbook tells you to call a technician — but doesn't have one to call.",
            value_message="HVAC failure playbook has your technician's contact.",
        ),
        GoalField(
            field_path="contacts_vendors.restoration_company.name",
            display_name="Restoration company",
            onboarding_step=6, step_label="Service Providers",
            weight="helpful",
            missing_message="After a fire or flood, you'll need a restoration company fast. Having one pre-identified saves critical hours.",
            value_message="Fire and water recovery sections have your restoration company ready.",
        ),
    ],

    # ── Guest & Sitter Handoff ───────────────────────────────
    "guest_handoff": [
        GoalField(
            field_path="guest_sitter_mode.wifi_password",
            display_name="WiFi password",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="critical",
            missing_message="Your Guest & Sitter packet won't include WiFi access — guests will need to ask you directly, defeating the purpose of a self-service handoff.",
            value_message="Guest packet includes WiFi credentials — one less thing to explain.",
        ),
        GoalField(
            field_path="guest_sitter_mode.fire_meeting_point",
            display_name="Fire meeting point",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="critical",
            missing_message="If a fire happens while a sitter is watching your home, they won't know where to meet. This is a safety essential.",
            value_message="Guest safety section includes your designated meeting point.",
        ),
        GoalField(
            field_path="guest_sitter_mode.escalation_contacts",
            display_name="Escalation contacts",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="critical",
            missing_message="If something goes wrong while you're away, your guest has no one to call. The packet says 'contact the homeowner' — but what if you're unreachable?",
            value_message="Guests have a clear chain of people to contact if issues arise.",
        ),
        GoalField(
            field_path="guest_sitter_mode.alarm_instructions",
            display_name="Alarm instructions",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="critical",
            missing_message="Without alarm instructions, your guest's first morning could start with a blaring alarm and a panicked call to you.",
            value_message="Alarm disarm/arm instructions included in guest packet.",
        ),
        GoalField(
            field_path="guest_sitter_mode.garage_code",
            display_name="Garage code",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="important",
            missing_message="If your guest needs garage access, they'll be locked out or texting you for the code — the one thing the packet should handle.",
            value_message="Garage access code included in guest packet.",
        ),
        GoalField(
            field_path="guest_sitter_mode.instructions",
            display_name="General house instructions",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="important",
            missing_message="Trash day, thermostat quirks, which door sticks — the things you'd normally explain in person. Without them, your packet is just emergency info.",
            value_message="Day-to-day house instructions included for guests.",
        ),
        GoalField(
            field_path="guest_sitter_mode.pet_sitter_info.feeding_instructions",
            display_name="Pet care instructions",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="important",
            missing_message="Your sitter will need to know when and how much to feed your pets. Without this, they'll be guessing — or calling you.",
            value_message="Pet feeding schedule and care instructions included.",
        ),
        GoalField(
            field_path="guest_sitter_mode.pet_sitter_info.vet_name",
            display_name="Veterinarian info",
            onboarding_step=7, step_label="Guest & Sitter Mode",
            weight="helpful",
            missing_message="If your pet has an emergency while you're away, your sitter won't know which vet to call.",
            value_message="Vet contact info ready for pet emergencies.",
        ),
    ],

    # ── Maintenance Tracking ─────────────────────────────────
    "maintenance_tracking": [
        GoalField(
            field_path="system_details.hvac_filter_size",
            display_name="HVAC filter size",
            onboarding_step=4, step_label="Critical Locations",
            weight="critical",
            missing_message="Your maintenance schedule will remind you to change your HVAC filter every 1-3 months — but you'll still need to figure out which size to buy every time.",
            value_message="Maintenance reminders include your exact filter size for easy reordering.",
        ),
        GoalField(
            field_path="system_details.hvac_filter_location",
            display_name="HVAC filter location",
            onboarding_step=4, step_label="Critical Locations",
            weight="important",
            missing_message="Your maintenance guide says 'replace your HVAC filter' but doesn't tell you where to find it. Half the battle is knowing where to look.",
            value_message="Filter replacement guide includes the exact location.",
        ),
        GoalField(
            field_path="system_details.water_heater_type",
            display_name="Water heater type",
            onboarding_step=4, step_label="Critical Locations",
            weight="important",
            missing_message="Gas and electric water heaters have completely different maintenance needs. Without knowing your type, the guide has to be generic.",
            value_message="Water heater maintenance guide is tailored to your specific type.",
        ),
        GoalField(
            field_path="system_details.water_heater_location",
            display_name="Water heater location",
            onboarding_step=4, step_label="Critical Locations",
            weight="helpful",
            missing_message="Annual water heater maintenance starts with finding it. Your binder should tell you exactly where it is.",
            value_message="Water heater location documented for maintenance access.",
        ),
        GoalField(
            field_path="critical_locations.hvac_unit.status",
            display_name="HVAC unit location",
            onboarding_step=4, step_label="Critical Locations",
            weight="important",
            missing_message="Seasonal HVAC maintenance requires outdoor unit access. Your binder says 'locate your unit' instead of telling you where it is.",
            value_message="Seasonal maintenance checklists reference your HVAC unit location.",
        ),
        GoalField(
            field_path="contacts_vendors.hvac_tech.name",
            display_name="HVAC technician",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Your maintenance guide recommends biannual professional HVAC service — but doesn't have anyone to call.",
            value_message="Maintenance schedule includes your HVAC tech for professional service.",
        ),
        GoalField(
            field_path="contacts_vendors.plumber.name",
            display_name="Plumber contact",
            onboarding_step=6, step_label="Service Providers",
            weight="helpful",
            missing_message="Maintenance guides reference 'call a plumber' for annual inspections — your binder should have one ready.",
            value_message="Plumbing maintenance sections have your plumber's info.",
        ),
        GoalField(
            field_path="contacts_vendors.pest_control.name",
            display_name="Pest control service",
            onboarding_step=6, step_label="Service Providers",
            weight="helpful",
            missing_message="Seasonal pest prevention is part of your maintenance calendar — having a service provider makes it actionable.",
            value_message="Pest control contact included in seasonal maintenance.",
        ),
    ],

    # ── New Homeowner Guide ──────────────────────────────────
    "new_homeowner": [
        GoalField(
            field_path="critical_locations.water_shutoff.status",
            display_name="Water shutoff location",
            onboarding_step=4, step_label="Critical Locations",
            weight="critical",
            missing_message="As a new homeowner, knowing where your water shutoff is should be day-one knowledge. Your binder is the perfect place to document it.",
            value_message="Water shutoff location documented — essential new-homeowner knowledge.",
        ),
        GoalField(
            field_path="critical_locations.electrical_panel.status",
            display_name="Electrical panel location",
            onboarding_step=4, step_label="Critical Locations",
            weight="critical",
            missing_message="Every homeowner needs to know where their breaker panel is. Walk around your home and find it — then record it here.",
            value_message="Electrical panel location documented.",
        ),
        GoalField(
            field_path="critical_locations.gas_shutoff.status",
            display_name="Gas shutoff location",
            onboarding_step=4, step_label="Critical Locations",
            weight="critical",
            missing_message="If you have gas service, knowing the shutoff valve location is a safety essential. Your binder should be the first place to find it.",
            value_message="Gas shutoff documented for safety.",
        ),
        GoalField(
            field_path="contacts_vendors.emergency_contacts",
            display_name="Emergency contacts",
            onboarding_step=5, step_label="Emergency Contacts",
            weight="critical",
            missing_message="Your binder's emergency sections reference contacts that don't exist yet. As a new homeowner, this is your chance to set them up.",
            value_message="Emergency contacts established for your new home.",
        ),
        GoalField(
            field_path="contacts_vendors.plumber.name",
            display_name="Plumber",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="You'll need a plumber eventually — every homeowner does. Finding one before an emergency means you won't overpay in a panic.",
            value_message="Go-to plumber established.",
        ),
        GoalField(
            field_path="contacts_vendors.electrician.name",
            display_name="Electrician",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Having a trusted electrician before you need one is essential. Ask neighbors for recommendations and record them here.",
            value_message="Trusted electrician on file.",
        ),
        GoalField(
            field_path="contacts_vendors.insurance.provider",
            display_name="Insurance provider",
            onboarding_step=6, step_label="Service Providers",
            weight="critical",
            missing_message="Your homeowner's insurance details should be the easiest thing to find. Right now your binder's insurance sections are blank.",
            value_message="Insurance details documented and accessible.",
        ),
        GoalField(
            field_path="contacts_vendors.power.company",
            display_name="Power company",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Your power outage playbook references your utility company — recording their info now means it's ready when the lights go out.",
            value_message="Power company info ready for outage reporting.",
        ),
        GoalField(
            field_path="system_details.hvac_filter_size",
            display_name="HVAC filter size",
            onboarding_step=4, step_label="Critical Locations",
            weight="helpful",
            missing_message="Check your existing HVAC filter for the size printed on it. You'll need to replace it every 1-3 months — your binder should have the size ready.",
            value_message="HVAC filter size documented for easy replacement.",
        ),
        GoalField(
            field_path="contacts_vendors.neighbors",
            display_name="Trusted neighbors",
            onboarding_step=5, step_label="Emergency Contacts",
            weight="helpful",
            missing_message="As a new homeowner, building neighbor relationships is invaluable. Your binder has space for trusted neighbor contacts — introduce yourself and fill this in.",
            value_message="Neighbor contacts documented.",
        ),
    ],

    # ── Insurance & Documentation ────────────────────────────
    "insurance_docs": [
        GoalField(
            field_path="contacts_vendors.insurance.provider",
            display_name="Insurance provider",
            onboarding_step=6, step_label="Service Providers",
            weight="critical",
            missing_message="Your binder's insurance section will be a blank placeholder. If you ever need to file a claim after a disaster, the one document that should have your policy info won't.",
            value_message="Insurance provider documented for quick reference.",
        ),
        GoalField(
            field_path="contacts_vendors.insurance.policy_number",
            display_name="Insurance policy number",
            onboarding_step=6, step_label="Service Providers",
            weight="critical",
            missing_message="Claims adjusters ask for your policy number immediately. Having it in your binder means you're not searching through emails during a crisis.",
            value_message="Policy number ready for claims filing.",
        ),
        GoalField(
            field_path="contacts_vendors.insurance.claim_phone",
            display_name="Insurance claims phone",
            onboarding_step=6, step_label="Service Providers",
            weight="critical",
            missing_message="Every emergency recovery section says 'call your insurance claims line' — without the number, those instructions are useless when you need them most.",
            value_message="Claims line included in all emergency recovery sections.",
        ),
        GoalField(
            field_path="contacts_vendors.emergency_contacts",
            display_name="Emergency contacts",
            onboarding_step=5, step_label="Emergency Contacts",
            weight="important",
            missing_message="Insurance documentation should include who to notify in emergencies. Your contacts section is empty.",
            value_message="Emergency contacts documented alongside insurance info.",
        ),
        GoalField(
            field_path="system_details.water_heater_type",
            display_name="Water heater type",
            onboarding_step=4, step_label="Critical Locations",
            weight="helpful",
            missing_message="Home equipment details help insurance claims — knowing your water heater type, age, and location makes claims documentation easier.",
            value_message="Water heater details documented for inventory.",
        ),
        GoalField(
            field_path="system_details.hvac_model",
            display_name="HVAC model/details",
            onboarding_step=4, step_label="Critical Locations",
            weight="helpful",
            missing_message="Equipment make and model info strengthens insurance claims and warranty lookups. Your HVAC details are empty.",
            value_message="HVAC system details documented.",
        ),
    ],

    # ── Vendor Organization ──────────────────────────────────
    "vendor_organization": [
        GoalField(
            field_path="contacts_vendors.plumber.name",
            display_name="Plumber",
            onboarding_step=6, step_label="Service Providers",
            weight="critical",
            missing_message="Your binder's vendor section has an empty plumber row. This is the most commonly needed service provider for homeowners.",
            value_message="Plumber contact organized in your binder.",
        ),
        GoalField(
            field_path="contacts_vendors.electrician.name",
            display_name="Electrician",
            onboarding_step=6, step_label="Service Providers",
            weight="critical",
            missing_message="No electrician on file. When you need one, you'll be scrolling through reviews instead of opening your binder.",
            value_message="Electrician contact organized in your binder.",
        ),
        GoalField(
            field_path="contacts_vendors.hvac_tech.name",
            display_name="HVAC technician",
            onboarding_step=6, step_label="Service Providers",
            weight="critical",
            missing_message="HVAC issues are time-sensitive — no heat in winter or no AC in summer. Having a tech ready means faster resolution.",
            value_message="HVAC technician organized in your binder.",
        ),
        GoalField(
            field_path="contacts_vendors.handyman.name",
            display_name="Handyman",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="A reliable handyman handles the 80% of jobs that don't need a specialist. Worth finding one before you need one.",
            value_message="Handyman contact on file.",
        ),
        GoalField(
            field_path="contacts_vendors.locksmith.name",
            display_name="Locksmith",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Lockouts happen at the worst times. Having a locksmith pre-identified prevents overpaying for whoever shows up first.",
            value_message="Locksmith contact on file.",
        ),
        GoalField(
            field_path="contacts_vendors.power.company",
            display_name="Power company",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Your power company info is blank. Outage reporting, billing questions, and account management all need this.",
            value_message="Power company organized in your binder.",
        ),
        GoalField(
            field_path="contacts_vendors.gas.company",
            display_name="Gas company",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Gas utility info is missing. Your emergency playbook references this for leak reporting.",
            value_message="Gas company organized in your binder.",
        ),
        GoalField(
            field_path="contacts_vendors.water.company",
            display_name="Water company",
            onboarding_step=6, step_label="Service Providers",
            weight="helpful",
            missing_message="Water utility info helps with billing, water quality issues, and main line emergencies.",
            value_message="Water company organized in your binder.",
        ),
        GoalField(
            field_path="contacts_vendors.insurance.provider",
            display_name="Insurance provider",
            onboarding_step=6, step_label="Service Providers",
            weight="important",
            missing_message="Insurance is the most critical vendor for any homeowner. Your binder's insurance section is empty.",
            value_message="Insurance provider organized in your binder.",
        ),
        GoalField(
            field_path="contacts_vendors.restoration_company.name",
            display_name="Restoration company",
            onboarding_step=6, step_label="Service Providers",
            weight="helpful",
            missing_message="Water/fire damage restoration is needed fast after a disaster. Pre-identifying a company saves critical hours.",
            value_message="Restoration company ready for emergencies.",
        ),
    ],
}


# ── Helper: check if a profile field has a meaningful value ──

def check_field_present(profile_dict: dict, field_path: str) -> bool:
    """
    Traverse a dot-separated path into a profile dict.
    Returns True if the field exists and has a non-empty value.

    Handles special cases:
    - LocationStatus: checks status == 'known'
    - Lists: checks len > 0
    - ServiceProvider: checks name is non-empty
    - Strings: checks non-empty after strip
    - Bools: returns the value
    """
    parts = field_path.split(".")
    obj = profile_dict
    for part in parts:
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list):
            # For list fields, check at the list level
            return len(obj) > 0
        else:
            return False
        if obj is None:
            return False

    # Evaluate the final value
    if isinstance(obj, str):
        val = obj.strip()
        return val != "" and val.lower() != "unknown"
    if isinstance(obj, list):
        # Filter out empty entries (contacts with no name/phone)
        return any(
            (isinstance(item, dict) and (item.get("name", "").strip() or item.get("phone", "").strip()))
            if isinstance(item, dict) else bool(item)
            for item in obj
        )
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        # LocationStatus: check status == 'known'
        if "status" in obj:
            return obj["status"] == "known"
        # ServiceProvider: check name
        if "name" in obj:
            return bool(obj["name"].strip())
        return False
    return obj is not None


def build_readiness_report(profile_dict: dict, active_goals: list[str]) -> dict:
    """
    Build goal-contextualized readiness report.

    Returns:
        {
            "active_goals": [...],
            "goal_reports": { goal_key: { label, score, total, filled, present[], missing[] } },
            "step_groups": { step_idx: [{ field, goal, weight, message }] },
        }
    """
    goal_reports: dict[str, dict] = {}
    step_groups: dict[int, list[dict]] = {}
    seen_fields: set[str] = set()  # deduplicate across goals in step_groups

    for goal in active_goals:
        requirements = GOAL_FIELD_MAP.get(goal, [])
        if not requirements:
            continue

        present: list[dict] = []
        missing: list[dict] = []

        for req in requirements:
            is_present = check_field_present(profile_dict, req.field_path)
            entry = {
                "field": req.display_name,
                "step": req.onboarding_step,
                "step_label": req.step_label,
                "weight": req.weight,
            }

            if is_present:
                entry["message"] = req.value_message
                present.append(entry)
            else:
                entry["message"] = req.missing_message
                missing.append(entry)

                # Add to step_groups (deduplicate by field_path)
                dedup_key = f"{req.field_path}:{goal}"
                if dedup_key not in seen_fields:
                    seen_fields.add(dedup_key)
                    step_groups.setdefault(req.onboarding_step, []).append({
                        "field": req.display_name,
                        "goal": goal,
                        "goal_label": GOAL_LABELS.get(goal, goal),
                        "weight": req.weight,
                        "message": req.missing_message,
                    })

        total = len(requirements)
        filled = len(present)
        goal_reports[goal] = {
            "label": GOAL_LABELS.get(goal, goal),
            "score": round(filled / total * 100) if total > 0 else 100,
            "total_fields": total,
            "filled_fields": filled,
            "present": present,
            "missing": missing,
        }

    return {
        "active_goals": active_goals,
        "goal_reports": goal_reports,
        "step_groups": {str(k): v for k, v in sorted(step_groups.items())},
    }
