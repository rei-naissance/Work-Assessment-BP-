import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';

const TONE_OPTIONS = [
  {
    value: 'friendly',
    label: 'Conversational',
    description: 'Warm, approachable language. Reads like advice from a knowledgeable neighbor.',
    sample: '"When the temperature drops below freezing, you\'ll want to open your cabinet doors to keep pipes from freezing up."',
  },
  {
    value: 'professional',
    label: 'Professional',
    description: 'Clear, polished, and to the point. Reads like a well-written manual.',
    sample: '"Open cabinet doors beneath sinks during freezing temperatures to allow warm air circulation and prevent pipe freezing."',
  },
  {
    value: 'concise',
    label: 'Just the Facts',
    description: 'Minimal prose. Bullet points, checklists, and direct instructions only.',
    sample: '"Below 32°F: Open cabinet doors under sinks. Allow faucets to drip. Insulate exposed pipes."',
  },
];

export default function OutputTone({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const ot = profile.output_tone;
  const update = (field: string, value: string) => {
    onChange({ ...profile, output_tone: { ...ot, [field]: value } });
  };

  return (
    <StepCard title="Binder Style" subtitle="Choose how the AI writes your binder content. All options are professional — this controls the voice.">
      <div className="space-y-3">
        {TONE_OPTIONS.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => update('tone', o.value)}
            className={`w-full text-left p-5 rounded-lg border transition shadow-sm ${
              ot.tone === o.value
                ? 'border-brand-400 bg-brand-50/60 ring-2 ring-brand-200'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <span className={`text-sm font-semibold ${ot.tone === o.value ? 'text-brand-700' : 'text-gray-900'}`}>{o.label}</span>
                <p className="text-xs text-gray-500 mt-0.5">{o.description}</p>
              </div>
              <div className={`w-5 h-5 rounded-full border-2 flex-shrink-0 mt-0.5 flex items-center justify-center ${
                ot.tone === o.value ? 'border-brand-600 bg-brand-600' : 'border-gray-300'
              }`}>
                {ot.tone === o.value && <div className="w-2 h-2 rounded-full bg-white" />}
              </div>
            </div>
            <div className="mt-3 bg-white border border-gray-200 rounded-lg px-4 py-3">
              <p className="text-[11px] text-gray-400 uppercase tracking-wider font-semibold mb-1">Example</p>
              <p className="text-sm text-gray-600 leading-relaxed">{o.sample}</p>
            </div>
          </button>
        ))}
      </div>
    </StepCard>
  );
}
