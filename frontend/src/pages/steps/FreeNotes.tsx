import StepCard from '../../components/StepCard';
import type { Profile } from '../../types';
import { hintClass, textareaClass } from '../../styles/form';

const PROMPTS = [
  'Recent renovations or repairs (e.g., new roof in 2023, re-plumbed the upstairs bathroom)',
  'Known issues or quirks (e.g., basement takes on water in heavy rain, back door sticks)',
  'Upcoming projects or concerns you want the binder to address',
  'Anything the AI should factor in that wasn\'t covered in earlier steps',
];

export default function FreeNotes({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  return (
    <StepCard title="Anything Else?" subtitle="This is your chance to tell us what we might have missed. The more context the AI has, the better your binder will be.">
      <div>
        <p className="text-sm font-semibold text-gray-800 mb-3">Things that might be helpful:</p>
        <ul className="space-y-1.5 mb-5">
          {PROMPTS.map((p) => (
            <li key={p} className="flex items-start gap-2 text-sm text-gray-500">
              <span className="text-gray-400 mt-0.5 flex-shrink-0">•</span>
              {p}
            </li>
          ))}
        </ul>
        <textarea
          className={`${textareaClass} h-40`}
          value={profile.free_notes.notes}
          onChange={(e) => onChange({ ...profile, free_notes: { notes: e.target.value } })}
          placeholder="Type anything you think we should know..."
        />
        <p className={hintClass}>Completely optional — but even a sentence or two can make a difference.</p>
      </div>
    </StepCard>
  );
}
