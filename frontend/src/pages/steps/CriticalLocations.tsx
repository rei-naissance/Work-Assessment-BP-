import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';
import { inputClass, labelClass, selectClass, hintClass } from '../../styles/form';
import { Icon } from '../../components/Icons';

const LOCATIONS = [
  { key: 'water_shutoff', label: 'Water Shutoff Valve', why: 'A burst pipe can cause $10,000+ in damage in hours. Knowing this location is the #1 thing you can do to protect your home.', feeds: 'Water Leak Playbook, Emergency Quick-Start Cards' },
  { key: 'gas_shutoff', label: 'Gas Shutoff Valve', why: 'If you smell gas, seconds matter. This goes directly into your Fire & Gas Emergency playbook.', feeds: 'Fire Emergency Playbook, Gas Leak Procedures' },
  { key: 'electrical_panel', label: 'Electrical Panel', why: 'Needed to cut power in emergencies and for any electrical work. Every contractor will ask where this is.', feeds: 'Power Outage Playbook, Emergency Quick-Start Cards' },
  { key: 'hvac_unit', label: 'HVAC Unit', why: 'For filter changes, emergency shutoff, and seasonal maintenance — this is referenced throughout your binder.', feeds: 'HVAC Failure Playbook, Seasonal Maintenance Checklists' },
  { key: 'sump_pump', label: 'Sump Pump', why: 'During heavy rain, you need to check this fast. Location goes into your flooding and storm playbooks.', feeds: 'Water Leak Playbook, Severe Storm Playbook' },
  { key: 'attic_access', label: 'Attic Access', why: 'Needed for insulation checks, leak tracing, and seasonal inspections.', feeds: 'Seasonal Maintenance, Roof & Attic Inspection Guide' },
  { key: 'crawlspace_access', label: 'Crawlspace Access', why: 'Important for plumbing checks, pest inspections, and moisture monitoring.', feeds: 'Seasonal Maintenance, Plumbing Guide' },
] as const;

function CompletionBar({ known, total }: { known: number; total: number }) {
  const pct = total > 0 ? Math.round((known / total) * 100) : 0;
  const color = pct === 100 ? 'bg-emerald-500' : pct >= 50 ? 'bg-brand-500' : 'bg-amber-500';
  const textColor = pct === 100 ? 'text-emerald-700' : pct >= 50 ? 'text-brand-700' : 'text-amber-700';
  const bgColor = pct === 100 ? 'bg-emerald-50 border-emerald-200' : pct >= 50 ? 'bg-brand-50 border-brand-200' : 'bg-amber-50 border-amber-200';

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${bgColor} mb-5`}>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className={`text-xs font-semibold ${textColor}`}>
            {pct === 100 ? 'All locations identified!' : `${known} of ${total} locations identified`}
          </span>
          <span className={`text-xs font-bold ${textColor}`}>{pct}%</span>
        </div>
        <div className="w-full h-1.5 bg-white/60 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
        </div>
      </div>
      {pct < 100 && (
        <span className="text-xs text-gray-500 whitespace-nowrap">
          {pct === 0 ? "Don't worry — mark what you know" : 'Getting there!'}
        </span>
      )}
    </div>
  );
}

export default function CriticalLocations({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const hi = profile.home_identity;
  const cl = profile.critical_locations;

  const knownCount = LOCATIONS.filter(({ key }) => (cl as any)[key].status === 'known').length;

  const updateIdentity = (field: string, value: string) => {
    onChange({ ...profile, home_identity: { ...hi, [field]: value } });
  };

  const updateLocation = (key: string, field: string, value: string) => {
    const loc = (cl as any)[key];
    onChange({
      ...profile,
      critical_locations: { ...cl, [key]: { ...loc, [field]: value } },
    });
  };

  return (
    <StepCard title="Critical Locations" subtitle="Mark what you know — for anything you're unsure about, our AI can generate step-by-step guides to help you locate them.">
  <div className="space-y-6">
        {/* Impact callout */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="w-9 h-9 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0"><Icon name="critical_locations" className="w-4.5 h-4.5" /></span>
            <div>
              <p className="text-sm font-semibold text-navy-900">These locations appear on your Emergency Quick-Start Cards</p>
              <p className="text-xs text-gray-500 mt-0.5">Every location you mark as "Known" gets printed on a laminated-style reference card at the front of your binder. In an emergency, you flip to page 1 and everything is right there — no searching.</p>
            </div>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Home Nickname <span className="text-gray-400 font-normal">(optional)</span></label>
            <input
              className={inputClass}
              placeholder="e.g., The Lake House"
              value={hi.home_nickname}
              onChange={(e) => updateIdentity('home_nickname', e.target.value)}
            />
            <p className={hintClass}>A friendly name for your binder cover.</p>
          </div>
          <div>
            <label className={labelClass}>Owner or Renter?</label>
            <select
              className={`w-full ${selectClass}`}
              value={hi.owner_renter}
              onChange={(e) => updateIdentity('owner_renter', e.target.value)}
            >
              <option value="owner">Owner</option>
              <option value="renter">Renter</option>
            </select>
            <p className={hintClass}>Affects which maintenance responsibilities apply.</p>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-5">
          <p className={labelClass}>System Locations</p>
          <p className={hintClass + ' mb-3 -mt-1'}>For each system, mark whether you know its location. If known, describe where it is.</p>

          <CompletionBar known={knownCount} total={LOCATIONS.length} />

          <div className="space-y-3">
            {LOCATIONS.map(({ key, label, why, feeds }) => {
              const loc = (cl as any)[key];
              const isKnown = loc.status === 'known';
              return (
                <div key={key} className={`rounded-lg border p-4 transition ${isKnown ? 'border-brand-200 bg-brand-50/40' : 'border-gray-200 bg-white'}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1 mr-3">
                      <span className="text-sm font-medium text-gray-700">{label}</span>
                      {!isKnown && (
                        <p className="text-[11px] text-gray-400 mt-0.5 leading-snug">{why}</p>
                      )}
                    </div>
                    <div className="flex rounded-md overflow-hidden border border-gray-200 flex-shrink-0">
                      <button
                        type="button"
                        onClick={() => updateLocation(key, 'status', 'known')}
                        className={`px-3.5 py-1.5 text-xs font-medium transition ${isKnown ? 'bg-brand-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
                      >
                        Known
                      </button>
                      <button
                        type="button"
                        onClick={() => updateLocation(key, 'status', 'unknown')}
                        className={`px-3.5 py-1.5 text-xs font-medium transition border-l border-gray-200 ${!isKnown ? 'bg-gray-700 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
                      >
                        Unknown
                      </button>
                    </div>
                  </div>
                  {isKnown && (
                    <div className="mt-3">
                      <input
                        className={inputClass}
                        placeholder="Where is it? (e.g., basement near water heater)"
                        value={loc.location}
                        onChange={(e) => updateLocation(key, 'location', e.target.value)}
                      />
                      <p className="text-xs text-brand-600 mt-1">Used in: {feeds}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {knownCount < LOCATIONS.length && (
            <div className="mt-4 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
              <p className="text-xs text-gray-600">
                <span className="font-semibold text-gray-700">Not sure where something is?</span> That's okay — leave it as "Unknown" and your binder will include a guide on how to locate it, plus a fill-in checklist page so you can update it later.
              </p>
            </div>
          )}
        </div>
      </div>
    </StepCard>
  );
}
