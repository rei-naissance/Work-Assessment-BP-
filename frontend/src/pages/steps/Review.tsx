import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="py-4 border-b border-gray-200 last:border-0">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{label}</h3>
      <div className="text-sm text-gray-700 space-y-1">{children}</div>
    </div>
  );
}

function Tag({ children, color = 'gray' }: { children: React.ReactNode; color?: 'gray' | 'green' | 'red' | 'amber' | 'brand' }) {
  const colors = {
    gray: 'bg-gray-100 text-gray-700 border border-gray-200',
    green: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
    red: 'bg-rose-50 text-rose-700 border border-rose-100',
    amber: 'bg-amber-50 text-amber-700 border border-amber-100',
    brand: 'bg-brand-50 text-brand-700 border border-brand-100',
  };
  return <span className={`inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full mr-1.5 mb-1.5 ${colors[color]}`}>{children}</span>;
}

const PROVIDER_LABELS: Record<string, string> = {
  plumber: 'Plumber', electrician: 'Electrician', hvac_tech: 'HVAC Tech', handyman: 'Handyman', locksmith: 'Locksmith',
};
const UTILITY_LABELS: Record<string, string> = {
  power: 'Power', gas: 'Gas', water: 'Water', isp: 'Internet / ISP',
};
const LOCATION_LABELS: Record<string, string> = {
  water_shutoff: 'Water Shutoff', gas_shutoff: 'Gas Shutoff', electrical_panel: 'Electrical Panel',
  hvac_unit: 'HVAC Unit', sump_pump: 'Sump Pump', attic_access: 'Attic Access', crawlspace_access: 'Crawlspace Access',
};
const MAINTENANCE_LABELS: Record<string, string> = { minimal: 'Minimal', balanced: 'Balanced', thorough: 'Thorough' };
const DIY_LABELS: Record<string, string> = { none: 'Hire It Out', moderate: 'Moderate', advanced: 'DIY First' };
const BUDGET_LABELS: Record<string, string> = { budget: 'Cost-Conscious', balanced: 'Best Value', premium: 'Quality First' };
const TONE_LABELS: Record<string, string> = { friendly: 'Conversational', professional: 'Professional', concise: 'Just the Facts' };

