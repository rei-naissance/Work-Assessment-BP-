const STEPS = [
  { label: 'Home' },
  { label: 'Goals' },
  { label: 'Features' },
  { label: 'Household' },
  { label: 'Locations' },
  { label: 'Contacts' },
  { label: 'Providers' },
  { label: 'Guest Mode' },
  { label: 'Preferences' },
  { label: 'Style' },
  { label: 'Notes' },
  { label: 'Review' },
];

interface StepperProps {
  current: number;
  onStepClick: (stepIndex: number) => void;
}

export default function Stepper({ current, onStepClick }: StepperProps) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-xs text-gray-500">
      {STEPS.map((s, i) => {
        const done = i < current;
        const active = i === current;
        const canClick = i !== current;

        const handleClick = () => {
          if (canClick) {
            onStepClick(i);
          }
        };

        return (
          <div key={s.label} className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleClick}
              className={`transition ${
                active
                  ? 'text-gray-900 font-semibold'
                  : done
                  ? 'text-gray-700'
                  : 'text-gray-400'
              } ${canClick ? 'hover:text-gray-900' : 'cursor-default'}`}
            >
              {s.label}
            </button>
            {i < STEPS.length - 1 && <span className="text-gray-300">•</span>}
          </div>
        );
      })}
    </div>
  );
}
