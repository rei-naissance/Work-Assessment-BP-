import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import type { Profile } from '../types';
import Stepper from '../components/Stepper';
import ProgressBar from '../components/ProgressBar';
import { useAuth } from '../AuthContext';
import { pageContainer, pageTitle, pageSubtitle, btnPrimary, btnSecondary } from '../styles/shared';
import { Icon } from '../components/Icons';
import HomeIdentity from './steps/HomeIdentity';
import Features from './steps/Features';
import Household from './steps/Household';
import CriticalLocations from './steps/CriticalLocations';
import EmergencyContacts from './steps/EmergencyContacts';
import ServiceProviders from './steps/ServiceProviders';
import GuestSitterMode from './steps/GuestSitterMode';
import Preferences from './steps/Preferences';
import OutputTone from './steps/OutputTone';
import FreeNotes from './steps/FreeNotes';
import Review from './steps/Review';
import BinderGoals from './steps/BinderGoals';

const TOTAL_STEPS = 12;

/* ── Feature-to-content mapping for "What's in your binder" ── */
const SYSTEM_MODULES: { key: string; label: string; iconName: string }[] = [
  { key: 'has_pool', label: 'Pool Maintenance Guide', iconName: 'pool' },
  { key: 'has_hot_tub', label: 'Hot Tub & Spa Care', iconName: 'hot_tub' },
  { key: 'has_garage', label: 'Garage Door & Workspace', iconName: 'garage' },
  { key: 'has_basement', label: 'Basement Care & Waterproofing', iconName: 'basement' },
  { key: 'has_attic', label: 'Attic Inspection & Insulation', iconName: 'attic' },
  { key: 'has_fireplace', label: 'Fireplace & Chimney Maintenance', iconName: 'fireplace' },
  { key: 'has_septic', label: 'Septic System Care', iconName: 'septic' },
  { key: 'has_well_water', label: 'Well Water System', iconName: 'well_water' },
  { key: 'has_water_softener', label: 'Water Softener Maintenance', iconName: 'water_softener' },
  { key: 'has_water_filtration', label: 'Water Filtration System', iconName: 'water_filtration' },
  { key: 'has_sump_pump', label: 'Sump Pump Maintenance', iconName: 'sump_pump' },
  { key: 'has_solar', label: 'Solar Panel System Care', iconName: 'solar' },
  { key: 'has_generator', label: 'Generator Maintenance', iconName: 'generator' },
  { key: 'has_ev_charger', label: 'EV Charger Care', iconName: 'ev_charger' },
  { key: 'has_sprinklers', label: 'Irrigation & Sprinkler System', iconName: 'sprinklers' },
  { key: 'has_security_system', label: 'Security System Management', iconName: 'security' },
  { key: 'has_smart_home', label: 'Smart Home Systems Guide', iconName: 'smart_home' },
  { key: 'has_washer_dryer', label: 'Washer & Dryer Care', iconName: 'washer_dryer' },
  { key: 'has_dishwasher', label: 'Dishwasher Maintenance', iconName: 'dishwasher' },
  { key: 'has_refrigerator', label: 'Refrigerator Care', iconName: 'refrigerator' },
  { key: 'has_garbage_disposal', label: 'Garbage Disposal Care', iconName: 'garbage_disposal' },
  { key: 'has_radon_mitigation', label: 'Radon Mitigation System', iconName: 'radon' },
];

const HOUSEHOLD_MODULES: { check: (p: Profile) => boolean; label: string; iconName: string; hint: string }[] = [
  { check: (p) => p.household.has_pets, label: 'Pet Safety & Home Care', iconName: 'pets', hint: 'Have pets? Check "Yes" on Step 3' },
  { check: (p) => p.household.num_children > 0, label: 'Child-Proofing & Safety', iconName: 'children', hint: 'Have kids? Update count on Step 3' },
  { check: (p) => p.household.has_elderly, label: 'Accessibility & Aging-in-Place', iconName: 'elderly', hint: 'Elderly household member? Check "Yes" on Step 3' },
  { check: (p) => p.household.has_allergies, label: 'Allergy & Air Quality Guide', iconName: 'allergies', hint: 'Allergies? Check "Yes" on Step 3' },
];