export default function Review({ profile }: { profile: Profile }) {
  const hi = profile.home_identity;
  const f = profile.features;
  const h = profile.household;
  const cl = profile.critical_locations;
  const cv = profile.contacts_vendors;
  const gm = profile.guest_sitter_mode;

  const enabledFeatures = Object.entries(f)
    .filter(([, v]) => v === true)
    .map(([k]) => k.replace('has_', '').replace(/_/g, ' '));

  const knownLocations = Object.entries(cl)
    .filter(([, v]) => (v as any).status === 'known');
  const unknownLocations = Object.entries(cl)
    .filter(([, v]) => (v as any).status === 'unknown');

  const filledProviders = Object.keys(PROVIDER_LABELS).filter((k) => (cv as any)[k].name);
  const skippedProviders = Object.keys(PROVIDER_LABELS).filter((k) => (cv as any)[k].skip);
  const emptyProviders = Object.keys(PROVIDER_LABELS).filter((k) => !(cv as any)[k].name && !(cv as any)[k].skip);

  const filledUtilities = Object.keys(UTILITY_LABELS).filter((k) => (cv as any)[k].company);
  const skippedUtilities = Object.keys(UTILITY_LABELS).filter((k) => (cv as any)[k].skip);
  const emptyUtilities = Object.keys(UTILITY_LABELS).filter((k) => !(cv as any)[k].company && !(cv as any)[k].skip);

  return (
    <StepCard title="Review Your Profile" subtitle="Take a look before we build your binder. You can always come back and edit.">
      {/* Home */}
      <Section label="Home">
        <p className="font-medium">{[hi.address_line1, hi.address_line2, hi.city, hi.state].filter(Boolean).join(', ') || 'No address'} {hi.zip_code || ''}</p>
        <div className="flex flex-wrap gap-1.5 mt-1">
          {hi.home_type && <Tag color="brand">{hi.home_type.replace(/_/g, ' ')}</Tag>}
          <Tag>{hi.owner_renter === 'renter' ? 'Renter' : 'Owner'}</Tag>
          {hi.year_built && <Tag>Built {hi.year_built}</Tag>}
          {hi.square_feet && <Tag>{hi.square_feet.toLocaleString()} sq ft</Tag>}
          {hi.home_nickname && <Tag>{hi.home_nickname}</Tag>}
        </div>
      </Section>

      {/* Features */}
      <Section label={`Features (${enabledFeatures.length})`}>
        {enabledFeatures.length > 0 ? (
          <div className="flex flex-wrap">
            {enabledFeatures.map((feat) => <Tag key={feat}>{feat}</Tag>)}
          </div>
        ) : (
          <p className="text-gray-500">None selected</p>
        )}
        {f.hvac_type && <p className="mt-1">HVAC: <span className="font-medium">{f.hvac_type.replace(/_/g, ' ')}</span></p>}
      </Section>

      {/* Household */}
      <Section label="Household">
        <div className="flex flex-wrap gap-1.5">
          <Tag>{h.num_adults} adult{h.num_adults !== 1 ? 's' : ''}</Tag>
          {h.num_children > 0 && <Tag>{h.num_children} child{h.num_children !== 1 ? 'ren' : ''}</Tag>}
          {h.has_pets && <Tag color="brand">{h.pet_types || 'Pets'}</Tag>}
          {h.has_elderly && <Tag color="amber">Elderly household member</Tag>}
          {h.has_allergies && <Tag color="amber">Allergies</Tag>}
        </div>
      </Section>

      {/* Critical Locations */}
      <Section label="Critical Locations">
        {knownLocations.length > 0 && (
          <div className="flex flex-wrap">
            {knownLocations.map(([k, v]) => (
              <Tag key={k} color="green">{LOCATION_LABELS[k] || k}: {(v as any).location || 'known'}</Tag>
            ))}
          </div>
        )}
        {unknownLocations.length > 0 && (
          <div className="flex flex-wrap mt-1">
            {unknownLocations.map(([k]) => (
              <Tag key={k} color="red">{LOCATION_LABELS[k] || k}</Tag>
            ))}
          </div>
        )}
        {unknownLocations.length > 0 && (
          <p className="text-xs text-gray-400 mt-1">The AI will include guides to help you locate the unknown ones.</p>
        )}
      </Section>

      {/* Emergency Contacts */}
      <Section label="Emergency Contacts">
        {cv.emergency_contacts.length > 0 ? (
          <div className="flex flex-wrap">
            {cv.emergency_contacts.map((c, i) => (
              <Tag key={i} color="brand">{c.name || 'Unnamed'}{c.relationship ? ` (${c.relationship})` : ''}</Tag>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">None added</p>
        )}
        {cv.neighbors.length > 0 && (
          <>
            <p className="text-xs font-medium text-gray-500 mt-2 mb-1">Neighbors</p>
            <div className="flex flex-wrap">
              {cv.neighbors.map((c, i) => <Tag key={i}>{c.name || 'Unnamed'}</Tag>)}
            </div>
          </>
        )}
      </Section>

      {/* Service Providers & Utilities */}
      <Section label="Service Providers & Utilities">
        {filledProviders.length > 0 && (
          <div className="flex flex-wrap">
            {filledProviders.map((k) => <Tag key={k} color="green">{PROVIDER_LABELS[k]}: {(cv as any)[k].name}</Tag>)}
          </div>
        )}
        {skippedProviders.length > 0 && (
          <div className="flex flex-wrap">
            {skippedProviders.map((k) => <Tag key={k} color="gray">{PROVIDER_LABELS[k]}: skipped</Tag>)}
          </div>
        )}
        {emptyProviders.length > 0 && (
          <div className="flex flex-wrap">
            {emptyProviders.map((k) => <Tag key={k} color="amber">{PROVIDER_LABELS[k]}: not set</Tag>)}
          </div>
        )}

        {(filledUtilities.length > 0 || skippedUtilities.length > 0 || emptyUtilities.length > 0) && (
          <p className="text-xs font-medium text-gray-500 mt-2 mb-1">Utilities</p>
        )}
        {filledUtilities.length > 0 && (
          <div className="flex flex-wrap">
            {filledUtilities.map((k) => <Tag key={k} color="green">{UTILITY_LABELS[k]}: {(cv as any)[k].company}</Tag>)}
          </div>
        )}
        {skippedUtilities.length > 0 && (
          <div className="flex flex-wrap">
            {skippedUtilities.map((k) => <Tag key={k} color="gray">{UTILITY_LABELS[k]}: skipped</Tag>)}
          </div>
        )}
        {emptyUtilities.length > 0 && (
          <div className="flex flex-wrap">
            {emptyUtilities.map((k) => <Tag key={k} color="amber">{UTILITY_LABELS[k]}: not set</Tag>)}
          </div>
        )}

        {cv.insurance.provider ? (
          <p className="mt-2 text-sm"><Tag color="green">Insurance: {cv.insurance.provider}</Tag></p>
        ) : cv.insurance.skip ? (
          <p className="mt-2 text-sm"><Tag color="gray">Insurance: skipped</Tag></p>
        ) : (
          <p className="mt-2 text-sm"><Tag color="amber">Insurance: not set</Tag></p>
        )}
      </Section>

      {/* Guest & Sitter Mode */}
      <Section label="Guest & Sitter Mode">
        <div className="flex flex-wrap">
          {gm.instructions ? <Tag color="green">General instructions added</Tag> : gm.skip_instructions ? <Tag>Instructions: skipped</Tag> : <Tag color="amber">Instructions: not set</Tag>}
          {gm.alarm_instructions ? <Tag color="green">Alarm instructions added</Tag> : gm.skip_alarm ? <Tag>Alarm: skipped</Tag> : <Tag color="amber">Alarm: not set</Tag>}
          {gm.escalation_contacts.length > 0 ? <Tag color="green">{gm.escalation_contacts.length} escalation contact{gm.escalation_contacts.length > 1 ? 's' : ''}</Tag> : gm.skip_escalation ? <Tag>Escalation: skipped</Tag> : <Tag color="amber">Escalation: not set</Tag>}
          {profile.household.has_pets && (
            gm.pet_sitter_info.pet_names || gm.pet_sitter_info.feeding_instructions
              ? <Tag color="green">Pet sitter info added</Tag>
              : gm.skip_pet_sitter ? <Tag>Pet sitter: skipped</Tag> : <Tag color="amber">Pet sitter: not set</Tag>
          )}
        </div>
      </Section>

      {/* Preferences & Style */}
      <Section label="Preferences & Style">
        <div className="flex flex-wrap">
          <Tag color="brand">{MAINTENANCE_LABELS[profile.preferences.maintenance_style] || profile.preferences.maintenance_style} maintenance</Tag>
          <Tag color="brand">{DIY_LABELS[profile.preferences.diy_comfort] || profile.preferences.diy_comfort}</Tag>
          <Tag color="brand">{BUDGET_LABELS[profile.preferences.budget_priority] || profile.preferences.budget_priority}</Tag>
          <Tag color="brand">{TONE_LABELS[profile.output_tone.tone] || profile.output_tone.tone} style</Tag>
        </div>
      </Section>

      {/* Notes */}
      {profile.free_notes.notes && (
        <Section label="Additional Notes">
          <p className="text-gray-600 leading-relaxed">{profile.free_notes.notes}</p>
        </Section>
      )}
    </StepCard>
  );
}
