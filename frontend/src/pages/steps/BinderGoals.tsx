import { Icon } from '../../components/Icons';
import type { Profile, BinderGoals as BinderGoalsType } from '../../types';

const GOALS: { key: keyof BinderGoalsType; label: string; iconName: string; description: string; example: string }[] = [
  {
    key: 'emergency_preparedness',
    label: 'Emergency Preparedness',
    iconName: 'emergency',
    description: 'Know exactly what to do and who to call when something goes wrong.',
    example: 'Fire playbook, water shutoff guide, power outage protocol',
  },
  {
    key: 'guest_handoff',
    label: 'Guest & Sitter Handoff',
    iconName: 'checklist',
    description: 'Leave a complete guide so guests and sitters never need to call you.',
    example: 'WiFi, alarm codes, pet care, escalation contacts',
  },
  {
    key: 'maintenance_tracking',
    label: 'Maintenance Tracking',
    iconName: 'maintenance',
    description: 'Stay ahead of seasonal tasks and system upkeep.',
    example: 'HVAC filter schedule, seasonal checklists, service logs',
  },
  {
    key: 'new_homeowner',
    label: 'New Homeowner Guide',
    iconName: 'home',
    description: "Learn your home's systems, locations, and quirks all at once.",
    example: 'System locations, utility contacts, first-year maintenance',
  },
  {
    key: 'insurance_docs',
    label: 'Insurance & Documentation',
    iconName: 'document',
    description: 'Have policy info, inventory records, and claim contacts ready.',
    example: 'Policy numbers, claim phone, equipment inventory',
  },
  {
    key: 'vendor_organization',
    label: 'Vendor Organization',
    iconName: 'tools',
    description: 'Keep trusted service providers organized and accessible.',
    example: 'Plumber, electrician, HVAC tech, all in one place',
  },
];

interface Props {
  profile: Profile;
  onChange: (p: Profile) => void;
}

export default function BinderGoals({ profile, onChange }: Props) {
  const goals = profile.binder_goals;

  const toggle = (key: keyof BinderGoalsType) => {
    onChange({
      ...profile,
      binder_goals: { ...goals, [key]: !goals[key] },
    });
  };

  const selectedCount = Object.values(goals).filter(Boolean).length;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-6">
        <h2 className="text-lg font-semibold text-navy-900">What do you want from your binder?</h2>
        <p className="text-sm text-gray-500 mt-1">
          Select all that apply. This helps us prioritize which information matters most and show you exactly what to fill in.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        {GOALS.map((g) => {
          const selected = goals[g.key];
          return (
            <button
              key={g.key}
              type="button"
              onClick={() => toggle(g.key)}
              className={`text-left p-4 rounded-lg border-2 transition ${
                selected
                  ? 'border-brand-400 bg-brand-50/60 ring-2 ring-brand-200'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                  selected ? 'bg-brand-100 text-brand-600' : 'bg-gray-100 text-gray-400'
                }`}>
                  <Icon name={g.iconName} className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <span className={`block text-sm font-semibold ${selected ? 'text-brand-700' : 'text-gray-900'}`}>
                    {g.label}
                  </span>
                  <span className="block text-xs text-gray-500 mt-0.5">{g.description}</span>
                  <span className="block text-xs text-gray-400 mt-1.5 italic">{g.example}</span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {selectedCount === 0 && (
        <p className="text-xs text-gray-400 mt-4 text-center">
          No goals selected yet — we'll generate a well-rounded binder covering everything.
        </p>
      )}
      {selectedCount > 0 && (
        <p className="text-xs text-brand-600 mt-4 text-center font-medium">
          {selectedCount} goal{selectedCount !== 1 ? 's' : ''} selected — we'll prioritize the information that matters for {selectedCount === 1 ? 'this' : 'these'}.
        </p>
      )}
    </div>
  );
}
