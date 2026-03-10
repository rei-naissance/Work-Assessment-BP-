import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';

interface Option {
  value: string;
  label: string;
  description: string;
}

function CardRadioGroup({ label, hint, value, options, onChange }: {
  label: string;
  hint?: string;
  value: string;
  options: Option[];
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <p className="text-sm font-semibold text-gray-800 mb-1">{label}</p>
      {hint && <p className="text-xs text-gray-500 mb-3">{hint}</p>}
      <div className="grid grid-cols-3 gap-3">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={`text-left p-4 rounded-lg border transition shadow-sm ${
              value === o.value
                ? 'border-brand-400 bg-brand-50/60 ring-2 ring-brand-200'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <span className={`block text-sm font-semibold mb-1 ${value === o.value ? 'text-brand-700' : 'text-gray-900'}`}>{o.label}</span>
            <span className="block text-xs text-gray-500 leading-relaxed">{o.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Preferences({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const p = profile.preferences;
  const update = (field: string, value: string) => {
    onChange({ ...profile, preferences: { ...p, [field]: value } });
  };

  return (
    <StepCard title="Preferences" subtitle="These shape the depth and tone of your binder content.">
      <div className="space-y-8">
        <CardRadioGroup
          label="Maintenance Style"
          hint="How much upkeep guidance do you want?"
          value={p.maintenance_style}
          onChange={(v) => update('maintenance_style', v)}
          options={[
            { value: 'minimal', label: 'Minimal', description: 'Just the essentials. Focus on what breaks or needs urgent attention.' },
            { value: 'balanced', label: 'Balanced', description: 'A practical mix of preventive care and seasonal reminders.' },
            { value: 'thorough', label: 'Thorough', description: 'Comprehensive schedules covering every system and surface.' },
          ]}
        />
  <div className="border-t border-gray-200 pt-6">
          <CardRadioGroup
            label="DIY Comfort"
            hint="How hands-on are you with home projects?"
            value={p.diy_comfort}
            onChange={(v) => update('diy_comfort', v)}
            options={[
              { value: 'none', label: 'Hire It Out', description: 'I prefer to call a professional for most things.' },
              { value: 'moderate', label: 'Moderate', description: 'Comfortable with basic tasks, hire out the complex stuff.' },
              { value: 'advanced', label: 'DIY First', description: 'I tackle most projects myself before calling anyone.' },
            ]}
          />
        </div>
  <div className="border-t border-gray-200 pt-6">
          <CardRadioGroup
            label="Budget Priority"
            hint="What matters more when the binder recommends products or services?"
            value={p.budget_priority}
            onChange={(v) => update('budget_priority', v)}
            options={[
              { value: 'budget', label: 'Cost-Conscious', description: 'Prioritize affordable options and DIY alternatives.' },
              { value: 'balanced', label: 'Best Value', description: 'Balance quality and cost — spend where it counts.' },
              { value: 'premium', label: 'Quality First', description: 'Recommend the best option regardless of price.' },
            ]}
          />
        </div>
      </div>
    </StepCard>
  );
}
