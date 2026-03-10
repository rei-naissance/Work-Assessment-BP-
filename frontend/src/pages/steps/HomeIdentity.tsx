import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';

const HOME_TYPES = [
  { value: 'single_family', label: 'Single Family' },
  { value: 'condo', label: 'Condo' },
  { value: 'townhouse', label: 'Townhouse' },
  { value: 'apartment', label: 'Apartment' },
  { value: 'mobile', label: 'Mobile / Manufactured' },
];

import { inputClass, labelClass, selectClass, hintClass, titleCase } from '../../styles/form';

export default function HomeIdentity({
  profile,
  onChange,
}: {
  profile: Profile;
  onChange: (p: Profile) => void;
}) {
  const hi = profile.home_identity;
  const update = (field: string, value: string | number | null) => {
    onChange({ ...profile, home_identity: { ...hi, [field]: value } });
  };

  return (
    <StepCard title="Home Identity" subtitle="Start with the basics — where is your home and what type is it?">
      <div className="space-y-6">
        <fieldset className="border border-gray-200 rounded-lg p-5 bg-white">
          <legend className="text-xs font-semibold text-gray-500 px-2 uppercase tracking-wide">
            Address <span className="text-gray-400 font-normal">(optional)</span>
          </legend>
          <div className="space-y-3">
            <input
              className={inputClass}
              value={hi.address_line1}
              onChange={(e) => update('address_line1', e.target.value)}
              onBlur={(e) => update('address_line1', titleCase(e.target.value.trim()))}
              placeholder="Street address"
            />
            <input
              className={inputClass}
              value={hi.address_line2}
              onChange={(e) => update('address_line2', e.target.value)}
              onBlur={(e) => update('address_line2', titleCase(e.target.value.trim()))}
              placeholder="Apt, Suite, Unit, etc."
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                className={inputClass}
                value={hi.city}
                onChange={(e) => update('city', e.target.value)}
                onBlur={(e) => update('city', titleCase(e.target.value.trim()))}
                placeholder="City"
              />
              <input
                className={inputClass}
                value={hi.state}
                onChange={(e) => update('state', e.target.value)}
                onBlur={(e) => update('state', e.target.value.trim().toUpperCase())}
                placeholder="State"
              />
            </div>
          </div>
          <p className={hintClass}>Used for your binder cover page. You can skip this if you prefer.</p>
        </fieldset>

        <div>
          <label className={labelClass}>ZIP Code <span className="text-red-500">*</span></label>
          <input
            className={inputClass}
            value={hi.zip_code}
            onChange={(e) => update('zip_code', e.target.value)}
            maxLength={10}
            placeholder="e.g. 33101"
          />
          <p className={hintClass}>Your ZIP code enables region-specific modules — storm prep, climate-based maintenance, and local hazard guidance tailored to your area.</p>
        </div>

        <div>
          <label className={labelClass}>Home Type <span className="text-red-500">*</span></label>
          <select className={selectClass} value={hi.home_type} onChange={(e) => update('home_type', e.target.value)}>
            <option value="">Select your home type...</option>
            {HOME_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>
              Year Built <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={4}
              className={inputClass}
              value={hi.year_built ?? ''}
              onChange={(e) => {
                const v = e.target.value.replace(/\D/g, '');
                update('year_built', v ? Number(v) : null);
              }}
              placeholder="1995"
            />
          </div>
          <div>
            <label className={labelClass}>
              Square Feet <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={7}
              className={inputClass}
              value={hi.square_feet ?? ''}
              onChange={(e) => {
                const v = e.target.value.replace(/\D/g, '');
                update('square_feet', v ? Number(v) : null);
              }}
              placeholder="2200"
            />
          </div>
        </div>
      </div>
    </StepCard>
  );
}
