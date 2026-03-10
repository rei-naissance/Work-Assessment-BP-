import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';
import { inputClass, labelClass, hintClass, checkboxClass } from '../../styles/form';

export default function Household({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const h = profile.household;
  const update = (field: string, value: any) => {
    onChange({ ...profile, household: { ...h, [field]: value } });
  };

  return (
    <StepCard title="Household" subtitle="Tell us about who lives in your home so we can tailor safety and maintenance guidance.">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Adults</label>
            <input type="number" min={1} className={inputClass} value={h.num_adults} onChange={(e) => update('num_adults', Number(e.target.value))} />
          </div>
          <div>
            <label className={labelClass}>Children</label>
            <input type="number" min={0} className={inputClass} value={h.num_children} onChange={(e) => update('num_children', Number(e.target.value))} />
          </div>
        </div>
        <div className="space-y-4">
          <label className="flex items-center gap-2.5 cursor-pointer group">
            <input type="checkbox" checked={h.has_pets} onChange={() => update('has_pets', !h.has_pets)} className={checkboxClass} />
            <span className="text-sm text-gray-700 group-hover:text-gray-900 transition">Pets</span>
          </label>
          {h.has_pets && (
            <div className="ml-7">
              <input className={inputClass} placeholder="Pet types (e.g. dog, cat)" value={h.pet_types} onChange={(e) => update('pet_types', e.target.value)} />
              <p className={hintClass}>Enables pet-specific sitter instructions and safety guidance.</p>
            </div>
          )}
          <label className="flex items-center gap-2.5 cursor-pointer group">
            <input type="checkbox" checked={h.has_elderly} onChange={() => update('has_elderly', !h.has_elderly)} className={checkboxClass} />
            <span className="text-sm text-gray-700 group-hover:text-gray-900 transition">Elderly household members</span>
          </label>
          <label className="flex items-center gap-2.5 cursor-pointer group">
            <input type="checkbox" checked={h.has_allergies} onChange={() => update('has_allergies', !h.has_allergies)} className={checkboxClass} />
            <span className="text-sm text-gray-700 group-hover:text-gray-900 transition">Allergies or sensitivities</span>
          </label>
        </div>
      </div>
    </StepCard>
  );
}
