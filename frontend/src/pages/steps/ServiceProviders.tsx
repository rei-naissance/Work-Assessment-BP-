import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';
import { inputClass, labelClass, hintClass, checkboxClass, titleCase } from '../../styles/form';

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 10);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

const PROVIDER_INFO: Record<string, { why: string; scenario: string }> = {
  plumber: { why: 'A burst pipe at 2 AM is not the time to Google "emergency plumber near me."', scenario: 'Water Leak Playbook' },
  electrician: { why: 'Electrical issues can be dangerous. Having someone on file means faster, safer response.', scenario: 'Power Outage Playbook' },
  hvac_tech: { why: 'When your AC dies in July or heat fails in January, you need someone you can call immediately.', scenario: 'HVAC Failure Playbook' },
  handyman: { why: 'For everything that falls between specialized trades — a reliable handyman saves time and money.', scenario: 'General Maintenance Guide' },
  locksmith: { why: 'Locked out at midnight? This one number is worth its weight in gold.', scenario: 'Security Incident Playbook' },
  roofer: { why: 'Storm damage won\'t wait. Your binder will tell guests/sitters exactly who to call about roof leaks.', scenario: 'Severe Storm Playbook' },
  landscaper: { why: 'Seasonal lawn care, tree trimming, irrigation — gets woven into your seasonal checklists.', scenario: 'Seasonal Maintenance' },
  pool_service: { why: 'Pool chemistry and equipment maintenance are time-sensitive. Your binder tracks the schedule.', scenario: 'Pool Maintenance Guide' },
  pest_control: { why: 'Termite swarming? Wasp nest? Your binder will have the number ready in the relevant playbook.', scenario: 'Seasonal Maintenance' },
  restoration_company: { why: 'After water damage, fire, or mold — restoration companies need to start FAST to minimize damage.', scenario: 'Water Leak & Fire Playbooks' },
  appliance_repair: { why: 'Refrigerator dies with a full freezer? Dryer stops mid-cycle? Time matters.', scenario: 'Appliance Care Guides' },
  garage_door: { why: 'A broken garage door can strand your car or be a security risk.', scenario: 'Garage & Workspace Guide' },
};

function ProviderField({
  label, providerKey, name, phone, skip, onName, onPhone, onSkip,
}: {
  label: string; providerKey: string; name: string; phone: string; skip: boolean;
  onName: (v: string) => void; onPhone: (v: string) => void; onSkip: (v: boolean) => void;
}) {
  const info = PROVIDER_INFO[providerKey];
  const isFilled = name.trim() || phone.trim();
  const isEmpty = !isFilled && !skip;

  return (
    <div className={`rounded-lg border p-3 mb-3 transition ${skip ? 'border-gray-100 bg-gray-50 opacity-50' : isFilled ? 'border-emerald-200 bg-emerald-50/30' : 'border-amber-200 bg-amber-50/20'}`}>
      <div className="grid grid-cols-[1fr_1fr_1fr_auto] gap-3 items-stretch">
        <div className="flex items-center">
          <div>
            <span className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
              {isFilled && !skip && <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />}
              {isEmpty && <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />}
              {skip && <span className="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0" />}
              {label}
            </span>
          </div>
        </div>
        <input className={inputClass} placeholder="Name" value={name} onChange={(e) => onName(e.target.value)} onBlur={(e) => onName(titleCase(e.target.value.trim()))} disabled={skip} />
        <input className={inputClass} placeholder="(555) 555-1234" type="tel" value={phone} onChange={(e) => onPhone(formatPhone(e.target.value))} disabled={skip} />
        <label className="relative cursor-pointer group flex items-center px-1" title={`I don't have a ${label.toLowerCase()}`}>
          <input
            type="checkbox"
            checked={skip}
            onChange={(e) => onSkip(e.target.checked)}
            className={checkboxClass}
          />
          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap text-[11px] text-gray-500 bg-white border border-gray-200 shadow-sm rounded-md px-2 py-1 opacity-0 group-hover:opacity-100 transition pointer-events-none">
            Don't have one
          </span>
        </label>
      </div>
      {isEmpty && info && (
        <p className="text-[11px] text-amber-700 mt-1.5 pl-[3.5px] leading-snug">
          <span className="font-medium">Why?</span> {info.why} <span className="text-amber-500">Used in: {info.scenario}</span>
        </p>
      )}
    </div>
  );
}

