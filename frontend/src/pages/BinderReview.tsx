import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import type { ReadinessData, GoalReport, StepGroupItem } from '../types';
import { pageContainer, pageTitle, pageSubtitle, card, btnPrimary, btnSecondary } from '../styles/shared';
import { Icon } from '../components/Icons';
import { Skeleton } from '../components/Skeleton';

/* ── Goal metadata ─────────────────────────────────────────── */

const GOAL_META: Record<string, { label: string; iconName: string }> = {
  emergency_preparedness: { label: 'Emergency Preparedness', iconName: 'emergency' },
  guest_handoff: { label: 'Guest & Sitter Handoff', iconName: 'checklist' },
  maintenance_tracking: { label: 'Maintenance Tracking', iconName: 'maintenance' },
  new_homeowner: { label: 'New Homeowner Guide', iconName: 'home' },
  insurance_docs: { label: 'Insurance & Documentation', iconName: 'document' },
  vendor_organization: { label: 'Vendor Organization', iconName: 'tools' },
};

const STEP_LABELS: Record<number, string> = {
  0: 'Home Identity',
  1: 'Goals',
  2: 'Features',
  3: 'Household',
  4: 'Critical Locations',
  5: 'Emergency Contacts',
  6: 'Service Providers',
  7: 'Guest & Sitter Mode',
  8: 'Preferences',
  9: 'Style',
  10: 'Notes',
  11: 'Review',
};

/* ── Score ring SVG ────────────────────────────────────────── */

function ScoreRing({ score, size = 140 }: { score: number; size?: number }) {
  const r = (size - 16) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? 'text-green-500' : score >= 50 ? 'text-amber-500' : 'text-orange-500';

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="absolute inset-0 -rotate-90" viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="currentColor"
          className="text-gray-100" strokeWidth="8"
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="currentColor"
          className={color} strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <span className="text-3xl font-bold text-gray-800">{score}%</span>
    </div>
  );
}

/* ── Critical issues banner ───────────────────────────────── */

