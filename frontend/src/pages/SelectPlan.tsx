import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import type { Tier } from '../types';
import { pageContainer, pageTitle, pageSubtitle, card, sectionTitle, btnPrimary, btnSecondary } from '../styles/shared';
import { Icon } from '../components/Icons';

interface TierPreview { count: number; items: number }
interface Insights {
  unknown_locations: string[];
  known_locations: string[];
  active_premium_features: string[];
  household_needs: string[];
  missing_providers: string[];
  missing_utilities: string[];
  has_insurance: boolean;
  emergency_contact_count: number;
}
interface PreviewData {
  has_profile: boolean;
  standard?: TierPreview;
  premium?: TierPreview;
  insights?: Insights;
}

export default function SelectPlan() {
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [selectedTier, setSelectedTier] = useState<Tier>('premium');
  const [existingBinder, setExistingBinder] = useState<{ id: string; tier: string } | null>(null);
  const [pricing, setPricing] = useState<{ standard: number; premium: number } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user already has a binder (already paid)
    api.get('/binders/').then((r) => {
      if (r.data && r.data.length > 0) {
        setExistingBinder(r.data[0]);
      }
    }).catch(() => {});

    api.get('/binders/preview').then((r) => {
      if (!r.data.has_profile) navigate('/onboarding');
      setPreview(r.data);
    }).catch(() => navigate('/onboarding'));

    api.get('/payments/pricing').then((r) => {
      setPricing({
        standard: r.data.prices.standard,
        premium: r.data.prices.premium,
      });
    }).catch(() => {});
  }, [navigate]);

  const ins = preview?.insights;
  const std = preview?.standard;
  const prem = preview?.premium;
  const extraModules = prem && std ? prem.count - std.count : 0;

  const unknowns = ins?.unknown_locations || [];
  const premFeatures = ins?.active_premium_features || [];
  const hhNeeds = ins?.household_needs || [];
  const missingProviders = ins?.missing_providers || [];
  const missingUtilities = ins?.missing_utilities || [];
  const standardPrice = pricing ? pricing.standard / 100 : 59;
  const premiumPrice = pricing ? pricing.premium / 100 : 99;

  if (!preview) return null;

  return (
    <div className={pageContainer}>
      <div className="text-center mb-10">
        <h1 className={`${pageTitle} mb-2`}>Your Home Profile is Ready</h1>
        <p className={pageSubtitle}>
          {existingBinder
            ? "You've already purchased a plan. Your changes will be reflected in your existing binder."
            : "Here's what we found. Choose a plan to generate your binder."}
        </p>
      </div>

      {existingBinder && (
        <div className={`${card} mb-8 bg-green-50 border-green-200 px-6 py-4 text-center`}>
          <p className="text-sm text-green-800">
            <span className="font-semibold">You already have the {existingBinder.tier === 'premium' ? 'In-Depth' : 'Standard'} plan.</span>
            {' '}Your profile updates will be saved. Return to Dashboard to regenerate your binder with the latest changes.
          </p>
        </div>
      )}

      {/* ---- Gaps Section ---- */}
      {ins && unknowns.length > 0 && (
        <div className={`${card} mb-6 border-red-200 bg-red-50 p-4`}>
          <p className="text-sm font-semibold text-red-800 mb-2">
            {unknowns.length} critical location{unknowns.length > 1 ? 's' : ''} unknown
          </p>
          <p className="text-xs text-red-700 mb-3">
            The In-Depth plan generates AI walkthroughs to help you locate these based on your home type and year built.
          </p>
          <div className="flex flex-wrap gap-2">
            {unknowns.map((loc) => (
              <span key={loc} className="text-xs font-medium bg-white text-red-700 border border-red-200 px-3 py-1.5 rounded-full">{loc}</span>
            ))}
          </div>
        </div>
      )}

      {/* ---- Provider Gaps with HomeSure CTA ---- */}
      {ins && (missingProviders.length > 0 || missingUtilities.length > 0) && (
        <div className={`${card} mb-10 bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200 p-5`}>
          <div className="flex items-start gap-4">
            <span className="w-12 h-12 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0"><Icon name="tools" className="w-6 h-6" /></span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-emerald-900">
                {missingProviders.length + missingUtilities.length} service provider{missingProviders.length + missingUtilities.length > 1 ? 's' : ''} not yet added
              </p>
              <p className="text-xs text-emerald-700 mt-1 mb-3">
                Having trusted providers on file means faster response in emergencies. HomeSure connects you with vetted local professionals.
              </p>
              <div className="flex flex-wrap gap-2 mb-3">
                {missingProviders.map((p) => (
                  <span key={p} className="text-xs font-medium bg-white/80 text-emerald-700 border border-emerald-200 px-2.5 py-1 rounded-full">{p}</span>
                ))}
                {missingUtilities.map((u) => (
                  <span key={u} className="text-xs font-medium bg-white/80 text-emerald-700 border border-emerald-200 px-2.5 py-1 rounded-full">{u}</span>
                ))}
              </div>
              <a
                href="https://homesureapp.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 px-4 py-2 rounded-lg transition"
              >
                Find Providers on HomeSure
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* ---- Tier Selection ---- */}
      <h2 className={`${sectionTitle} mb-1`}>Choose Your Plan</h2>
      <p className="text-sm text-gray-500 mb-6">Both plans are one-time purchases. Your binder is yours forever.</p>

      <div className="grid md:grid-cols-2 gap-6 mb-6 items-stretch">
        {/* Standard */}
        <button
          type="button"
          onClick={() => setSelectedTier('standard')}
          className={`text-left border-2 rounded-lg p-6 flex flex-col transition relative ${
            selectedTier === 'standard'
              ? 'border-brand-500 ring-2 ring-brand-500/20 bg-white'
              : 'border-gray-200 bg-white hover:border-gray-300'
          }`}
        >
          {/* Spacer to match "Recommended" badge height */}
          <div className="h-4" />

          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-extrabold text-brand-700">${standardPrice}</span>
            <span className="text-sm text-gray-400">one-time</span>
          </div>
          <h3 className="text-lg font-bold text-navy-900 mb-1">Standard Binder</h3>
          <p className="text-sm text-gray-500 mb-4 min-h-[40px]">Core emergency, seasonal, and maintenance coverage.</p>

          {std && (
            <div className="flex gap-3 mb-4">
              <div className="bg-gray-50 rounded-lg px-3 py-2 text-center flex-1">
                <span className="block text-xl font-bold text-brand-700">{std.count}</span>
                <span className="text-xs text-gray-500">Modules</span>
              </div>
              <div className="bg-gray-50 rounded-lg px-3 py-2 text-center flex-1">
                <span className="block text-xl font-bold text-brand-700">{std.items}</span>
                <span className="text-xs text-gray-500">Action Items</span>
              </div>
            </div>
          )}

          <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 mb-4 min-h-[68px]">
            <p className="text-xs font-semibold text-gray-600">Template-based generation</p>
            <p className="text-xs text-gray-400 mt-0.5">Pre-written content matched to your region, home type, and season.</p>
          </div>

          <ul className="space-y-1.5 text-sm text-gray-600">
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Emergency procedures & shutoff guides</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Seasonal checklists</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Maintenance & cleaning schedules</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Region-specific hazard prep</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Home-type guide</li>
          </ul>

          {(premFeatures.length > 0 || hhNeeds.length > 0) && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Not included</p>
              <ul className="space-y-1 text-sm text-gray-400">
                {premFeatures.slice(0, 3).map((f) => (
                  <li key={f} className="flex items-start gap-2"><span className="mt-0.5">&#10007;</span> {f} guide</li>
                ))}
                {premFeatures.length > 3 && (
                  <li className="flex items-start gap-2"><span className="mt-0.5">&#10007;</span> +{premFeatures.length - 3} more system guides</li>
                )}
                {hhNeeds.length > 0 && (
                  <li className="flex items-start gap-2"><span className="mt-0.5">&#10007;</span> Household safety modules</li>
                )}
                <li className="flex items-start gap-2"><span className="mt-0.5">&#10007;</span> AI-personalized content</li>
              </ul>
            </div>
          )}

          <div className="mt-auto pt-5">
            <div className={`w-full py-2.5 rounded-xl font-semibold text-center text-sm transition ${
              selectedTier === 'standard' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-500'
            }`}>
              {selectedTier === 'standard' ? 'Selected' : 'Select Standard'}
            </div>
          </div>
        </button>

        {/* Premium */}
        <button
          type="button"
          onClick={() => setSelectedTier('premium')}
          className={`text-left border-2 rounded-lg p-6 flex flex-col transition relative ${
            selectedTier === 'premium'
              ? 'border-brand-500 ring-2 ring-brand-500/20 bg-brand-50/50'
              : 'border-brand-200 bg-brand-50/30 hover:border-brand-300'
          }`}
        >
          <span className="absolute -top-3 left-5 text-xs font-bold uppercase tracking-wide text-white bg-brand-600 px-3 py-1 rounded-full">Recommended</span>

          {/* Spacer to align with Standard card */}
          <div className="h-4" />

          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-extrabold text-brand-700">${premiumPrice}</span>
            <span className="text-sm text-gray-400">one-time</span>
          </div>
          <h3 className="text-lg font-bold text-navy-900 mb-1">In-Depth Binder</h3>
          <p className="text-sm text-gray-500 mb-4 min-h-[40px]">Everything in Standard, plus dedicated coverage for every system and need you told us about.</p>

          {prem && (
            <div className="flex gap-3 mb-4">
              <div className="bg-brand-100/60 rounded-lg px-3 py-2 text-center flex-1">
                <span className="block text-xl font-bold text-brand-700">{prem.count}</span>
                <span className="text-xs text-gray-500">Modules</span>
              </div>
              <div className="bg-brand-100/60 rounded-lg px-3 py-2 text-center flex-1">
                <span className="block text-xl font-bold text-brand-700">{prem.items}</span>
                <span className="text-xs text-gray-500">Action Items</span>
              </div>
            </div>
          )}

          <div className="bg-brand-100/50 border border-brand-200 rounded-lg px-3 py-2 mb-4 min-h-[68px]">
            <p className="text-xs font-semibold text-brand-800">AI-personalized content</p>
            <p className="text-xs text-brand-600/70 mt-0.5">
              An advanced model writes home-specific instructions using your address, systems, year built, household, and climate data — not generic templates.
            </p>
          </div>

          <ul className="space-y-1.5 text-sm text-gray-600">
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Emergency procedures & shutoff guides</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Seasonal checklists</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Maintenance & cleaning schedules</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Region-specific hazard prep</li>
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Home-type guide</li>
            {premFeatures.length > 0 && (
              <li className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#10003;</span>
                <span>
                  {premFeatures.length <= 3
                    ? premFeatures.join(', ')
                    : `${premFeatures.slice(0, 3).join(', ')} + ${premFeatures.length - 3} more`
                  } — dedicated SOPs
                </span>
              </li>
            )}
            {hhNeeds.map((need) => (
              <li key={need} className="flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#10003;</span>
                <span>{need}</span>
              </li>
            ))}
            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">&#10003;</span> Landscaping & drainage suite</li>
          </ul>

          <div className="mt-auto pt-5">
            <div className={`w-full py-2.5 rounded-xl font-semibold text-center text-sm transition ${
              selectedTier === 'premium' ? 'bg-brand-600 text-white' : 'bg-brand-100 text-brand-600'
            }`}>
              {selectedTier === 'premium' ? 'Selected' : 'Select In-Depth'}
            </div>
          </div>
        </button>
      </div>

      {/* Upsell when standard selected */}
      {selectedTier === 'standard' && (
        <div className="bg-gradient-to-r from-brand-50 to-brand-100/40 border border-brand-200 rounded-lg p-6 mb-6">
          <h3 className="text-sm font-bold text-brand-800 mb-2">
            For $40 more, your binder is written specifically for your home.
          </h3>
          <p className="text-sm text-brand-700/70 mb-4">
            The In-Depth plan uses an advanced AI model that reads your full profile — address, year built, systems, household, and climate zone — and writes instructions tailored to your home. Not templates. Not generic checklists. Content that references your actual setup.
          </p>
          {(premFeatures.length > 0 || hhNeeds.length > 0) && (
            <>
              <p className="text-xs font-semibold text-brand-800 mb-2">
                Plus, {extraModules} additional module{extraModules !== 1 ? 's' : ''} covering systems you told us about:
              </p>
              <div className="flex flex-wrap gap-2 mb-4">
                {premFeatures.map((f) => (
                  <span key={f} className="text-xs font-medium bg-white/80 border border-brand-200 text-brand-700 px-2.5 py-1.5 rounded-full">{f}</span>
                ))}
                {hhNeeds.map((n) => (
                  <span key={n} className="text-xs font-medium bg-white/80 border border-brand-200 text-brand-700 px-2.5 py-1.5 rounded-full">{n.split(' — ')[0]}</span>
                ))}
              </div>
            </>
          )}
          {unknowns.length > 0 && (
            <p className="text-xs text-brand-700/70 mb-4">
              You marked {unknowns.length} system{unknowns.length > 1 ? 's' : ''} as unknown — the In-Depth plan generates location-finding walkthroughs specific to your home type and year built.
            </p>
          )}
          <button type="button" onClick={() => setSelectedTier('premium')} className={`${btnPrimary} px-6 py-2.5 rounded-full`}>
            Upgrade to In-Depth — $99
          </button>
        </div>
      )}

      {/* Continue */}
      <div className="flex items-center justify-between mt-8">
        <button onClick={() => navigate('/onboarding')} className={`${btnSecondary} px-5 py-2.5 rounded-full`}>
          Edit Responses
        </button>
        {existingBinder ? (
          <button
            onClick={() => navigate('/dashboard')}
            className={`${btnPrimary} px-8 py-2.5 rounded-full`}
          >
            Return to Dashboard
          </button>
        ) : (
          <button
            onClick={() => navigate('/checkout', { state: { tier: selectedTier } })}
            className={`${btnPrimary} px-8 py-2.5 rounded-full`}
          >
            Continue to Payment — {selectedTier === 'premium' ? '$99' : '$59'}
          </button>
        )}
      </div>
    </div>
  );
}
