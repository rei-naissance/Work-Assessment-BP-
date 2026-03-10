import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import api from '../api';
import { card, cardPadded } from '../styles/shared';
import { Icon, IconBadge } from '../components/Icons';

/* ── Static content data ────────────────────────────────────────── */

const HOW_IT_WORKS = [
  { num: '1', label: 'Tell us about your home', desc: 'Walk through our 12-step wizard — address, ZIP, home type, year built, systems, household members, emergency contacts, service providers, and preferences. The more you share, the more tailored your binder becomes.', iconName: 'home' },
  { num: '2', label: 'We match your modules', desc: 'Our rules engine cross-references your profile against 87 modules — filtering by region, home type, installed systems, household needs, and comfort level to build a binder that fits your home exactly.', iconName: 'puzzle' },
  { num: '3', label: 'Get your binder', desc: 'We ship you a professionally printed binder organized into 8 sections. Need to make changes? Update your profile anytime and download individual sections to print, or request a new copy for just the cost of shipping.', iconName: 'document' },
];

const WHATS_INCLUDED = [
  { iconName: 'emergency', title: 'Emergency Playbooks', desc: 'Quick-reference cards and step-by-step procedures for fire, water leaks, power outages, HVAC failure, storms, and security incidents.', count: 9, details: ['Emergency Quick Start Cards', 'Fire Playbook', 'Water Leak Playbook', 'Power Outage Playbook', 'HVAC Failure Playbook', 'Storm Playbook', 'Security Incident Playbook', 'Gas Leak Procedure', 'Medical Emergency Guide'] },
  { iconName: 'seasonal', title: 'Seasonal Maintenance', desc: 'Spring, summer, fall, and winter checklists plus general upkeep — GFCI testing, water heater, caulking, appliances, and cleaning schedules.', count: 7, details: ['Spring Checklist', 'Summer Checklist', 'Fall Checklist', 'Winter Checklist', 'General Maintenance', 'Appliance Care', 'Cleaning Schedules'] },
  { iconName: 'gear', title: 'System-Specific SOPs', desc: 'Pool, hot tub, septic, well water, solar, HVAC, EV charger, appliances, and more.', count: 30, details: ['Pool', 'Hot Tub / Spa', 'Septic System', 'Well Water', 'Water Softener', 'Water Filtration', 'Sump Pump', 'Solar Panels', 'Generator', 'EV Charger', 'Central Air', 'Heat Pump', 'Radiant Heat', 'Window AC', 'Fireplace', 'Water Heater', 'Roof', 'Plumbing', 'Electrical Panel', 'Garage', 'Basement', 'Attic', 'Security System', 'Smart Home', 'Sprinklers', 'Washer / Dryer', 'Dishwasher', 'Refrigerator', 'Garbage Disposal', 'Radon Mitigation'] },
  { iconName: 'house', title: 'Home Type Guides', desc: 'SOPs tailored to single family, condo/HOA, townhouse, apartment, and mobile homes.', count: 5, details: ['Single Family', 'Condo / HOA', 'Townhouse', 'Apartment', 'Mobile Home'] },
  { iconName: 'tree', title: 'Landscaping & Outdoors', desc: 'Lawn care, trees, seasonal landscaping, grading, and drainage management.', count: 5, details: ['Lawn Care', 'Tree Maintenance', 'Seasonal Landscaping', 'Grading & Drainage', 'Outdoor Structures'] },
  { iconName: 'family', title: 'Household Safety', desc: 'Child-proofing, pet safety, elderly accessibility, air quality, and home inventory checklists.', count: 6, details: ['Child-Proofing', 'Pet Safety', 'Elderly Accessibility', 'Air Quality', 'Equipment Inventory', 'Emergency Supply Kit'] },
  { iconName: 'contacts', title: 'Contacts & Vendors', desc: 'Emergency contacts, service providers, utilities, and insurance — organized and ready when you need them.', count: 5, details: ['Emergency Contacts', 'Service Providers', 'Utility Companies', 'Insurance Info', 'Neighbor Contacts'] },
  { iconName: 'guest_safety', title: 'Guests, Sitters & Rentals', desc: 'House rules, alarm instructions, pet care, escalation contacts — everything a guest, sitter, or short-term renter needs.', count: 5, details: ['Guest Instructions', 'Alarm & Security', 'Pet Care Info', 'Escalation Contacts', 'Rental Expectations'] },
  { iconName: 'party', title: 'Events & Hosting', desc: 'Prep checklists for hosting gatherings, conferences, weddings, and seasonal entertaining at your home.', count: 4, details: ['Event Prep Checklist', 'Guest Accommodations', 'Vendor Coordination', 'Post-Event Cleanup'] },
];

