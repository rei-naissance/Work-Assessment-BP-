import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';
import { checkboxClass, selectClass, hintClass } from '../../styles/form';

const FEATURE_GROUPS = [
  {
    label: 'Structure',
    items: [
      { key: 'has_pool', label: 'Pool' },
      { key: 'has_hot_tub', label: 'Hot Tub / Spa' },
      { key: 'has_garage', label: 'Garage' },
      { key: 'has_basement', label: 'Basement' },
      { key: 'has_attic', label: 'Attic' },
      { key: 'has_crawl_space', label: 'Crawl Space' },
      { key: 'has_fireplace', label: 'Fireplace' },
      { key: 'has_gutters', label: 'Gutters / Downspouts' },
    ],
  },
  {
    label: 'Outdoor / Property',
    items: [
      { key: 'has_sprinklers', label: 'Sprinkler / Irrigation' },
      { key: 'has_fence', label: 'Fence' },
      { key: 'has_deck_patio', label: 'Deck / Patio / Terrace' },
      { key: 'has_lanai', label: 'Lanai / Screened Porch' },
      { key: 'has_roof_deck', label: 'Roof Deck / Rooftop Terrace' },
      { key: 'has_driveway', label: 'Driveway' },
      { key: 'has_shed', label: 'Shed / Outbuilding' },
      { key: 'has_outdoor_kitchen', label: 'Outdoor Kitchen / Grill' },
      { key: 'has_outdoor_lighting', label: 'Outdoor Lighting' },
      { key: 'has_retaining_wall', label: 'Retaining Wall' },
    ],
  },
  {
    label: 'Water & Waste',
    items: [
      { key: 'has_septic', label: 'Septic System' },
      { key: 'has_well_water', label: 'Well Water' },
      { key: 'has_water_softener', label: 'Water Softener' },
      { key: 'has_water_filtration', label: 'Water Filtration' },
      { key: 'has_sump_pump', label: 'Sump Pump' },
    ],
  },
  {
    label: 'Energy & Power',
    items: [
      { key: 'has_solar', label: 'Solar Panels' },
      { key: 'has_generator', label: 'Generator' },
      { key: 'has_ev_charger', label: 'EV Charger' },
      { key: 'has_battery_backup', label: 'Battery Backup (e.g. Powerwall)' },
    ],
  },
  {
    label: 'Climate & Ventilation',
    items: [
      { key: 'has_whole_house_fan', label: 'Whole House Fan' },
      { key: 'has_dehumidifier', label: 'Whole House Dehumidifier' },
      { key: 'has_humidifier', label: 'Whole House Humidifier' },
      { key: 'has_air_purifier', label: 'Air Purifier / Filtration' },
      { key: 'has_ductwork', label: 'Ductwork' },
    ],
  },
  {
    label: 'Security & Automation',
    items: [
      { key: 'has_security_system', label: 'Security System' },
      { key: 'has_smart_home', label: 'Smart Home Devices' },
      { key: 'has_cameras', label: 'Security Cameras' },
      { key: 'has_smoke_co', label: 'Smoke / CO Detectors' },
      { key: 'has_doorbell_cam', label: 'Video Doorbell' },
    ],
  },
  {
    label: 'Appliances',
    items: [
      { key: 'has_washer_dryer', label: 'Washer / Dryer' },
      { key: 'has_dishwasher', label: 'Dishwasher' },
      { key: 'has_refrigerator', label: 'Refrigerator' },
      { key: 'has_garbage_disposal', label: 'Garbage Disposal' },
      { key: 'has_oven_range', label: 'Oven / Range' },
      { key: 'has_microwave', label: 'Built-in Microwave' },
      { key: 'has_freezer', label: 'Standalone Freezer' },
      { key: 'has_trash_compactor', label: 'Trash Compactor' },
    ],
  },
  {
    label: 'Specialty',
    items: [
      { key: 'has_radon_mitigation', label: 'Radon Mitigation System' },
      { key: 'has_elevator_stairlift', label: 'Elevator / Stairlift' },
      { key: 'has_central_vacuum', label: 'Central Vacuum' },
      { key: 'has_intercom', label: 'Intercom System' },
      { key: 'has_wine_cellar', label: 'Wine Cellar / Storage' },
    ],
  },
];

const HVAC_TYPES = [
  { value: '', label: 'Not specified' },
  { value: 'central_air', label: 'Central Air' },
  { value: 'window_unit', label: 'Window Units' },
  { value: 'heat_pump', label: 'Heat Pump' },
  { value: 'radiant', label: 'Radiant' },
  { value: 'none', label: 'None' },
];

export default function Features({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const f = profile.features;
  const toggle = (key: string) => {
    onChange({ ...profile, features: { ...f, [key]: !(f as any)[key] } });
  };

  return (
    <StepCard title="Home Features" subtitle="The more thorough you are here, the more personalized the AI can make your content. Check everything your home has — every selection shapes the recommendations and action items generated for you.">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-6">
        {FEATURE_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{group.label}</p>
            <div className="space-y-2">
              {group.items.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2.5 cursor-pointer group">
                  <input type="checkbox" checked={(f as any)[key] || false} onChange={() => toggle(key)} className={checkboxClass} />
                  <span className="text-sm text-gray-700 group-hover:text-gray-900 transition">{label}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-200 pt-5 mt-6 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-700">HVAC Type</p>
          <p className={hintClass}>Select your primary heating and cooling system.</p>
        </div>
        <select className={`w-52 ${selectClass}`} value={f.hvac_type} onChange={(e) => onChange({ ...profile, features: { ...f, hvac_type: e.target.value } })}>
          {HVAC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>

      <p className={`${hintClass} border-t border-gray-200 pt-4 mt-5`}>Water heater, roof, plumbing, and electrical panel are included automatically for all homes.</p>
    </StepCard>
  );
}