function CriticalBanner({ criticalCount, onGoToStep, stepGroups }: {
  criticalCount: number;
  onGoToStep: (s: number) => void;
  stepGroups: Record<string, StepGroupItem[]>;
}) {
  const firstCriticalStep = Object.entries(stepGroups)
    .sort(([a], [b]) => Number(a) - Number(b))
    .find(([, items]) => items.some((i) => i.weight === 'critical'));

  return (
    <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 mb-6">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Icon name="emergency" className="w-4.5 h-4.5 text-red-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-red-800">
            {criticalCount} critical item{criticalCount !== 1 ? 's' : ''} will leave gaps in your binder
          </p>
          <p className="text-xs text-red-600/80 mt-1 leading-relaxed">
            These fields directly impact the most important sections. Without them, key pages will show
            &ldquo;UNKNOWN&rdquo; placeholders instead of real information.
          </p>
          {firstCriticalStep && (
            <button
              onClick={() => onGoToStep(Number(firstCriticalStep[0]))}
              className="mt-2.5 inline-flex items-center gap-1.5 bg-red-600 text-white text-xs font-semibold px-4 py-1.5 rounded-lg hover:bg-red-700 transition"
            >
              Fix critical items now <span>&rarr;</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Goal impact card ──────────────────────────────────────── */

function GoalImpactCard({ goalKey, report, onGoToStep }: {
  goalKey: string;
  report: GoalReport;
  onGoToStep: (s: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = GOAL_META[goalKey] || { label: goalKey, iconName: 'help' };
  const scoreColor = report.score >= 80 ? 'text-green-600' : report.score >= 50 ? 'text-amber-600' : 'text-orange-600';
  const scoreBg = report.score >= 80 ? 'bg-green-50 border-green-200' : report.score >= 50 ? 'bg-amber-50 border-amber-200' : 'bg-orange-50 border-orange-200';
  const criticalMissing = report.missing.filter((m) => m.weight === 'critical').length;

  return (
    <div className={`${card} p-4 ${report.score < 50 ? 'ring-1 ring-orange-200' : ''}`}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left"
      >
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
            report.score >= 80 ? 'bg-green-50 text-green-600' : report.score >= 50 ? 'bg-amber-50 text-amber-600' : 'bg-orange-50 text-orange-600'
          }`}>
            <Icon name={meta.iconName} className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-gray-800">{meta.label}</span>
              <div className="flex items-center gap-2 flex-shrink-0">
                {criticalMissing > 0 && (
                  <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                    {criticalMissing} critical
                  </span>
                )}
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${scoreBg} ${scoreColor}`}>
                  {report.score}%
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1.5">
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    report.score >= 80 ? 'bg-green-500' : report.score >= 50 ? 'bg-amber-500' : 'bg-orange-500'
                  }`}
                  style={{ width: `${report.score}%` }}
                />
              </div>
              <span className="text-xs text-gray-400 flex-shrink-0">{report.filled_fields}/{report.total_fields}</span>
            </div>
          </div>
          <svg
            className={`w-4 h-4 text-gray-300 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
          {report.missing.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-400 mb-1.5">Missing</p>
              {report.missing.map((item, i) => (
                <div
                  key={i}
                  className={`rounded-lg px-3 py-2 mb-1.5 border ${
                    item.weight === 'critical'
                      ? 'bg-red-50/60 border-red-100'
                      : item.weight === 'important'
                      ? 'bg-amber-50/60 border-amber-100'
                      : 'bg-gray-50 border-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                        item.weight === 'critical' ? 'bg-red-400' : item.weight === 'important' ? 'bg-amber-400' : 'bg-gray-300'
                      }`} />
                      <span className="text-xs font-semibold text-gray-700">{item.field}</span>
                      {item.weight === 'critical' && (
                        <span className="text-[10px] font-bold text-red-600 uppercase">Critical</span>
                      )}
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); onGoToStep(item.step); }}
                      className="text-[10px] font-semibold text-brand-600 hover:text-brand-700 whitespace-nowrap"
                    >
                      Fix &rarr;
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{item.message}</p>
                </div>
              ))}
            </div>
          )}
          {report.present.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-400 mb-1.5">Completed</p>
              {report.present.map((item, i) => (
                <div key={i} className="flex items-start gap-2 px-3 py-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0 mt-1" />
                  <div>
                    <span className="text-xs font-medium text-gray-600">{item.field}</span>
                    <p className="text-xs text-gray-400">{item.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Step group card ───────────────────────────────────────── */

function StepGroupCard({ stepNum, items, onGoToStep }: {
  stepNum: number;
  items: StepGroupItem[];
  onGoToStep: (s: number) => void;
}) {
  const criticalCount = items.filter((i) => i.weight === 'critical').length;
  const hasCritical = criticalCount > 0;

  return (
    <div className={`${card} p-4 mb-3 ${hasCritical ? 'border-red-200 bg-red-50/30' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-gray-800">
            {STEP_LABELS[stepNum] || `Step ${stepNum + 1}`}
          </span>
          <span className="text-xs text-gray-400">
            {items.length} item{items.length !== 1 ? 's' : ''}
          </span>
          {hasCritical && (
            <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
              {criticalCount} critical
            </span>
          )}
        </div>
        <button
          onClick={() => onGoToStep(stepNum)}
          className="inline-flex items-center gap-1.5 bg-brand-600 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg hover:bg-brand-700 transition flex-shrink-0"
        >
          Go fix this <span>&rarr;</span>
        </button>
      </div>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <div
            key={i}
            className={`rounded-lg px-3 py-2 ${
              item.weight === 'critical'
                ? 'bg-red-50 border border-red-100'
                : item.weight === 'important'
                ? 'bg-amber-50/60 border border-amber-100'
                : 'bg-gray-50'
            }`}
          >
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                item.weight === 'critical' ? 'bg-red-400' : item.weight === 'important' ? 'bg-amber-400' : 'bg-gray-300'
              }`} />
              <span className="text-xs font-semibold text-gray-700">{item.field}</span>
              {item.weight === 'critical' && (
                <span className="text-[10px] font-bold text-red-600 uppercase">Critical</span>
              )}
              <span className="text-xs text-gray-400">· {item.goal_label}</span>
            </div>
            <p className="text-xs text-gray-500 mt-1 leading-relaxed">{item.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Main page ─────────────────────────────────────────────── */

export default function BinderReview() {
  const [data, setData] = useState<ReadinessData | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/profile/readiness')
      .then((r) => setData(r.data))
      .catch(() => navigate('/onboarding'))
      .finally(() => setLoading(false));
  }, [navigate]);

  const goToStep = (stepNum: number) => {
    localStorage.setItem('onboarding_step', String(stepNum));
    navigate('/onboarding');
  };

  if (loading) {
    return (
      <div className={pageContainer}>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96 mt-2" />
        <div className="grid lg:grid-cols-5 gap-6 mt-8">
          <div className="lg:col-span-2 space-y-4">
            <Skeleton className="h-44 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </div>
          <div className="lg:col-span-3 space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const goalsWereSelected = data.goals_were_selected;
  const hasGoals = data.active_goals.length > 0;
  const totalMissing = Object.values(data.step_groups).reduce((sum, items) => sum + items.length, 0);
  const totalCritical = Object.values(data.step_groups)
    .reduce((sum, items) => sum + items.filter((i) => i.weight === 'critical').length, 0);

  return (
    <div className={pageContainer}>
      {/* ── Page header ─────────────────────────────────────── */}
      <div className="mb-8">
        <h1 className={pageTitle}>Your Binder Readiness Review</h1>
        <p className={pageSubtitle}>
          {goalsWereSelected
            ? "Here's how complete your binder will be based on your goals."
            : "Here's how complete your binder will be. We checked everything since you didn't select specific goals."}
        </p>
      </div>

      {/* ── Two-column layout ───────────────────────────────── */}
      <div className="grid lg:grid-cols-5 gap-6 items-start">

        {/* ── LEFT COLUMN: Score + Goal cards ───────────────── */}
        <div className="lg:col-span-2 space-y-4">

          {/* Score card */}
          <div className={`${card} p-6`}>
            <div className="flex items-center gap-5">
              <ScoreRing score={data.overall_score} size={110} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-800">
                  {data.overall_score >= 80
                    ? 'Looking great!'
                    : data.overall_score >= 50
                    ? 'Good start'
                    : 'Needs attention'}
                </p>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                  {data.overall_score >= 80
                    ? 'Your binder will be comprehensive and personalized.'
                    : data.overall_score >= 50
                    ? `${totalMissing} item${totalMissing !== 1 ? 's' : ''} could make your binder significantly more useful.`
                    : 'Many sections will have placeholder gaps. A few minutes filling in details will make a big difference.'}
                </p>
                {totalCritical > 0 && (
                  <div className="flex items-center gap-1.5 mt-2">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    <span className="text-xs font-semibold text-red-600">
                      {totalCritical} critical item{totalCritical !== 1 ? 's' : ''}
                    </span>
                  </div>
                )}
                {totalMissing > 0 && totalCritical === 0 && (
                  <div className="flex items-center gap-1.5 mt-2">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span className="text-xs font-medium text-amber-600">
                      {totalMissing} item{totalMissing !== 1 ? 's' : ''} to improve
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Weight legend */}
            {totalMissing > 0 && (
              <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-100 text-[11px] text-gray-400">
                <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-red-400" /> Critical</span>
                <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> Important</span>
                <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-gray-300" /> Helpful</span>
              </div>
            )}
          </div>

          {/* No goals nudge */}
          {!goalsWereSelected && totalMissing > 0 && (
            <div className={`${card} p-4 border-brand-200 bg-brand-50/40`}>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                  <Icon name="sparkles" className="w-4 h-4 text-brand-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">Want a more focused review?</p>
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                    Select your goals and we'll prioritize what matters most to you.
                  </p>
                  <button
                    onClick={() => goToStep(1)}
                    className="mt-2 text-xs font-semibold text-brand-600 hover:text-brand-700"
                  >
                    Select your goals &rarr;
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Goal impact cards */}
          {hasGoals && (
            <div>
              <h2 className="text-sm font-semibold text-navy-900 mb-2">
                {goalsWereSelected ? 'Impact on Your Goals' : 'All Areas'}
              </h2>
              <div className="space-y-3">
                {data.active_goals.map((goal) => {
                  const report = data.goal_reports[goal];
                  if (!report) return null;
                  return (
                    <GoalImpactCard
                      key={goal}
                      goalKey={goal}
                      report={report}
                      onGoToStep={goToStep}
                    />
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT COLUMN: Action items ────────────────────── */}
        <div className="lg:col-span-3 space-y-4">

          {/* Critical banner */}
          {totalCritical > 0 && (
            <CriticalBanner
              criticalCount={totalCritical}
              onGoToStep={goToStep}
              stepGroups={data.step_groups}
            />
          )}

          {/* Step-grouped missing items */}
          {totalMissing > 0 && (
            <div>
              <div className="flex items-center gap-3 mb-3">
                <h2 className="text-lg font-semibold text-navy-900">What to Complete</h2>
                <span className="inline-flex items-center gap-1 bg-gray-100 text-gray-600 text-xs font-medium px-2.5 py-0.5 rounded-full">
                  {totalMissing} item{totalMissing !== 1 ? 's' : ''}
                </span>
                {totalCritical > 0 && (
                  <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-xs font-bold px-2.5 py-0.5 rounded-full">
                    {totalCritical} critical
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500 mb-4">
                Grouped by where to fix them. Click the button to jump directly to the right step.
              </p>
              {Object.entries(data.step_groups)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([stepStr, items]) => (
                  <StepGroupCard
                    key={stepStr}
                    stepNum={Number(stepStr)}
                    items={items}
                    onGoToStep={goToStep}
                  />
                ))}
            </div>
          )}

          {/* All complete */}
          {totalMissing === 0 && (
            <div className={`${card} p-8 text-center`}>
              <Icon name="sparkles" className="w-10 h-10 text-brand-400 mx-auto mb-3" />
              <p className="text-base font-semibold text-gray-800">Your profile is looking complete!</p>
              <p className="text-sm text-gray-500 mt-1">
                You're ready to generate a comprehensive, personalized binder.
              </p>
            </div>
          )}

          {/* CTAs */}
          <div className="flex items-center justify-between pt-6 border-t border-gray-200">
            <button
              onClick={() => navigate('/onboarding')}
              className={`${btnSecondary} px-6 py-2.5`}
            >
              &larr; Go Back & Complete More
            </button>
            <button
              onClick={() => navigate('/select-plan')}
              className={`${btnPrimary} px-8 py-2.5`}
            >
              I'm Ready &mdash; Choose My Plan &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