const REGIONS = [
  { name: 'Northeast', tagline: 'Harsh winters, coastal storms, and aging infrastructure', states: 'CT, ME, MA, NH, NJ, NY, PA, RI, VT', modules: ['Winter Prep', 'Pest Prevention', 'Ice Dam & Roof', 'Energy Efficiency', 'Coastal Flooding'], img: 'https://images.unsplash.com/photo-1548777123-e216912df7d8?w=1600&q=90' },
  { name: 'Southeast', tagline: 'Humidity, hurricanes, extreme heat, and year-round pest pressure', states: 'AL, AR, DE, DC, FL, GA, KY, LA, MD, MS, NC, OK, SC, TN, TX, VA, WV', modules: ['Hurricane & Storm', 'Humidity & Moisture', 'Pest Control', 'Extreme Heat', 'Energy & Cooling'], img: 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=1600&q=90' },
  { name: 'Midwest', tagline: 'Tornadoes, freeze cycles, and foundation shifting', states: 'IA, IL, IN, KS, MI, MN, MO, ND, NE, OH, SD, WI', modules: ['Tornado & Storm', 'Foundation & Soil', 'Winter Freeze', 'Basement Flooding', 'Insulation & Energy'], img: 'https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=1600&q=90' },
  { name: 'West', tagline: 'Wildfire, seismic activity, extreme heat, and drought', states: 'AK, AZ, CA, CO, HI, ID, MT, NM, NV, OR, UT, WA, WY', modules: ['Wildfire & Defensible Space', 'Earthquake Prep', 'Extreme Heat', 'Water Conservation', 'Mudslide & Erosion'], img: 'https://images.unsplash.com/photo-1449844908441-8829872d2607?w=1600&q=90' },
];

const SYSTEMS = [
  'Pool', 'Hot Tub / Spa', 'Garage', 'Basement', 'Attic', 'Fireplace',
  'Water Heater', 'Roof', 'Plumbing', 'Electrical Panel',
  'Septic', 'Well Water', 'Water Softener', 'Water Filtration', 'Sump Pump',
  'Solar Panels', 'Generator', 'EV Charger',
  'Sprinklers', 'Security System', 'Smart Home',
  'Washer / Dryer', 'Dishwasher', 'Refrigerator', 'Garbage Disposal',
  'Radon Mitigation',
  'Central Air', 'Heat Pump', 'Radiant Heat', 'Window AC',
];

const FAQ = [
  { q: 'How is this different from a generic home checklist?', a: 'Generic checklists give everyone the same list. BinderPro uses a rules engine that cross-references your ZIP code, home type, installed systems, household members, and preferences to assemble a binder unique to your home. A pool owner in Florida gets a completely different binder than a condo renter in Vermont.' },
  { q: 'What exactly do I receive?', a: 'We ship you a professionally printed binder organized into 8 sections — emergency quick start, home profile, emergency playbooks, guest & sitter mode, maintenance guides, home inventory, contacts & vendors, and an appendix. You also get full digital access so you can download or reprint any section at any time.' },
  { q: 'What if I don\'t know all the answers during setup?', a: 'That\'s completely fine — and actually part of the point. The setup process helps you take stock of what you know and what you don\'t, while also setting intentions for how you want your home to run. Any field left blank becomes a "to be filled in" placeholder in your binder. As you learn, update your profile — your binder grows with you, turning unknowns into a proactive plan.' },
  { q: 'Can I update my binder after I receive it?', a: 'Yes. Your profile is always editable. When you make changes — new service provider, updated contacts, a system you added or removed — you can download the updated sections to print and swap into your binder, or request a freshly printed copy for just the cost of shipping.' },
  { q: 'Who is this for?', a: 'Anyone responsible for a home:', bullets: ['First-time homeowners getting organized from day one', 'Long-time owners who\'ve never had a system in place', 'Landlords preparing rental or investment properties', 'Parents who want their household to run smoothly if they\'re not around', 'Anyone hosting guests, sitters, or short-term renters'], after: 'If your home has systems, contacts, and routines — this is for you.' },
  { q: 'Can I use this for a rental property or guest house?', a: 'Absolutely. The Guest & Sitter Mode section is built for exactly this — house rules, alarm instructions, pet care details, escalation contacts, and rental expectations. It\'s everything a guest, sitter, or short-term renter needs to take care of your home.' },
  { q: 'Is my information private?', a: 'Your profile is stored securely and never shared or sold. We use it only to build your binder. Your data stays on file so you can log back in, make updates, and regenerate anytime without starting over. Moving to a new home? Use our "New Home" path to start a fresh profile while keeping your account — no need to re-enter contacts and preferences that carry over.' },
  { q: 'Why a physical binder and not just an app?', a: 'When the power is out, your phone is dead, or a guest needs instructions — a physical binder on the shelf is always accessible. That said, you get digital access too, so you have both. The physical format also makes it easy to hand to a contractor, sitter, or family member without sharing logins.' },
];

/* ── Component ──────────────────────────────────────────────────── */

export default function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const cta = () => navigate(isAuthenticated ? '/dashboard' : '/login');
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [regionIdx, setRegionIdx] = useState(0);
  const [expandedCard, setExpandedCard] = useState<number | null>(null);
  const [pricing, setPricing] = useState<{ standard: number; premium: number } | null>(null);

  useEffect(() => {
    api.get('/payments/pricing').then((r) => {
      setPricing({
        standard: r.data.prices.standard,
        premium: r.data.prices.premium,
      });
    }).catch(() => {});
  }, []);

  const standardPrice = pricing ? pricing.standard / 100 : 59;
  const premiumPrice = pricing ? pricing.premium / 100 : 99;

  return (
    <div className="min-h-screen">
      {/* ─── HERO ─── */}
      <section className="relative bg-gradient-to-br from-brand-800 via-brand-700 to-brand-900 text-white overflow-hidden">
        {/* Decorative shapes */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-brand-600/30 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-coral-500/20 rounded-full blur-3xl translate-y-1/2 -translate-x-1/3" />

        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 pt-12 pb-28 text-center">
          <img
            src="/logo.png"
            alt="BinderPro"
            className="mx-auto h-12 sm:h-14 w-auto max-w-[280px] object-contain brightness-0 invert mb-8"
          />
          <span className="inline-block text-sm font-semibold bg-white/10 backdrop-blur border border-white/20 px-4 py-1.5 rounded-full mb-6">
            87 modules &middot; 640+ action items &middot; 8 organized sections
          </span>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl leading-tight">
            Your home deserves<br />an operating manual.
          </h1>
          <p className="mt-6 text-lg text-brand-100 max-w-2xl mx-auto leading-relaxed">
            Think about everything that runs through your home — maintenance, emergencies, services, seasonal care, contacts, inventory. BinderPro organizes all of it into one personalized reference guide, so nothing falls through the cracks.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button onClick={cta} className="px-10 py-4 bg-white text-brand-700 text-lg font-bold rounded-full shadow-xl hover:shadow-2xl hover:scale-105 transition-all">
              Build Your Binder
            </button>
            <a href="#why-it-matters" className="px-6 py-2.5 border-2 border-white text-white font-semibold rounded-full hover:bg-white/10 flex items-center gap-2 transition-all">
              Why it matters <span className="text-lg">↓</span>
            </a>
          </div>
        </div>

        {/* Wave divider */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
            <path d="M0 80V40C240 70 480 80 720 60C960 40 1200 10 1440 30V80H0Z" fill="white"/>
          </svg>
        </div>
      </section>

      {/* ─── WHY IT MATTERS (video + messaging) ─── */}
      <section id="why-it-matters" className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-sm font-semibold text-brand-600 tracking-wide mb-3">More Than a Binder</p>

          <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
            {/* Left: messaging */}
            <div>
              <h2 className="font-display text-3xl text-navy-900 mb-4">The first step in getting your life in order.</h2>
              <p className="text-gray-500 leading-relaxed mb-6">
                Your home is the hub of your life — services, maintenance, emergencies, finances, contacts, seasonal routines. Most of it lives in your head or scattered across drawers and apps. BinderPro is the first step in organizing all of it with intention: knowing what you have, who to call, and what to do when something breaks.
              </p>
              <blockquote className="border-l-4 border-brand-400 pl-5 py-2">
                <p className="text-lg text-navy-800 italic leading-relaxed">"Give me six hours to chop down a tree and I will spend the first four sharpening the axe."</p>
                <footer className="mt-2 text-sm text-gray-400">— Abraham Lincoln</footer>
              </blockquote>
            </div>

            {/* Right: video placeholder */}
            <div>
              <div className="relative aspect-video bg-gray-100 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center overflow-hidden">
                <div className="text-center">
                  <div className="w-16 h-16 rounded-full bg-brand-600/10 flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-brand-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                  </div>
                  <p className="text-sm font-semibold text-gray-500">Why BinderPro?</p>
                  <p className="text-xs text-gray-400 mt-1">Video coming soon</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto text-center">
            <div>
              <p className="text-3xl font-extrabold text-brand-700 mb-1">Organization</p>
              <p className="text-sm text-gray-500">Every system, contact, and procedure in one place — not scattered across your head, drawers, and apps.</p>
            </div>
            <div>
              <p className="text-3xl font-extrabold text-brand-700 mb-1">Intention</p>
              <p className="text-sm text-gray-500">Setting up your profile forces you to take stock of what you have — the first step to managing it well.</p>
            </div>
            <div>
              <p className="text-3xl font-extrabold text-brand-700 mb-1">Preparedness</p>
              <p className="text-sm text-gray-500">When something breaks at 2 AM, you'll know exactly where to look and who to call.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section className="py-20 bg-brand-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-center text-sm font-semibold text-brand-600 tracking-wide mb-3">Simple as 1-2-3</p>
          <h2 className="font-display text-3xl text-navy-900 text-center mb-14">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-10">
            {HOW_IT_WORKS.map((s) => (
              <div key={s.num} className="text-center group">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-lg bg-white text-gray-600 mb-5 group-hover:scale-105 transition-transform">
                  <Icon name={s.iconName} className="w-6 h-6" />
                </div>
                <div className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-brand-600 text-white text-xs font-bold mb-3">{s.num}</div>
                <h3 className="font-semibold text-navy-800 text-lg mb-2">{s.label}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── WHAT'S INCLUDED ─── */}
      <section id="whats-included" className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-center text-sm font-semibold text-brand-600 tracking-wide mb-3">Comprehensive Coverage</p>
          <h2 className="font-display text-3xl text-navy-900 text-center mb-3">What's Inside Your Binder</h2>
          <p className="text-center text-gray-500 mb-12 max-w-xl mx-auto">Every binder pulls from our library of <strong className="text-brand-700">87 modules</strong> and <strong className="text-brand-700">640+ action items</strong>, organized into 8 sections.</p>
          <div className="flex flex-col gap-6">
            {[0, 3, 6].map((rowStart) => {
              const rowItems = WHATS_INCLUDED.slice(rowStart, rowStart + 3);
              const expandedInRow = expandedCard !== null && expandedCard >= rowStart && expandedCard < rowStart + 3 ? expandedCard : null;
              const expandedItem = expandedInRow !== null ? WHATS_INCLUDED[expandedInRow] : null;
              return (
                <div key={rowStart}>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {rowItems.map((f, j) => {
                      const idx = rowStart + j;
                      return (
                        <div key={f.title} className={`${card} bg-brand-50 border-brand-100 rounded-lg p-6 transition-all flex flex-col ${expandedInRow === idx ? 'border-brand-300 ring-1 ring-brand-300' : ''}`}>
                          <div className="flex items-start justify-between mb-3">
                            <IconBadge name={f.iconName} size="lg" />
                            <button
                              onClick={() => setExpandedCard(expandedCard === idx ? null : idx)}
                              className="text-xs font-semibold text-brand-600 bg-brand-100 px-2.5 py-1 rounded-full hover:bg-brand-200 transition cursor-pointer"
                            >
                              {f.count} module{f.count > 1 ? 's' : ''} {expandedCard === idx ? '▲' : '▼'}
                            </button>
                          </div>
                          <h3 className="font-semibold text-navy-800 mb-1.5">{f.title}</h3>
                          <p className="text-sm text-gray-500 leading-relaxed flex-1">{f.desc}</p>
                        </div>
                      );
                    })}
                  </div>
                  {expandedItem && (
                    <div className={`${card} mt-3 border-brand-200 p-5`}>
                      <div className="flex items-center gap-2 mb-3">
                        <Icon name={expandedItem.iconName} className="w-5 h-5 text-brand-600" />
                        <h4 className="font-semibold text-navy-800 text-sm">{expandedItem.title} — Included Modules</h4>
                      </div>
                      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-1.5">
                        {expandedItem.details.map((d) => (
                          <span key={d} className="text-sm text-gray-600 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 flex-shrink-0" />
                            {d}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── REGIONS ─── */}
      <section className="py-20 bg-brand-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-center text-sm font-semibold text-brand-600 tracking-wide mb-2">Location-Aware</p>
          <h2 className="font-display text-3xl text-navy-900 text-center mb-2">Region-Specific Guidance</h2>
          <p className="text-center text-gray-500 mb-10 max-w-md mx-auto">Your ZIP code unlocks specialized modules for your area.</p>
          <div className="max-w-2xl mx-auto">
            <div className="rounded-lg shadow-xl overflow-hidden relative">
              <img src={REGIONS[regionIdx].img} alt={REGIONS[regionIdx].name} className="absolute inset-0 w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
              <div className="relative p-10 pt-28">
                <h3 className="font-display text-4xl font-bold text-white text-center mb-2 drop-shadow-lg">{REGIONS[regionIdx].name}</h3>
                <p className="text-white/90 text-base font-medium text-center mb-6">{REGIONS[regionIdx].tagline}</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {REGIONS[regionIdx].modules.map((m) => (
                    <span key={m} className="text-sm font-medium px-4 py-1.5 rounded-full bg-white/20 text-white backdrop-blur-md border border-white/10">{m}</span>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-center gap-4 mt-6">
              <button onClick={() => setRegionIdx((regionIdx - 1 + REGIONS.length) % REGIONS.length)} className="w-10 h-10 rounded-full bg-white border border-gray-200 shadow-sm flex items-center justify-center text-gray-500 hover:text-brand-600 hover:border-brand-300 transition">
                ←
              </button>
              <div className="flex gap-2">
                {REGIONS.map((r, i) => (
                  <button key={r.name} onClick={() => setRegionIdx(i)} className={`w-2.5 h-2.5 rounded-full transition ${i === regionIdx ? 'bg-brand-600 scale-125' : 'bg-gray-300 hover:bg-gray-400'}`} />
                ))}
              </div>
              <button onClick={() => setRegionIdx((regionIdx + 1) % REGIONS.length)} className="w-10 h-10 rounded-full bg-white border border-gray-200 shadow-sm flex items-center justify-center text-gray-500 hover:text-brand-600 hover:border-brand-300 transition">
                →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ─── SYSTEMS ─── */}
      <section className="py-20 bg-gradient-to-br from-brand-800 to-brand-900 text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-center text-sm font-semibold text-brand-300 tracking-wide mb-3">Feature-Matched</p>
          <h2 className="font-display text-3xl text-center mb-3">30 Home Systems Covered</h2>
          <p className="text-center text-brand-200 mb-12 max-w-lg mx-auto">Check the ones your home has during onboarding. We include maintenance SOPs only for what you actually own.</p>
          <div className="flex flex-wrap justify-center gap-3">
            {SYSTEMS.map((s) => (
              <span key={s} className="px-5 py-2.5 bg-white/10 backdrop-blur text-white text-sm font-medium rounded-full border border-white/20 hover:bg-white/20 transition cursor-default">{s}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ─── PRICING ─── */}
      <section id="pricing" className="py-20 bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-center text-sm font-semibold text-brand-600 tracking-wide mb-3">One-Time Purchase</p>
          <h2 className="font-display text-3xl text-navy-900 text-center mb-2">Choose Your Binder</h2>
          <p className="text-gray-500 text-center mb-12">Set up your profile for free. Pay only when you generate.</p>

          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* Standard */}
            <div className={`${card} rounded-lg p-8 flex flex-col`}>
              <div className="text-4xl font-extrabold text-navy-900 font-display">${standardPrice}</div>
              <p className="text-sm text-gray-400 mb-1">one-time</p>
              <h3 className="text-xl font-bold text-navy-800 mb-2">Standard Binder</h3>
              <p className="text-sm text-gray-500 mb-5 leading-relaxed">The essentials — a solid foundation for any homeowner who wants to stay organized and prepared.</p>
              <ul className="text-sm space-y-3 mb-8 flex-1">
                {[
                  'Emergency quick-start cards & playbooks',
                  '4 seasonal maintenance checklists',
                  'General maintenance & home inventory',
                  'Cleaning schedules (daily to annual)',
                  'Region-specific hazard prep',
                  'Home-type guide (condo, townhouse, etc.)',
                  'Contacts & vendors section',
                  'Print-ready PDF with 8 organized sections',
                ].map((f) => (
                  <li key={f} className="flex items-start gap-2.5">
                    <span className="text-brand-500 font-bold mt-0.5">&#10003;</span>
                    <span className="text-gray-600">{f}</span>
                  </li>
                ))}
              </ul>
              <button onClick={cta} className="w-full py-3.5 border-2 border-brand-600 text-brand-600 font-semibold rounded-full hover:bg-brand-50 transition">
                Get Started
              </button>
            </div>

            {/* Premium */}
            <div className={`${card} rounded-lg p-8 flex flex-col ring-2 ring-coral-500 relative`}>
              <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 text-xs font-bold uppercase tracking-wide text-white bg-coral-500 px-4 py-1.5 rounded-full shadow-lg shadow-coral-500/30">Most Popular</span>
              <div className="text-4xl font-extrabold text-navy-900 font-display">${premiumPrice}</div>
              <p className="text-sm text-gray-400 mb-1">one-time</p>
              <h3 className="text-xl font-bold text-navy-800 mb-2">In-Depth Binder</h3>
              <p className="text-sm text-gray-500 mb-5 leading-relaxed">The full picture — every system in your home, every member of your household, fully covered.</p>
              <ul className="text-sm space-y-3 mb-8 flex-1">
                {[
                  { text: 'Everything in Standard', bold: true },
                  { text: 'System SOPs: pool, septic, solar, HVAC, sprinklers, security, and more' },
                  { text: 'Child-proofing & child safety guide' },
                  { text: 'Pet safety & home care' },
                  { text: 'Elderly accessibility & aging-in-place' },
                  { text: 'Allergy management & indoor air quality' },
                  { text: 'Full landscaping suite (lawn, trees, drainage)' },
                  { text: 'Up to 87 modules and 640+ action items' },
                ].map((f) => (
                  <li key={f.text} className="flex items-start gap-2.5">
                    <span className="text-coral-500 font-bold mt-0.5">&#10003;</span>
                    <span className={f.bold ? 'font-semibold text-navy-800' : 'text-gray-600'}>{f.text}</span>
                  </li>
                ))}
              </ul>
              <button onClick={cta} className="w-full py-3.5 bg-brand-600 text-white font-semibold rounded-full shadow-lg shadow-brand-600/25 hover:bg-brand-700 transition">
                Get Started
              </button>
            </div>
          </div>

          <p className="text-gray-600 text-sm text-center mt-8">Both tiers include region-specific content. Update your profile and regenerate anytime.</p>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section id="faq" className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <p className="text-center text-sm font-semibold text-brand-600 tracking-wide mb-3">Questions?</p>
          <h2 className="font-display text-3xl text-navy-900 text-center mb-12">Frequently Asked Questions</h2>
          <div className="space-y-3">
            {FAQ.map((item, i) => (
              <div key={item.q} className={`${card} overflow-hidden`}>
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition"
                >
                  <span className="font-bold text-navy-900">{item.q}</span>
                  <span className={`text-brand-500 text-2xl font-light transition-transform ${openFaq === i ? 'rotate-45' : ''}`}>+</span>
                </button>
                {openFaq === i && (
                  <div className="pl-10 pr-6 pb-5">
                    <p className="text-sm text-gray-500 leading-relaxed">{item.a}</p>
                    {'bullets' in item && (item as any).bullets && (
                      <ul className="mt-2 space-y-1.5">
                        {((item as any).bullets as string[]).map((b: string) => (
                          <li key={b} className="text-sm text-gray-500 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 flex-shrink-0" />
                            {b}
                          </li>
                        ))}
                      </ul>
                    )}
                    {'after' in item && (item as any).after && (
                      <p className="text-sm text-gray-500 leading-relaxed mt-2">{(item as any).after}</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── BOTTOM CTA ─── */}
      <section className="py-20 bg-gradient-to-r from-brand-700 via-brand-600 to-brand-700 text-white text-center">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <h2 className="font-display text-3xl mb-4">Ready to build your binder?</h2>
          <p className="text-brand-100 mb-3 text-lg leading-relaxed">
            It's more than just a binder — it's the first step in organizing the services, maintenance, and daily life that all run through your home.
          </p>
          <p className="text-brand-200 mb-8">Set up your profile for free. Pay only when you generate.</p>
          <button onClick={cta} className="px-10 py-4 bg-white text-brand-700 text-lg font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all">
            Get Started Free
          </button>
        </div>
      </section>

    </div>
  );
}