function UtilityField({
  label, company, phone, accountNumber, skip, onCompany, onPhone, onAccountNumber, onSkip,
}: {
  label: string; company: string; phone: string; accountNumber: string; skip: boolean;
  onCompany: (v: string) => void; onPhone: (v: string) => void; onAccountNumber: (v: string) => void; onSkip: (v: boolean) => void;
}) {
  const isFilled = company.trim() || phone.trim();

  return (
    <div className={`rounded-lg border p-3 mb-3 transition ${skip ? 'border-gray-100 bg-gray-50 opacity-50' : isFilled ? 'border-emerald-200 bg-emerald-50/30' : 'border-amber-200 bg-amber-50/20'}`}>
      <div className="grid grid-cols-[1fr_1fr_1fr_1fr_auto] gap-3 items-stretch">
        <span className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
          {isFilled && !skip && <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />}
          {!isFilled && !skip && <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />}
          {skip && <span className="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0" />}
          {label}
        </span>
        <input className={inputClass} placeholder="Company" value={company} onChange={(e) => onCompany(e.target.value)} onBlur={(e) => onCompany(titleCase(e.target.value.trim()))} disabled={skip} />
        <input className={inputClass} placeholder="Account #" value={accountNumber} onChange={(e) => onAccountNumber(e.target.value)} disabled={skip} />
        <input className={inputClass} placeholder="(555) 555-1234" type="tel" value={phone} onChange={(e) => onPhone(formatPhone(e.target.value))} disabled={skip} />
        <label className="relative cursor-pointer group flex items-center px-1" title="I don't have this info">
          <input
            type="checkbox"
            checked={skip}
            onChange={(e) => onSkip(e.target.checked)}
            className={checkboxClass}
          />
          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap text-[11px] text-gray-500 bg-white border border-gray-200 shadow-sm rounded-md px-2 py-1 opacity-0 group-hover:opacity-100 transition pointer-events-none">
            Don't have this
          </span>
        </label>
      </div>
    </div>
  );
}