const ALWAYS_INCLUDED = [
  { label: 'Emergency Quick-Start Cards', iconName: 'emergency' },
  { label: 'Fire Emergency Playbook', iconName: 'fire' },
  { label: 'Water Leak / Flood Playbook', iconName: 'water' },
  { label: 'Power Outage Playbook', iconName: 'power' },
  { label: 'HVAC Failure Playbook', iconName: 'hvac' },
  { label: 'Severe Storm Playbook', iconName: 'storm' },
  { label: 'Security Incident Playbook', iconName: 'security' },
  { label: 'Home Equipment Inventory', iconName: 'inventory' },
  { label: 'Emergency Supply Kit Checklist', iconName: 'supply_kit' },
  { label: 'Seasonal Maintenance Checklists (4)', iconName: 'seasonal' },
  { label: 'General Home Maintenance', iconName: 'maintenance' },
  { label: 'Cleaning Schedule & Guidelines', iconName: 'cleaning' },
];

function BinderPreview({ profile, step }: { profile: Profile; step: number }) {
  const f = profile.features;
  const enabled = SYSTEM_MODULES.filter((m) => (f as any)[m.key]);
  const disabled = SYSTEM_MODULES.filter((m) => !(f as any)[m.key]);
  const householdEnabled = HOUSEHOLD_MODULES.filter((m) => m.check(profile));
  const householdDisabled = HOUSEHOLD_MODULES.filter((m) => !m.check(profile));

  const totalModules = ALWAYS_INCLUDED.length + enabled.length + householdEnabled.length + 5 /* region */ + 1 /* home type */;
  const missingCount = disabled.length + householdDisabled.length;

  // Show contextual content based on step
  const showFeatures = step === 2; // Features step
  const showHousehold = step === 3; // Household step
  const showLocations = step === 4; // Critical Locations
  const showContacts = step === 5; // Emergency Contacts
  const showProviders = step === 6; // Service Providers
  const showGuest = step === 7; // Guest & Sitter
  const showReview = step === 11; // Review

  // Compute completeness for locations
  const cl = profile.critical_locations;
  const locationKeys = ['water_shutoff', 'gas_shutoff', 'electrical_panel', 'hvac_unit', 'sump_pump', 'attic_access', 'crawlspace_access'];
  const knownLocations = locationKeys.filter((k) => (cl as any)[k]?.status === 'known').length;

  // Compute completeness for contacts
  const contactCount = profile.contacts_vendors.emergency_contacts.filter((c: any) => c.name?.trim() && c.phone?.trim()).length;
  const neighborCount = profile.contacts_vendors.neighbors.filter((c: any) => c.name?.trim() && c.phone?.trim()).length;

  // Compute completeness for providers
  const cv = profile.contacts_vendors;
  const providerKeys = ['plumber', 'electrician', 'hvac_tech', 'handyman', 'locksmith'];
  const filledProviders = providerKeys.filter((k) => {
    const p = (cv as any)[k];
    return p?.skip || p?.name?.trim() || p?.phone?.trim();
  }).length;

  // Always show the summary bar
  return (
    <div className="max-w-5xl mx-auto mt-6">
      <div className="bg-gradient-to-r from-brand-50 to-emerald-50 border border-brand-100 rounded-xl overflow-hidden">
        {/* Summary bar */}
        <div className="px-5 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-brand-100">
              <Icon name="document" className="w-5 h-5 text-brand-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">Your binder: <span className="text-brand-700">{totalModules} modules</span> and counting</p>
              <p className="text-xs text-gray-500">
                {missingCount > 0 ? (
                  <>{missingCount} additional guide{missingCount > 1 ? 's' : ''} available — toggle features to unlock</>
                ) : (
                  <>All available guides unlocked!</>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-brand-500 inline-block" /> Included</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-300 inline-block" /> Not yet added</span>
          </div>
        </div>

        {/* Contextual detail section */}
        {(showFeatures || showHousehold || showReview) && (
          <div className="border-t border-brand-100 px-5 py-4">
            {/* Features step: show system modules */}
            {(showFeatures || showReview) && (
              <>
                {enabled.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-semibold text-brand-700 mb-2">
                      {showFeatures ? 'Unlocked by your selections' : 'System Guides Included'}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {enabled.map((m) => (
                        <span key={m.key} className="inline-flex items-center gap-1 text-xs bg-brand-100 text-brand-800 px-2.5 py-1 rounded-full">
                          <Icon name={m.iconName} className="w-3.5 h-3.5" /> {m.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {disabled.length > 0 && showFeatures && (
                  <div>
                    <p className="text-xs font-medium text-gray-400 mb-2">You're missing out on</p>
                    <div className="flex flex-wrap gap-1.5">
                      {disabled.map((m) => (
                        <span key={m.key} className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full">
                          <Icon name={m.iconName} className="w-3.5 h-3.5 opacity-50" /> {m.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Household step: show household modules */}
            {(showHousehold || showReview) && (
              <div className={showReview && enabled.length > 0 ? 'mt-3' : ''}>
                {householdEnabled.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-semibold text-brand-700 mb-2">Household-specific guides</p>
                    <div className="flex flex-wrap gap-1.5">
                      {householdEnabled.map((m) => (
                        <span key={m.label} className="inline-flex items-center gap-1 text-xs bg-brand-100 text-brand-800 px-2.5 py-1 rounded-full">
                          <Icon name={m.iconName} className="w-3.5 h-3.5" /> {m.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {householdDisabled.length > 0 && showHousehold && (
                  <div>
                    <p className="text-xs font-medium text-gray-400 mb-2">Also available for your household</p>
                    <div className="flex flex-wrap gap-1.5">
                      {householdDisabled.map((m) => (
                        <span key={m.label} className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full group cursor-help" title={m.hint}>
                          <Icon name={m.iconName} className="w-3.5 h-3.5 opacity-50" /> {m.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Review: show always-included */}
            {showReview && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-brand-700 mb-2">Always included</p>
                <div className="flex flex-wrap gap-1.5">
                  {ALWAYS_INCLUDED.map((m) => (
                    <span key={m.label} className="inline-flex items-center gap-1 text-xs bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full">
                      <Icon name={m.iconName} className="w-3.5 h-3.5" /> {m.label}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Critical Locations — show what's populated vs missing */}
        {showLocations && (
          <div className="border-t border-brand-100 px-5 py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-brand-700">How your locations feed into your binder</p>
              <span className={`text-xs font-bold ${knownLocations === locationKeys.length ? 'text-emerald-600' : 'text-amber-600'}`}>{knownLocations}/{locationKeys.length} identified</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { label: 'Emergency Quick-Start Cards', iconName: 'emergency', needs: 'All locations' },
                { label: 'Water Leak Playbook', iconName: 'water', needs: 'Water shutoff' },
                { label: 'Fire Emergency Playbook', iconName: 'fire', needs: 'Gas shutoff, electrical' },
                { label: 'Power Outage Playbook', iconName: 'power', needs: 'Electrical panel' },
                { label: 'HVAC Failure Playbook', iconName: 'hvac', needs: 'HVAC unit' },
                { label: 'Severe Storm Playbook', iconName: 'storm', needs: 'Sump pump' },
                { label: 'Seasonal Checklists', iconName: 'seasonal', needs: 'All locations' },
                { label: 'Guest & Sitter Packet', iconName: 'checklist', needs: 'All locations' },
              ].map((item) => (
                <div key={item.label} className="bg-white/60 rounded-lg px-2.5 py-2 text-center">
                  <Icon name={item.iconName} className="w-4 h-4 mx-auto text-gray-600" />
                  <p className="text-xs font-medium text-gray-700 mt-0.5">{item.label}</p>
                  <p className="text-xs text-gray-400">Needs: {item.needs}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Emergency Contacts — show coverage */}
        {showContacts && (
          <div className="border-t border-brand-100 px-5 py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-brand-700">Your contact coverage</p>
              <div className="flex items-center gap-3">
                <span className={`text-xs font-medium ${contactCount > 0 ? 'text-emerald-600' : 'text-amber-600'}`}>{contactCount} contact{contactCount !== 1 ? 's' : ''}</span>
                <span className={`text-xs font-medium ${neighborCount > 0 ? 'text-emerald-600' : 'text-amber-600'}`}>{neighborCount} neighbor{neighborCount !== 1 ? 's' : ''}</span>
              </div>
            </div>
            <p className="text-xs text-gray-600 mb-2">Your contacts are embedded into <strong>6 emergency playbooks</strong>, your <strong>Quick-Start Cards</strong>, and your <strong>Guest & Sitter Packet</strong>.</p>
            {contactCount === 0 && (
              <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2 border border-amber-200">
                <strong>Tip:</strong> We recommend at least 2 emergency contacts. Without them, your playbooks will say "Contact your emergency contact" with no number to call.
              </p>
            )}
          </div>
        )}

        {/* Service Providers — show what's missing */}
        {showProviders && (
          <div className="border-t border-brand-100 px-5 py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-brand-700">Provider coverage for your playbooks</p>
              <span className={`text-xs font-bold ${filledProviders === providerKeys.length ? 'text-emerald-600' : 'text-amber-600'}`}>{filledProviders}/{providerKeys.length} critical providers</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {[
                { key: 'plumber', label: 'Plumber', playbook: 'Water Leak Playbook' },
                { key: 'electrician', label: 'Electrician', playbook: 'Power Outage Playbook' },
                { key: 'hvac_tech', label: 'HVAC Tech', playbook: 'HVAC Failure Playbook' },
                { key: 'handyman', label: 'Handyman', playbook: 'General Maintenance' },
                { key: 'locksmith', label: 'Locksmith', playbook: 'Security Playbook' },
              ].map((p) => {
                const prov = (cv as any)[p.key];
                const filled = prov?.skip || prov?.name?.trim() || prov?.phone?.trim();
                return (
                  <span key={p.key} className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${filled ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${filled ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    {p.label}
                    {!filled && <span className="text-[10px] text-amber-500">({p.playbook})</span>}
                  </span>
                );
              })}
            </div>
            {filledProviders < providerKeys.length && (
              <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2 border border-amber-200">
                <strong>Tip:</strong> Providers marked in amber are referenced in emergency playbooks. Without them, your binder will say "Call your [provider]" but won't have a number.
              </p>
            )}
          </div>
        )}

        {/* Guest & Sitter — show packet status */}
        {showGuest && (
          <div className="border-t border-brand-100 px-5 py-4">
            <p className="text-xs font-semibold text-brand-700 mb-2">Your Guest & Sitter Packet</p>
            <p className="text-xs text-gray-600">
              Everything on this page generates a <strong>separate printable document</strong> — leave it on the counter for house sitters, guests, or family. The more you fill in, the more useful it becomes.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

const DEFAULT_PROFILE: Profile = {
  user_id: '',
  home_identity: { address_line1: '', address_line2: '', city: '', state: '', zip_code: '', home_type: '', year_built: null, square_feet: null, home_nickname: '', owner_renter: 'owner' },
  features: {
    has_pool: false, has_hot_tub: false, has_garage: false, has_basement: false, has_attic: false, has_crawl_space: false, has_fireplace: false, has_gutters: false,
    has_sprinklers: false, has_fence: false, has_deck_patio: false, has_lanai: false, has_roof_deck: false, has_driveway: false, has_shed: false, has_outdoor_kitchen: false, has_outdoor_lighting: false, has_retaining_wall: false,
    has_septic: false, has_well_water: false, has_water_softener: false, has_water_filtration: false, has_sump_pump: false,
    has_solar: false, has_generator: false, has_ev_charger: false, has_battery_backup: false,
    has_whole_house_fan: false, has_dehumidifier: false, has_humidifier: false, has_air_purifier: false, has_ductwork: false,
    has_security_system: false, has_smart_home: false, has_cameras: false, has_smoke_co: false, has_doorbell_cam: false,
    has_washer_dryer: false, has_dishwasher: false, has_refrigerator: false, has_garbage_disposal: false, has_oven_range: false, has_microwave: false, has_freezer: false, has_trash_compactor: false,
    has_water_heater: true, has_roof: true, has_plumbing: true, has_electrical: true,
    has_radon_mitigation: false, has_elevator_stairlift: false, has_central_vacuum: false, has_intercom: false, has_wine_cellar: false,
    hvac_type: '',
  },
  household: { num_adults: 1, num_children: 0, has_pets: false, pet_types: '', has_elderly: false, has_allergies: false },
  preferences: { maintenance_style: 'balanced', diy_comfort: 'moderate', budget_priority: 'balanced' },
  coverage: { include_emergency: true, include_seasonal: true, include_maintenance: true, include_systems: true, include_cleaning: true, include_landscaping: true },
  output_tone: { tone: 'friendly', detail_level: 'standard' },
  free_notes: { notes: '' },
  critical_locations: {
    water_shutoff: { status: 'unknown', location: '' },
    gas_shutoff: { status: 'unknown', location: '' },
    electrical_panel: { status: 'unknown', location: '' },
    hvac_unit: { status: 'unknown', location: '' },
    sump_pump: { status: 'unknown', location: '' },
    attic_access: { status: 'unknown', location: '' },
    crawlspace_access: { status: 'unknown', location: '' },
  },
  contacts_vendors: {
    emergency_contacts: [],
    neighbors: [],
    plumber: { name: '', phone: '', skip: false },
    electrician: { name: '', phone: '', skip: false },
    hvac_tech: { name: '', phone: '', skip: false },
    handyman: { name: '', phone: '', skip: false },
    locksmith: { name: '', phone: '', skip: false },
    roofer: { name: '', phone: '', skip: false },
    landscaper: { name: '', phone: '', skip: false },
    pool_service: { name: '', phone: '', skip: false },
    pest_control: { name: '', phone: '', skip: false },
    restoration_company: { name: '', phone: '', skip: false },
    appliance_repair: { name: '', phone: '', skip: false },
    garage_door: { name: '', phone: '', skip: false },
    power: { company: '', account_number: '', phone: '', skip: false },
    gas: { company: '', account_number: '', phone: '', skip: false },
    water: { company: '', account_number: '', phone: '', skip: false },
    isp: { company: '', account_number: '', phone: '', skip: false },
    insurance: { provider: '', policy_number: '', claim_phone: '', skip: false },
  },
  guest_sitter_mode: {
    instructions: '',
    skip_instructions: false,
    escalation_contacts: [],
    skip_escalation: false,
    alarm_instructions: '',
    skip_alarm: false,
    pet_sitter_info: { pet_names: '', feeding_instructions: '', medications: '', vet_name: '', vet_phone: '' },
    skip_pet_sitter: false,
    fire_meeting_point: '',
    wifi_password: '',
    garage_code: '',
    safe_room_location: '',
  },
  system_details: {
    hvac_filter_size: '',
    hvac_filter_location: '',
    hvac_model: '',
    hvac_last_serviced: '',
    water_heater_type: '',
    water_heater_location: '',
    generator_location: '',
    generator_fuel_type: '',
    generator_wattage: '',
    pool_type: '',
    pool_equipment_location: '',
    alarm_company: '',
    alarm_company_phone: '',
    alarm_panel_location: '',
  },
  binder_goals: {
    emergency_preparedness: false,
    guest_handoff: false,
    maintenance_tracking: false,
    new_homeowner: false,
    insurance_docs: false,
    vendor_organization: false,
  },
  completed: false,
};

export default function Onboarding() {
  const [step, setStepRaw] = useState(() => {
    const saved = localStorage.getItem('onboarding_step');
    return saved ? Math.min(parseInt(saved, 10), TOTAL_STEPS - 1) : 0;
  });
  const setStep = (s: number) => {
    setStepRaw(s);
    localStorage.setItem('onboarding_step', String(s));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const [profile, setProfile] = useState<Profile>(DEFAULT_PROFILE);
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [hasPaidPlan, setHasPaidPlan] = useState(false);  // Track if user already has a binder
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  // Handle clicking on a step indicator to navigate
  const handleStepClick = (targetStep: number) => {
    setValidationError('');
    setStepRaw(targetStep);
    localStorage.setItem('onboarding_step', String(targetStep));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    if (isAdmin) {
      navigate('/admin');
      return;
    }
    // Load profile
    api.get('/profile/').then((res) => {
      setProfile({ ...DEFAULT_PROFILE, ...res.data });
    }).catch(() => {});
    // Check if user already has a binder (has paid)
    api.get('/binders/').then((res) => {
      if (res.data && res.data.length > 0) {
        setHasPaidPlan(true);
      }
    }).catch(() => {});
  }, [isAdmin, navigate]);

  const save = async (completed = false): Promise<boolean> => {
    setSaving(true);
    try {
      await api.put('/profile/', { ...profile, completed });
      setSaving(false);
      return true;
    } catch (e: any) {
      setSaving(false);
      const msg = e?.response?.data?.message || e?.message || 'Failed to save. Please try again.';
      setValidationError(`Save failed: ${msg}`);
      return false;
    }
  };

  const validateStep = (): string | null => {
    if (step === 0) {
      const hi = profile.home_identity;
      if (!hi.zip_code.trim()) return 'ZIP code is required — it enables region-specific content for your binder.';
      if (!/^\d{5}(-\d{4})?$/.test(hi.zip_code.trim())) return 'Enter a valid ZIP code (e.g. 33101 or 33101-1234).';
      if (!hi.home_type) return 'Please select a home type.';
    }

    if (step === 6) {
      // Service Providers step
      const cv = profile.contacts_vendors;
      const providerKeys = ['plumber', 'electrician', 'hvac_tech', 'handyman', 'locksmith'] as const;
      const utilityKeys = ['power', 'gas', 'water', 'isp'] as const;

      const incompleteProviders = providerKeys.filter((k) => {
        const p = (cv as any)[k];
        return !p.skip && !p.name && !p.phone;
      });
      const incompleteUtilities = utilityKeys.filter((k) => {
        const u = (cv as any)[k];
        return !u.skip && !u.company && !u.phone;
      });
      const insuranceEmpty = !cv.insurance.skip && !cv.insurance.provider && !cv.insurance.claim_phone && !cv.insurance.policy_number;

      const missing: string[] = [];
      if (incompleteProviders.length > 0) missing.push(`${incompleteProviders.length} service provider${incompleteProviders.length > 1 ? 's' : ''}`);
      if (incompleteUtilities.length > 0) missing.push(`${incompleteUtilities.length} utilit${incompleteUtilities.length > 1 ? 'ies' : 'y'}`);
      if (insuranceEmpty) missing.push('insurance');

      if (missing.length > 0) {
        return `Please fill in or check "Don't have" for: ${missing.join(', ')}.`;
      }
    }

    if (step === 7) {
      // Guest & Sitter Mode step
      const gm = profile.guest_sitter_mode;
      const missing: string[] = [];

      if (!gm.skip_instructions && !gm.instructions.trim()) missing.push('general instructions');
      if (!gm.skip_alarm && !gm.alarm_instructions.trim()) missing.push('alarm instructions');
      if (!gm.skip_escalation && gm.escalation_contacts.length === 0) missing.push('escalation contacts');
      if (profile.household.has_pets && !gm.skip_pet_sitter) {
        const pi = gm.pet_sitter_info;
        if (!pi.feeding_instructions.trim() && !pi.medications.trim() && !pi.vet_name.trim()) {
          missing.push('pet sitter info');
        }
      }

      if (missing.length > 0) {
        return `Please fill in or mark "Not needed" for: ${missing.join(', ')}.`;
      }
    }

    return null;
  };

  const next = async () => {
    const error = validateStep();
    if (error) { setValidationError(error); return; }
    setValidationError('');
    const saved = await save();
    if (!saved) return;
    if (step < TOTAL_STEPS - 1) setStep(step + 1);
  };

  const finish = async () => {
    const saved = await save(true);
    if (!saved) return;
    localStorage.removeItem('onboarding_step');
    navigate(hasPaidPlan ? '/dashboard' : '/binder-review');
  };

  const prev = () => { if (step > 0) { setValidationError(''); setStep(step - 1); } };

  const stepComponents = [
    <HomeIdentity profile={profile} onChange={setProfile} />,
    <BinderGoals profile={profile} onChange={setProfile} />,
    <Features profile={profile} onChange={setProfile} />,
    <Household profile={profile} onChange={setProfile} />,
    <CriticalLocations profile={profile} onChange={setProfile} />,
    <EmergencyContacts profile={profile} onChange={setProfile} />,
    <ServiceProviders profile={profile} onChange={setProfile} />,
    <GuestSitterMode profile={profile} onChange={setProfile} />,
    <Preferences profile={profile} onChange={setProfile} />,
    <OutputTone profile={profile} onChange={setProfile} />,
    <FreeNotes profile={profile} onChange={setProfile} />,
    <Review profile={profile} />,
  ];

  return (
    <div className={pageContainer}>
      <div className="text-center">
        <p className="text-xs font-semibold tracking-[0.2em] text-gray-400 uppercase">Onboarding</p>
        <h1 className={`${pageTitle} mt-2`}>Set Up Your Home Profile</h1>
        <p className={pageSubtitle}>Step {step + 1} of {TOTAL_STEPS} <span className="mx-2 text-gray-300">·</span> Estimated time: 10–12 minutes</p>
      </div>
      <div className="mt-5">
        <ProgressBar current={step + 1} total={TOTAL_STEPS} />
        <Stepper current={step} onStepClick={handleStepClick} />
      </div>
      {step === 0 && (
        <p className="text-center text-sm text-gray-500 mt-5 max-w-2xl mx-auto">
          Only a few fields are required — but the more you share, the more personalized your binder will be.
          Fill in what you're comfortable with and skip the rest.
        </p>
      )}
      <div className="mt-6">{stepComponents[step]}</div>
      <BinderPreview profile={profile} step={step} />
      {validationError && (
        <div className="max-w-5xl mx-auto mt-4">
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 px-4 py-2.5 rounded-lg">{validationError}</p>
        </div>
      )}
      <div className="flex items-center justify-between mt-5 max-w-5xl mx-auto">
        <div className="flex items-center gap-2">
          <button onClick={prev} disabled={step === 0} className={`${btnSecondary} px-5 py-2.5 disabled:opacity-30`}>
            Back
          </button>
          <button
            onClick={async () => {
              const saved = await save();
              if (saved) navigate(hasPaidPlan ? '/dashboard' : '/');
            }}
            disabled={saving}
            className="text-sm text-gray-500 hover:text-gray-700 px-3 py-2.5 transition"
          >
            Save & Exit
          </button>
        </div>
        {step < TOTAL_STEPS - 1 ? (
          <button onClick={next} disabled={saving} className={`${btnPrimary} px-8 py-2.5`}>
            {saving ? 'Saving...' : 'Continue'}
          </button>
        ) : (
          <button onClick={finish} disabled={saving} className={`${btnPrimary} px-8 py-2.5`}>
            {saving ? 'Saving...' : hasPaidPlan ? 'Save & Return to Dashboard' : 'Finish & Review Your Binder'}
          </button>
        )}
      </div>
    </div>
  );
}