export default function ServiceProviders({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const cv = profile.contacts_vendors;

  const updateProvider = (key: string, field: string, value: string | boolean) => {
    onChange({ ...profile, contacts_vendors: { ...cv, [key]: { ...(cv as any)[key], [field]: value } } });
  };

  const updateUtility = (key: string, field: string, value: string | boolean) => {
    onChange({ ...profile, contacts_vendors: { ...cv, [key]: { ...(cv as any)[key], [field]: value } } });
  };

  const updateInsurance = (field: string, value: string | boolean) => {
    onChange({ ...profile, contacts_vendors: { ...cv, insurance: { ...cv.insurance, [field]: value } } });
  };

  // Completion tracking
  const providerKeys = ['plumber', 'electrician', 'hvac_tech', 'handyman', 'locksmith', 'roofer', 'landscaper', 'pool_service', 'pest_control', 'restoration_company', 'appliance_repair', 'garage_door'] as const;
  const utilityKeys = ['power', 'gas', 'water', 'isp'] as const;

  const filledProviders = providerKeys.filter((k) => {
    const p = (cv as any)[k];
    return p.skip || (p.name?.trim() || p.phone?.trim());
  }).length;
  const filledUtilities = utilityKeys.filter((k) => {
    const u = (cv as any)[k];
    return u.skip || (u.company?.trim() || u.phone?.trim());
  }).length;
  const insuranceFilled = cv.insurance.skip || cv.insurance.provider?.trim() || cv.insurance.claim_phone?.trim();
  const totalFilled = filledProviders + filledUtilities + (insuranceFilled ? 1 : 0);
  const totalFields = providerKeys.length + utilityKeys.length + 1;
  const pct = Math.round((totalFilled / totalFields) * 100);

  const insSkip = cv.insurance.skip;

  return (
    <StepCard title="Service Providers & Utilities" subtitle="Fill in what you have — for any you're missing, our AI can help you identify what to look for and include a ready-to-fill reference page.">
      <div className="space-y-6">
        {/* Impact callout */}
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="w-9 h-9 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-lg flex-shrink-0">📞</span>
            <div>
              <p className="text-sm font-semibold text-emerald-900">Every provider you add gets embedded into the right playbook</p>
              <p className="text-xs text-emerald-700 mt-0.5">Your plumber appears in the Water Leak Playbook. Your electrician appears in the Power Outage Playbook. Your HVAC tech appears in the HVAC Failure Playbook. <strong>In a crisis, your binder becomes a one-stop action plan — not just a phone book.</strong></p>
            </div>
          </div>
        </div>

        {/* Completion tracker */}
        <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${pct === 100 ? 'bg-emerald-50 border-emerald-200' : pct >= 50 ? 'bg-brand-50 border-brand-200' : 'bg-amber-50 border-amber-200'}`}>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className={`text-xs font-semibold ${pct === 100 ? 'text-emerald-700' : pct >= 50 ? 'text-brand-700' : 'text-amber-700'}`}>
                {pct === 100 ? 'All providers and utilities complete!' : `${totalFilled} of ${totalFields} filled or marked "Don't have"`}
              </span>
              <span className={`text-xs font-bold ${pct === 100 ? 'text-emerald-700' : pct >= 50 ? 'text-brand-700' : 'text-amber-700'}`}>{pct}%</span>
            </div>
            <div className="w-full h-1.5 bg-white/60 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${pct === 100 ? 'bg-emerald-500' : pct >= 50 ? 'bg-brand-500' : 'bg-amber-500'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          {pct < 50 && (
            <span className="text-[11px] text-amber-600 font-medium whitespace-nowrap">
              Amber items need your attention
            </span>
          )}
        </div>

        {/* HomeSure CTA */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="w-10 h-10 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center text-sm font-semibold flex-shrink-0">HS</span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-900">Need help finding trusted providers?</p>
              <p className="text-xs text-gray-600 mt-0.5 mb-2">
                HomeSure connects you with vetted, local service professionals — plumbers, electricians, HVAC techs, and more.
              </p>
              <a
                href="https://homesureapp.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-gray-700 hover:text-gray-900 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200 hover:border-gray-300 transition"
              >
                Find Providers on HomeSure
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Service Providers</p>
            <p className="text-[11px] text-gray-400">{filledProviders} of {providerKeys.length} complete</p>
          </div>

          {/* Core providers - highlighted */}
          <div className="mb-2">
            <p className="text-[11px] font-medium text-gray-500 mb-2 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              Critical — these are referenced in emergency playbooks
            </p>
            {(['plumber', 'electrician', 'hvac_tech', 'handyman', 'locksmith'] as const).map((key) => (
              <ProviderField
                key={key}
                providerKey={key}
                label={key === 'hvac_tech' ? 'HVAC Tech' : key.charAt(0).toUpperCase() + key.slice(1)}
                name={(cv as any)[key].name}
                phone={(cv as any)[key].phone}
                skip={(cv as any)[key].skip ?? false}
                onName={(v) => updateProvider(key, 'name', v)}
                onPhone={(v) => updateProvider(key, 'phone', v)}
                onSkip={(v) => updateProvider(key, 'skip', v)}
              />
            ))}
          </div>

          <div>
            <p className="text-[11px] font-medium text-gray-500 mb-2 flex items-center gap-1.5 mt-4">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              Recommended — these enhance your seasonal and specialty guides
            </p>
            {(['roofer', 'landscaper', 'pool_service', 'pest_control', 'restoration_company', 'appliance_repair', 'garage_door'] as const).map((key) => (
              <ProviderField
                key={key}
                providerKey={key}
                label={key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                name={(cv as any)[key].name}
                phone={(cv as any)[key].phone}
                skip={(cv as any)[key].skip ?? false}
                onName={(v) => updateProvider(key, 'name', v)}
                onPhone={(v) => updateProvider(key, 'phone', v)}
                onSkip={(v) => updateProvider(key, 'skip', v)}
              />
            ))}
          </div>
        </div>

        <div className="border-t border-gray-200 pt-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Utilities</p>
            <p className="text-[11px] text-gray-400">{filledUtilities} of {utilityKeys.length} complete</p>
          </div>
          <p className="text-[11px] text-gray-500 mb-3">Account numbers are included in your binder so you (or a guest) can call about outages without hunting for a bill.</p>
          {(['power', 'gas', 'water', 'isp'] as const).map((key) => (
            <UtilityField
              key={key}
              label={key === 'isp' ? 'Internet / ISP' : key.charAt(0).toUpperCase() + key.slice(1)}
              company={(cv as any)[key].company}
              phone={(cv as any)[key].phone}
              accountNumber={(cv as any)[key].account_number}
              skip={(cv as any)[key].skip ?? false}
              onCompany={(v) => updateUtility(key, 'company', v)}
              onPhone={(v) => updateUtility(key, 'phone', v)}
              onAccountNumber={(v) => updateUtility(key, 'account_number', v)}
              onSkip={(v) => updateUtility(key, 'skip', v)}
            />
          ))}
        </div>

        <div className="border-t border-gray-200 pt-5">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Homeowners / Renters Insurance</p>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-gray-500">Don't have this</span>
              <input
                type="checkbox"
                checked={insSkip}
                onChange={(e) => updateInsurance('skip', e.target.checked)}
                className={checkboxClass}
              />
            </label>
          </div>
          <p className={hintClass + ' mb-3'}>Your home insurance policy only — not auto, health, or life.</p>
          <div className={`bg-white border rounded-lg p-4 space-y-3 ${insSkip ? 'border-gray-100 opacity-40 pointer-events-none' : !insuranceFilled ? 'border-amber-200 bg-amber-50/20' : 'border-emerald-200 bg-emerald-50/30'}`}>
            {!insSkip && !insuranceFilled && (
              <p className="text-[11px] text-amber-700 font-medium">
                Your insurance claim number appears in fire, water, and storm playbooks — so you can file a claim immediately, not after searching for your policy documents.
              </p>
            )}
            <div className="grid sm:grid-cols-[1fr_1fr] gap-3">
              <div>
                <label className={labelClass}>Insurance Provider</label>
                <input className={inputClass} placeholder="e.g., State Farm, Allstate" value={cv.insurance.provider} onChange={(e) => updateInsurance('provider', e.target.value)} onBlur={(e) => updateInsurance('provider', titleCase(e.target.value.trim()))} disabled={insSkip} />
              </div>
              <div>
                <label className={labelClass}>Claims Phone</label>
                <input className={inputClass} placeholder="(555) 555-1234" type="tel" value={cv.insurance.claim_phone} onChange={(e) => updateInsurance('claim_phone', formatPhone(e.target.value))} disabled={insSkip} />
              </div>
            </div>
            <div>
              <label className={labelClass}>Policy Number</label>
              <input className={inputClass} placeholder="e.g., HO-123456789" value={cv.insurance.policy_number} onChange={(e) => updateInsurance('policy_number', e.target.value)} disabled={insSkip} />
            </div>
          </div>
        </div>
      </div>
    </StepCard>
  );
}
