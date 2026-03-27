import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import type { Binder, Tier } from '../types';
import { useToast } from '../components/Toast';
import { useAuth } from '../AuthContext';
import { SkeletonDashboard } from '../components/Skeleton';
import {
  pageContainerWide, pageTitle, card, cardPadded, cardPrimary, cardSecondary,
  btnPrimary, btnSecondary, sectionTitle, badge, badgeColors,
  sectionLabel,
} from '../styles/shared';
import BlockRenderer from '../components/BlockRenderer';
import { titleCase } from '../styles/form';
import { Icon, IconBadge } from '../components/Icons';

/* ── Helpers for Command Center ── */
function PhoneLink({ phone, className = '' }: { phone: string; className?: string }) {
  if (!phone) return <span className="text-gray-300 text-sm">—</span>;
  const digits = phone.replace(/\D/g, '');
  return (
    <a href={`tel:${digits}`} className={`text-brand-600 hover:text-brand-800 font-medium transition ${className}`}>
      {phone}
    </a>
  );
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {}
  };
  if (!text) return null;
  return (
    <button onClick={copy} className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-brand-600 transition" title={`Copy ${label}`}>
      {copied ? (
        <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
      )}
    </button>
  );
}

function CardHeader({ title, iconName, editing, onToggleEdit, count }: { title: string; iconName: string; editing: boolean; onToggleEdit: () => void; count?: number }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2.5">
        <IconBadge name={iconName} size="sm" className="bg-brand-50 text-brand-600" />
        <div>
          <h3 className="text-sm font-bold text-navy-900">{title}</h3>
          {count !== undefined && count > 0 && (
            <p className="text-xs text-brand-600 font-medium">{count} added</p>
          )}
        </div>
      </div>
      <button onClick={onToggleEdit} className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${editing ? 'bg-brand-100 text-brand-700' : 'text-gray-400 hover:text-brand-600 hover:bg-brand-50'}`}>
        {editing ? 'Done' : 'Edit'}
      </button>
    </div>
  );
}

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 10);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

interface SectionModule {
  key: string;
  title: string;
}

interface BinderSection {
  section: string;
  title: string;
  description: string;
  icon: string;
  profile_only: boolean;
  modules: SectionModule[];
  ai_intro?: string;
}

interface Profile {
  home_identity: {
    address_line1: string;
    address_line2: string;
    city: string;
    state: string;
    zip_code: string;
    home_type: string;
    year_built: number | null;
    square_feet: number | null;
    home_nickname: string;
    owner_renter: string;
  };
  features: Record<string, boolean | string>;
  household: {
    num_adults: number;
    num_children: number;
    has_pets: boolean;
    pet_types: string;
    has_elderly: boolean;
    has_allergies: boolean;
  };
  critical_locations: Record<string, { status: string; location: string }>;
  contacts_vendors: {
    emergency_contacts: Array<{ name: string; phone: string; relationship: string }>;
    neighbors: Array<{ name: string; phone: string; relationship: string }>;
    plumber: { name: string; phone: string; skip: boolean };
    electrician: { name: string; phone: string; skip: boolean };
    hvac_tech: { name: string; phone: string; skip: boolean };
    handyman: { name: string; phone: string; skip: boolean };
    locksmith: { name: string; phone: string; skip: boolean };
    power: { company: string; account_number: string; phone: string; skip: boolean };
    gas: { company: string; account_number: string; phone: string; skip: boolean };
    water: { company: string; account_number: string; phone: string; skip: boolean };
    isp: { company: string; account_number: string; phone: string; skip: boolean };
    insurance: { provider: string; policy_number: string; claim_phone: string; skip: boolean };
  };
  guest_sitter_mode: {
    instructions: string;
    skip_instructions: boolean;
    escalation_contacts: Array<{ name: string; phone: string; relationship: string }>;
    skip_escalation: boolean;
    alarm_instructions: string;
    skip_alarm: boolean;
    pet_sitter_info: {
      pet_names: string;
      feeding_instructions: string;
      medications: string;
      vet_name: string;
      vet_phone: string;
    };
    skip_pet_sitter: boolean;
    fire_meeting_point: string;
    wifi_password: string;
    garage_code: string;
    safe_room_location: string;
  };
  system_details: {
    hvac_filter_size: string;
    hvac_filter_location: string;
    hvac_model: string;
    hvac_last_serviced: string;
    water_heater_type: string;
    water_heater_location: string;
    generator_location: string;
    generator_fuel_type: string;
    generator_wattage: string;
    pool_type: string;
    pool_equipment_location: string;
    alarm_company: string;
    alarm_company_phone: string;
    alarm_panel_location: string;
  };
  completed: boolean;
  purchased_tier?: Tier | '';
  stripe_session_id?: string;
}

const HOME_TYPES: Record<string, string> = {
  single_family: 'Single Family', condo: 'Condo', townhouse: 'Townhouse', apartment: 'Apartment', mobile: 'Mobile Home',
};

const FEATURE_LABELS: Record<string, string> = {
  has_pool: 'Pool', has_hot_tub: 'Hot Tub', has_garage: 'Garage', has_basement: 'Basement',
  has_attic: 'Attic', has_crawl_space: 'Crawl Space', has_fireplace: 'Fireplace', has_gutters: 'Gutters',
  has_sprinklers: 'Sprinklers', has_fence: 'Fence', has_deck_patio: 'Deck/Patio', has_lanai: 'Lanai',
  has_driveway: 'Driveway', has_shed: 'Shed', has_septic: 'Septic', has_well_water: 'Well Water',
  has_water_softener: 'Water Softener', has_sump_pump: 'Sump Pump', has_solar: 'Solar',
  has_generator: 'Generator', has_ev_charger: 'EV Charger', has_security_system: 'Security System',
  has_smart_home: 'Smart Home', has_cameras: 'Cameras', has_washer_dryer: 'Washer/Dryer',
  has_dishwasher: 'Dishwasher', has_garbage_disposal: 'Disposal',
};

const LOCATION_LABELS: Record<string, string> = {
  water_shutoff: 'Water Shutoff', gas_shutoff: 'Gas Shutoff', electrical_panel: 'Electrical Panel',
  hvac_unit: 'HVAC Unit', sump_pump: 'Sump Pump', attic_access: 'Attic Access', crawlspace_access: 'Crawlspace',
};

export default function Dashboard() {
  const [binders, setBinders] = useState<Binder[]>([]);
  const [sections, setSections] = useState<BinderSection[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState('');
  const [firstGenLoading, setFirstGenLoading] = useState(false);
  const [firstGenError, setFirstGenError] = useState('');
  const [profileComplete, setProfileComplete] = useState<{
  overall_score: number;
  can_generate: boolean;
  blocking_issues: string[];
  sections: Record<string, {
    name: string;
    score: number;
    status: string;
    critical_missing: string[];
    warnings: string[];
    tips: string[];
  }>;
  feature_warnings: Array<{
    feature: string;
    missing: string[];
    step_to_fix: string;
  }>;
} | null>(null);
  const [savedProfile, setSavedProfile] = useState<typeof profile>(null);
  const hasChanges = useMemo(() => JSON.stringify(profile) !== JSON.stringify(savedProfile), [profile, savedProfile]);
  const [activeSection, setActiveSection] = useState<string>('home_info');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [expandedInfoSection, setExpandedInfoSection] = useState<string>('address'); // kept for suggestion navigation
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [userMessages, setUserMessages] = useState<Array<{
    id: string; order_id: string; sender: string; message: string; read: boolean; created_at: string | null;
  }>>([]);
  const [expandedMessage, setExpandedMessage] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');
  const [replySending, setReplySending] = useState(false);
  const [replySent, setReplySent] = useState<string | null>(null);
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { isAdmin } = useAuth();

  // Map suggestion text to Home Info section keys
  const getSectionForSuggestion = (suggestion: string): string => {
    const s = suggestion.toLowerCase();
    if (s.includes('year built') || s.includes('square')) return 'address';
    if (s.includes('critical location')) return 'locations';
    if (s.includes('provider') || s.includes('plumber') || s.includes('electrician') || s.includes('hvac')) return 'providers';
    if (s.includes('emergency contact')) return 'providers'; // or could add emergency_contacts section
    return 'address';
  };

  const handleSuggestionClick = (suggestion: string) => {
    const section = getSectionForSuggestion(suggestion);
    setActiveSection('home_info');
    setExpandedInfoSection(section);
    setShowSuggestions(false);
  };

  const generateFirstBinder = async (tier: Tier) => {
    setFirstGenLoading(true);
    setFirstGenError('');
    setGenerationStatus('Generating your binder...');
    try {
      await api.post('/binders/generate', { tier }, { timeout: 200000 });
      const res = await api.get('/binders/');
      setBinders(res.data);
      window.dispatchEvent(new Event('binder:updated'));
      if (res.data.length > 0 && res.data[0].status === 'ready') {
        const sr = await api.get(`/binders/${res.data[0].id}/sections`);
        setSections(sr.data);
      }
      showToast('Binder generated successfully', 'success');
    } catch (e: any) {
      const errorMsg = e.response?.data?.detail || e.message || 'Unknown error';
      setFirstGenError(errorMsg);
      showToast(`Failed to generate binder: ${errorMsg}`, 'error');
    } finally {
      setGenerationStatus('');
      setFirstGenLoading(false);
    }
  };

  useEffect(() => {
    // Check profile completeness
    api.get('/profile/completeness')
      .then(res => setProfileComplete(res.data))
      .catch(() => {});
    // Load user messages
    api.get('/profile/messages')
      .then(res => setUserMessages(res.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (isAdmin) {
      navigate('/admin', { replace: true });
      return;
    }
    const load = async () => {
      try {
        const [bindersRes, profileRes] = await Promise.all([api.get('/binders/'), api.get('/profile/')]);
        setBinders(bindersRes.data);
        setProfile(profileRes.data);
        setSavedProfile(profileRes.data);

        if (bindersRes.data.length === 0) {
          const purchasedTier = (profileRes.data.purchased_tier || '') as Tier | '';
          if (purchasedTier) {
            await generateFirstBinder(purchasedTier || 'premium');
            setLoading(false);
            return;
          }
          setLoading(false);
          if (profileRes.data.completed) navigate('/select-plan', { replace: true });
          else navigate('/onboarding', { replace: true });
          return;
        }

        if (bindersRes.data[0].status === 'ready') {
          try {
            const sr = await api.get(`/binders/${bindersRes.data[0].id}/sections`);
            setSections(sr.data);
          } catch {
            // Section load failed — user can still see sidebar
          }
        }
        setLoading(false);
      } catch {
        setLoading(false);
        navigate('/onboarding', { replace: true });
      }
    };

    load();
  }, [isAdmin, navigate]);

  const updateProfile = (section: string, field: string, value: any) => {
    if (!profile) return;
    setProfile({ ...profile, [section]: { ...(profile as any)[section], [field]: value } });
  };

  const updateNestedProfile = (section: string, subsection: string, field: string, value: any) => {
    if (!profile) return;
    setProfile({
      ...profile,
      [section]: { ...(profile as any)[section], [subsection]: { ...(profile as any)[section][subsection], [field]: value } },
    });
  };

  const saveChanges = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      await api.put('/profile/', profile);
      setSavedProfile(profile);
      // Refresh completeness check
      const res = await api.get('/profile/completeness');
      setProfileComplete(res.data);
      showToast('Changes saved successfully', 'success');
    } catch {
      showToast('Failed to save changes', 'error');
    }
    setSaving(false);
  };

  const replyToMessage = async (messageId: string) => {
    if (!replyText.trim()) return;
    setReplySending(true);
    try {
      await api.post(`/profile/messages/${messageId}/reply`, { message: replyText.trim() });
      setReplyText('');
      setReplySent(messageId);
      // Mark as read
      await api.post(`/profile/messages/${messageId}/read`);
      // Refresh messages
      const res = await api.get('/profile/messages');
      setUserMessages(res.data);
      showToast('Reply sent', 'success');
      setTimeout(() => setReplySent(null), 3000);
    } catch {
      showToast('Failed to send reply', 'error');
    } finally {
      setReplySending(false);
    }
  };

  const regenerateBinder = async () => {
    if (!profile) return;
    setRegenerating(true);
    setGenerationStatus('Saving profile...');
    try {
      if (hasChanges) {
        await api.put('/profile/', profile);
        setSavedProfile(profile);
      }
      const tier = binders[0]?.tier || 'premium';
      setGenerationStatus('Generating AI content (30-90 sec)...');
      // Generation can take up to 3 minutes with AI content
      const response = await api.post('/binders/generate', { tier }, { timeout: 200000 });
      setGenerationStatus('Loading binder...');
      const res = await api.get('/binders/');
      setBinders(res.data);
      window.dispatchEvent(new Event('binder:updated'));
      if (res.data.length > 0 && res.data[0].status === 'ready') {
        const sr = await api.get(`/binders/${res.data[0].id}/sections`);
        setSections(sr.data);
      }
      setGenerationStatus('');
      showToast('Binder regenerated successfully', 'success');
    } catch (e: any) {
      setGenerationStatus('');
      const errorMsg = e.response?.data?.detail || e.message || 'Unknown error';
      showToast(`Failed to generate binder: ${errorMsg}`, 'error');
    }
    setRegenerating(false);
  };

  const secureDownload = async (url: string, filename: string) => {
    try {
      const response = await api.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch {
      showToast('Download failed', 'error');
    }
  };

  const binderFilename = (b: Binder, type: 'full' | 'sitter' | 'checklist'): string => {
    const date = b.created_at ? new Date(b.created_at).toISOString().slice(0, 10) : 'unknown';
    const tier = b.tier || 'standard';
    if (type === 'sitter') return `sitter-packet-${tier}-${date}.pdf`;
    if (type === 'checklist') return `fill-in-checklist-${tier}-${date}.pdf`;
    return `binderpro-${tier}-${date}.pdf`;
  };

  const download = (b: Binder) => {
    secureDownload(`/binders/${b.id}/download`, binderFilename(b, 'full'));
  };

  const downloadSitterPacket = (b: Binder) => {
    secureDownload(`/binders/${b.id}/download/sitter-packet`, binderFilename(b, 'sitter'));
  };

  const downloadChecklist = (b: Binder) => {
    secureDownload(`/binders/${b.id}/download/checklist`, binderFilename(b, 'checklist'));
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-50/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <SkeletonDashboard />
      </div>
    </div>
  );

  if (!profile) return null;

  if (binders.length === 0 && profile.purchased_tier) {
    const tier = (profile.purchased_tier || 'premium') as Tier;
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className={`${cardPadded} max-w-lg w-full p-8 text-center`}>
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-brand-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <h1 className={`${pageTitle} mb-2`}>Let's generate your binder</h1>
          <p className="text-gray-500 mb-6">
            We found your payment, but your binder hasn’t been generated yet. Click below to create it now.
          </p>
          {generationStatus && (
            <p className="text-sm text-brand-600 mb-4">{generationStatus}</p>
          )}
          {firstGenError && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg mb-4">{firstGenError}</p>
          )}
          <button
            onClick={() => generateFirstBinder(tier)}
            disabled={firstGenLoading}
            className={`w-full py-3 rounded-full ${btnPrimary}`}
          >
            {firstGenLoading ? 'Generating...' : 'Generate My Binder'}
          </button>
        </div>
      </div>
    );
  }

  const latestBinder = binders[0];
  const addr = profile.home_identity;
  const filteredSections = sections.filter(s => s.section !== 'section_0');

  const printSection = (_sectionKey: string) => {
    window.print();
  };

  const renderMainContent = () => {
    // Home Information
    if (activeSection === 'home_info') {
      return <CommandCenter profile={profile} updateProfile={updateProfile} updateNestedProfile={updateNestedProfile} onSave={saveChanges} hasChanges={hasChanges} saving={saving} />;
    }

    // Chapter content
    const sec = sections.find(s => s.section === activeSection);
    if (!sec) return <p className="text-gray-400 text-center py-10">Select a section from the sidebar.</p>;

    const chapterNum = filteredSections.findIndex(s => s.section === activeSection) + 1;

    return (
      <div>
        {/* Chapter Header with Print/Download */}
        <div className="mb-6 flex items-start justify-between" data-print-hide>
          <div className="flex items-center gap-3">
            <span className="w-10 h-10 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center font-bold">{chapterNum}</span>
            <div>
              <h2 className={sectionTitle}>{sec.title}</h2>
              <p className="text-sm text-gray-500">{sec.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
              title="Print this section"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
            </button>
            <button
              onClick={() => latestBinder && download(latestBinder)}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
              title="Download full binder"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>
          </div>
        </div>

        {/* Print-friendly chapter header */}
        <div className="hidden print:block mb-6">
          <h2 className="text-2xl font-bold text-navy-900 mb-2">{chapterNum}. {sec.title}</h2>
          <p className="text-gray-700 text-sm">{sec.description}</p>
        </div>

        {sec.ai_intro && (
          <div className="mb-6 bg-blue-50 border border-blue-100 rounded-xl p-4" data-print-hide>
            <p className="text-xs text-blue-600 font-semibold uppercase tracking-wider mb-1">Personalized for Your Home</p>
            <p className="text-sm text-gray-700">{sec.ai_intro}</p>
          </div>
        )}

        {/* Sub-chapters Overview */}
        {sec.modules.length > 0 ? (
          <div className="space-y-3">
            {sec.modules.map((mod, idx) => (
              <SubChapterOverview
                key={mod.key}
                chapterNum={chapterNum}
                subNum={idx + 1}
                title={mod.title}
                moduleKey={mod.key}
                profile={profile}
                binderId={latestBinder?.id}
                sectionKey={sec.section}
              />
            ))}
          </div>
        ) : sec.profile_only ? (
          <ProfileSectionContent section={sec.section} profile={profile} />
        ) : (
          <p className="text-sm text-gray-400 text-center py-8" data-print-hide>No content in this section.</p>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50/80">
      {/* Mobile Header */}
      <div className="lg:hidden sticky top-0 z-40 bg-white border-b border-gray-200 px-4 py-3" data-print-hide>
        <div className="flex items-center justify-between">
          <button
            onClick={() => setMobileNavOpen(true)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <span>Menu</span>
          </button>
          <div className="flex items-center gap-2">
            {hasChanges && (
              <button onClick={saveChanges} disabled={saving} className={`${btnSecondary} px-3 py-1.5`}>
                {saving ? '...' : 'Save'}
              </button>
            )}
            <button
              onClick={regenerateBinder}
              disabled={regenerating || (profileComplete !== null && !profileComplete.can_generate)}
              className={`${btnPrimary} px-3 py-1.5`}
            >
              {regenerating ? 'Generating...' : 'Regenerate'}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Nav Drawer */}
      {mobileNavOpen && (
        <div className="lg:hidden fixed inset-0 z-50" data-print-hide>
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileNavOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-80 max-w-[85vw] bg-white shadow-xl overflow-y-auto">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-semibold text-navy-900">Navigation</h2>
              <button onClick={() => setMobileNavOpen(false)} className="p-1 text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {/* Home Info */}
            <div className="p-2 border-b border-gray-100">
              <button
                onClick={() => { setActiveSection('home_info'); setMobileNavOpen(false); }}
                className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-3 transition ${activeSection === 'home_info' ? 'bg-brand-50 text-brand-700' : 'text-gray-600'}`}
              >
                <Icon name="home" className="w-5 h-5" />
                <span className={`text-sm font-medium ${activeSection === 'home_info' ? 'text-brand-700' : 'text-navy-900'}`}>My Home</span>
              </button>
            </div>
            {/* Chapters */}
            <div className="p-2">
              <p className={`px-3 py-2 ${sectionLabel}`}>Chapters</p>
              {filteredSections.map((sec, idx) => (
                <button
                  key={sec.section}
                  onClick={() => { setActiveSection(sec.section); setMobileNavOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-3 transition mb-0.5 ${sec.section === activeSection ? 'bg-brand-50 text-brand-700' : 'text-gray-600'}`}
                >
                  <span className="w-6 h-6 rounded bg-gray-100 text-gray-500 flex items-center justify-center text-xs font-semibold">{idx + 1}</span>
                  <span className={`text-sm font-medium ${sec.section === activeSection ? 'text-brand-700' : 'text-navy-900'}`}>{sec.title}</span>
                </button>
              ))}
            </div>
            {/* Downloads */}
            {latestBinder && (
              <div className="p-3 border-t border-gray-100">
                <p className={`${sectionLabel} mb-2`}>Downloads</p>
                <div className="space-y-2">
                  <button onClick={() => download(latestBinder)} className="w-full text-left px-3 py-2 rounded-lg bg-brand-50 text-brand-700 text-sm font-medium">
                    Full Binder PDF
                  </button>
                  <button onClick={() => downloadSitterPacket(latestBinder)} className="w-full text-left px-3 py-2 rounded-lg bg-purple-50 text-purple-700 text-sm font-medium">
                    Sitter Packet
                  </button>
                </div>
              </div>
            )}
            {/* Ecosystem Links */}
            <div className="p-3 border-t border-gray-100">
              <p className={`${sectionLabel} mb-2 text-brand-700`}>Put Your Binder to Use</p>
              <div className="space-y-1.5">
                {[
                  { href: 'https://homesureapp.com', iconName: 'tools', label: 'Find Service Providers' },
                  { href: 'https://homeeaseusa.com', iconName: 'home', label: 'Manage Your Home' },
                  { href: 'https://domuslogic.com', iconName: 'automate', label: 'Automate Your Home' },
                  { href: 'https://nodeharborpro.com', iconName: 'computer', label: 'Build a Home Lab' },
                  { href: 'https://mysphere.me', iconName: 'calendar', label: 'Schedule & Wellness' },
                  { href: 'https://innerquestcoaching.com', iconName: 'sparkles', label: 'Life Coaching' },
                ].map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-brand-50 hover:text-brand-700 transition"
                  >
                    <Icon name={link.iconName} className="w-4 h-4" />
                    <span className="flex-1 font-medium">{link.label}</span>
                    <svg className="w-3.5 h-3.5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                ))}
              </div>
              <div className="mt-2 pt-2 border-t border-gray-100">
                <a href="https://getliberated.me" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-brand-600 transition">
                  <span>Part of</span>
                  <span className="font-semibold">GetLiberated.me</span>
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex">
        {/* Sidebar - Hidden on mobile */}
        <div className="hidden lg:block w-64 xl:w-72 flex-shrink-0 border-r border-gray-200 bg-white min-h-[calc(100vh-3.5rem)]" data-print-hide>
          <div className="sticky top-14 overflow-y-auto max-h-[calc(100vh-3.5rem)]">
              {/* Actions */}
              <div className="p-3 pb-3 border-b border-gray-100/60">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Actions</p>
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={regenerateBinder}
                    disabled={regenerating || (profileComplete !== null && !profileComplete.can_generate)}
                    className={`flex-1 ${btnPrimary} px-3 py-2 flex items-center justify-center gap-2`}
                  >
                    {regenerating ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span className="truncate text-xs">{generationStatus || 'Generating...'}</span>
                      </>
                    ) : 'Regenerate'}
                  </button>
                  {hasChanges && (
                    <button onClick={saveChanges} disabled={saving} className={`${btnSecondary} px-3 py-2`}>
                      {saving ? '...' : 'Save'}
                    </button>
                  )}
                </div>

                {/* Status indicators */}
                {hasChanges && (
                  <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 px-2 py-1.5 rounded-lg mb-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                    Unsaved changes
                  </div>
                )}

                {/* Blocking issues */}
                {profileComplete && !profileComplete.can_generate && (profileComplete.blocking_issues?.length ?? 0) > 0 && (
                  <div className="text-xs text-red-600 bg-red-50 px-2 py-1.5 rounded-lg mb-2">
                    <div className="flex items-center gap-1.5 font-medium">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      Required to generate:
                    </div>
                    <ul className="mt-1 ml-5 list-disc">
                      {(profileComplete.blocking_issues ?? []).map((m, i) => <li key={i}>{m}</li>)}
                    </ul>
                  </div>
                )}

                {/* Section completeness with expandable details */}
                {profileComplete && profileComplete.sections && (
                  <div className="relative">
                    <button
                      onClick={() => setShowSuggestions(!showSuggestions)}
                      className={`w-full text-left text-xs px-2 py-1.5 rounded-lg transition ${
                        profileComplete.overall_score >= 80
                          ? 'text-green-700 bg-green-50 hover:bg-green-100'
                          : profileComplete.overall_score >= 50
                          ? 'text-amber-700 bg-amber-50 hover:bg-amber-100'
                          : 'text-orange-700 bg-orange-50 hover:bg-orange-100'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <div className="w-7 h-7 rounded-full border-2 flex items-center justify-center text-[10px] font-bold"
                               style={{ borderColor: profileComplete.overall_score >= 80 ? '#22c55e' : profileComplete.overall_score >= 50 ? '#f59e0b' : '#f97316' }}>
                            {profileComplete.overall_score}
                          </div>
                          <span className="font-medium">Binder Completeness</span>
                        </div>
                        <svg className={`w-3.5 h-3.5 transition-transform ${showSuggestions ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </button>
                    {showSuggestions && (
                      <div className="mt-1 text-xs bg-gray-50 px-2 py-2 rounded-lg max-h-80 overflow-y-auto">
                        {Object.entries(profileComplete.sections).map(([key, section]) => {
                          const hasIssues = section.critical_missing.length > 0 || section.warnings.length > 0;
                          if (!hasIssues) return null;
                          return (
                            <div key={key} className="mb-2 pb-2 border-b border-gray-200 last:border-0">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-gray-700">{section.name}</span>
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                  section.status === 'incomplete' ? 'bg-red-100 text-red-700' :
                                  section.status === 'needs_attention' ? 'bg-amber-100 text-amber-700' :
                                  'bg-green-100 text-green-700'
                                }`}>
                                  {section.score}%
                                </span>
                              </div>
                              {section.critical_missing.length > 0 && (
                                <ul className="ml-2 space-y-0.5">
                                  {section.critical_missing.map((item, i) => (
                                    <li key={i} className="flex items-start gap-1.5 text-red-600">
                                      <span className="mt-0.5">✗</span>
                                      <span>{item}</span>
                                    </li>
                                  ))}
                                </ul>
                              )}
                              {section.warnings.length > 0 && (
                                <ul className="ml-2 space-y-0.5 mt-1">
                                  {section.warnings.map((item, i) => (
                                    <li key={i} className="flex items-start gap-1.5 text-amber-600">
                                      <span className="mt-0.5">!</span>
                                      <span>{item}</span>
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          );
                        })}

                        <button
                          onClick={() => { setActiveSection('home_info'); setShowSuggestions(false); }}
                          className="mt-2 text-brand-600 hover:text-brand-700 font-medium"
                        >
                          Go to Home Information →
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Home Info */}
              <div className="p-2 border-b border-gray-100/60">
                <button
                  onClick={() => setActiveSection('home_info')}
                  className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-3 transition ${activeSection === 'home_info' ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-50'}`}
                >
                  <Icon name="home" className="w-5 h-5" />
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm font-medium ${activeSection === 'home_info' ? 'text-brand-700' : 'text-navy-900'}`}>My Home</p>
                    <p className="text-xs text-gray-400">Contacts, providers & info</p>
                  </div>
                </button>
              </div>

              {/* Chapters */}
              <div className="p-2">
                <p className={`px-3 py-2 ${sectionLabel}`}>Chapters</p>
                {filteredSections.length === 0 && latestBinder ? (
                  <div className="px-3 py-4 text-center">
                    {latestBinder.status === 'generating' && (
                      <p className="text-xs text-amber-600">Binder is generating...</p>
                    )}
                    {latestBinder.status === 'failed' && (
                      <p className="text-xs text-red-600">Binder generation failed. Try regenerating.</p>
                    )}
                    {latestBinder.status === 'ready' && (
                      <p className="text-xs text-gray-500">Loading chapters...</p>
                    )}
                  </div>
                ) : (
                  filteredSections.map((sec, idx) => {
                    const isActive = sec.section === activeSection;
                    return (
                      <button
                        key={sec.section}
                        onClick={() => setActiveSection(sec.section)}
                        className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-3 transition mb-0.5 ${isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-50'}`}
                      >
                        <span className="w-6 h-6 rounded bg-gray-100 text-gray-500 flex items-center justify-center text-xs font-semibold">{idx + 1}</span>
                        <div className="min-w-0 flex-1">
                          <p className={`text-sm font-medium truncate ${isActive ? 'text-brand-700' : 'text-navy-900'}`}>{sec.title}</p>
                          <p className="text-xs text-gray-400">{sec.modules.length > 0 ? `${sec.modules.length} sub-chapters` : 'Profile data'}</p>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>

              {/* Binder History */}
              {binders.length > 1 && (
                <div className="p-3 border-t border-gray-100">
                  <p className={`${sectionLabel} mb-2`}>Previous</p>
                  {binders.slice(1, 3).map((b) => (
                    <div key={b.id} className="flex items-center justify-between py-1">
                      <span className="text-xs text-gray-400">{b.created_at && new Date(b.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>
                      <button onClick={() => download(b)} className="text-xs text-brand-600 hover:text-brand-700">Download</button>
                    </div>
                  ))}
                </div>
              )}

              {/* Downloads */}
              {latestBinder && (
                <div className="p-3 border-t border-gray-100">
                  <p className={`${sectionLabel} mb-2`}>Downloads</p>
                  <div className="space-y-2">
                    <button
                      onClick={() => download(latestBinder)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-50 hover:bg-brand-100 transition group"
                    >
                      <span className="w-6 h-6 rounded bg-brand-100 text-brand-600 flex items-center justify-center text-xs group-hover:bg-brand-200">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                      </span>
                      <div className="flex-1 text-left">
                        <p className="text-xs font-medium text-brand-700">Full Binder</p>
                        <p className="text-xs text-brand-500">Complete home guide</p>
                      </div>
                      <svg className="w-4 h-4 text-brand-400 group-hover:text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </button>
                    <button
                      onClick={() => downloadSitterPacket(latestBinder)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-purple-50 hover:bg-purple-100 transition group"
                    >
                      <span className="w-6 h-6 rounded bg-purple-100 text-purple-600 flex items-center justify-center text-xs group-hover:bg-purple-200">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                      </span>
                      <div className="flex-1 text-left">
                        <p className="text-xs font-medium text-purple-700">Sitter Packet</p>
                        <p className="text-xs text-purple-500">Guest & sitter essentials</p>
                      </div>
                      <svg className="w-4 h-4 text-purple-400 group-hover:text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </button>
                    <button
                      onClick={() => downloadChecklist(latestBinder)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 hover:bg-amber-100 transition group"
                    >
                      <span className="w-6 h-6 rounded bg-amber-100 text-amber-600 flex items-center justify-center text-xs group-hover:bg-amber-200">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                        </svg>
                      </span>
                      <div className="flex-1 text-left">
                        <p className="text-xs font-medium text-amber-700">Fill-In Checklist</p>
                        <p className="text-xs text-amber-500">Missing info to complete</p>
                      </div>
                      <svg className="w-4 h-4 text-amber-400 group-hover:text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Put Your Binder to Use */}
              <div className="p-3 border-t border-gray-100">
                <p className={`${sectionLabel} mb-2 text-brand-700`}>Put Your Binder to Use</p>
                <div className="space-y-2">
                  {[
                    { href: 'https://homesureapp.com', iconName: 'tools', label: 'Find Service Providers', subtitle: 'HomeSureApp.com' },
                    { href: 'https://homeeaseusa.com', iconName: 'home', label: 'Manage Your Home', subtitle: 'HomeEaseUSA.com' },
                    { href: 'https://domuslogic.com', iconName: 'automate', label: 'Automate Your Home', subtitle: 'DomusLogic.com' },
                    { href: 'https://nodeharborpro.com', iconName: 'computer', label: 'Build a Home Lab', subtitle: 'NodeHarborPro.com' },
                    { href: 'https://mysphere.me', iconName: 'calendar', label: 'Schedule & Wellness', subtitle: 'MySphere.me' },
                    { href: 'https://innerquestcoaching.com', iconName: 'sparkles', label: 'Life Coaching', subtitle: 'InnerQuestCoaching.com' },
                  ].map((link) => (
                    <a
                      key={link.href}
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block px-3 py-2 rounded-lg bg-white border border-gray-100 hover:border-brand-200 transition group"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-gray-100 text-gray-500 flex items-center justify-center">
                          <Icon name={link.iconName} className="w-3.5 h-3.5" />
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-navy-900 group-hover:text-brand-700">{link.label}</p>
                          <p className="text-xs text-gray-400">{link.subtitle}</p>
                        </div>
                        <svg className="w-3.5 h-3.5 text-gray-300 group-hover:text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </div>
                    </a>
                  ))}
                </div>
                <div className="mt-3 pt-2 border-t border-gray-100">
                  <a
                    href="https://getliberated.me"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-brand-600 transition"
                  >
                    <span>Part of</span>
                    <span className="font-semibold">GetLiberated.me</span>
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                </div>
              </div>
            </div>
          </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0 px-6 sm:px-8 lg:px-10 py-6">
            {/* Message Notification Banner */}
            {userMessages.filter(m => m.sender === 'admin' && !m.read).length > 0 && (
              <div className="mb-4 space-y-2" data-print-hide>
                {userMessages.filter(m => m.sender === 'admin' && !m.read).map(msg => (
                  <div key={msg.id} className={`${card} bg-yellow-50 border-yellow-200 p-4`}>
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-full bg-yellow-100 flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-yellow-800">Message from BinderPro team</p>
                        {expandedMessage === msg.id ? (
                          <>
                            <p className="text-sm text-yellow-700 mt-1 whitespace-pre-wrap">{msg.message}</p>
                            {msg.created_at && (
                              <p className="text-xs text-yellow-500 mt-1">{new Date(msg.created_at).toLocaleString()}</p>
                            )}
                            {replySent === msg.id ? (
                              <p className="text-sm text-green-600 font-medium mt-2">Reply sent</p>
                            ) : (
                              <div className="flex gap-2 mt-2">
                                <input
                                  type="text"
                                  value={replyText}
                                  onChange={(e) => setReplyText(e.target.value)}
                                  placeholder="Type your reply..."
                                  className="flex-1 border border-yellow-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 bg-white"
                                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); replyToMessage(msg.id); } }}
                                />
                                <button
                                  onClick={() => replyToMessage(msg.id)}
                                  disabled={!replyText.trim() || replySending}
                                  className="px-3 py-1.5 bg-yellow-600 text-white rounded-lg text-sm font-medium hover:bg-yellow-700 disabled:opacity-50 transition"
                                >
                                  {replySending ? '...' : 'Reply'}
                                </button>
                              </div>
                            )}
                          </>
                        ) : (
                          <>
                            <p className="text-sm text-yellow-700 mt-0.5 truncate">{msg.message}</p>
                            <button
                              onClick={() => { setExpandedMessage(msg.id); setReplyText(''); }}
                              className="text-xs text-yellow-600 hover:text-yellow-800 font-medium mt-1"
                            >
                              View full message & reply
                            </button>
                          </>
                        )}
                      </div>
                      {expandedMessage === msg.id && (
                        <button
                          onClick={() => setExpandedMessage(null)}
                          className="text-yellow-400 hover:text-yellow-600 p-1"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {renderMainContent()}
          </div>
        </div>
      </div>
  );
}

// Module descriptions for overview display
const MODULE_DESCRIPTIONS: Record<string, string> = {
  // Quick Start Cards
  quick_start_gas: 'Step-by-step guide for gas leak detection and emergency shutoff procedures.',
  quick_start_water: 'How to quickly shut off water supply and handle burst pipes or flooding.',
  quick_start_fire: 'Fire safety protocols, evacuation routes, and extinguisher locations.',
  quick_start_power: 'Power outage response, generator operation, and electrical safety.',
  qs_gas_leak: 'Emergency reference card for gas leak detection and immediate response steps.',
  qs_water_shutoff: 'Quick reference for locating and operating your main water shutoff valve.',
  qs_fire_safety: 'At-a-glance fire safety card with evacuation routes and extinguisher use.',
  qs_power_outage: 'Quick steps for power outage response and protecting your appliances.',
  // Playbooks
  playbook_fire: 'Complete fire emergency playbook with prevention, response, and recovery phases.',
  playbook_water: 'Water damage response from leak detection to insurance claims and restoration.',
  playbook_power: 'Power outage management including backup power and appliance protection.',
  playbook_hvac: 'HVAC failure response for both heating and cooling system emergencies.',
  playbook_storm: 'Storm preparation and response customized for your region.',
  playbook_security: 'Home security protocols for break-ins, suspicious activity, and lockouts.',
  // Seasonal Maintenance
  seasonal_spring: 'Spring maintenance checklist for exterior, HVAC, and landscaping.',
  seasonal_summer: 'Summer upkeep including AC maintenance, pest control, and outdoor care.',
  seasonal_fall: 'Fall preparation for heating season, gutter cleaning, and winterization.',
  seasonal_winter: 'Winter maintenance for pipes, heating, snow removal, and ice prevention.',
  // Cleaning
  cleaning_schedule: 'Room-by-room cleaning schedules from daily tasks to annual deep cleans.',
  cleaning_kitchen: 'Kitchen cleaning guide including appliances, surfaces, and deep clean tasks.',
  cleaning_bathroom: 'Bathroom cleaning checklist for fixtures, tiles, and ventilation.',
  // Systems
  hvac_maintenance: 'HVAC system care including filter changes, seasonal tune-ups, and efficiency tips.',
  plumbing_basics: 'Plumbing maintenance, common repairs, and when to call a professional.',
  electrical_safety: 'Electrical system overview, safety checks, and circuit breaker guide.',
  appliance_care: 'Maintenance schedules and tips for major household appliances.',
  water_heater: 'Water heater maintenance, temperature settings, and troubleshooting guide.',
  // Feature-specific
  pool_maintenance: 'Pool and spa care including chemical balance, cleaning, and winterization.',
  fireplace_care: 'Fireplace and chimney maintenance, safety checks, and seasonal operation.',
  garage_maintenance: 'Garage door maintenance, opener care, and organization tips.',
  basement_care: 'Basement moisture control, waterproofing, and maintenance checklist.',
  septic_system: 'Septic system care, pumping schedule, and dos and don\'ts.',
  well_water: 'Well water system maintenance, testing schedule, and treatment options.',
  solar_panels: 'Solar panel cleaning, monitoring, and maintenance best practices.',
  generator_maintenance: 'Generator testing, fuel management, and maintenance schedule.',
  security_system: 'Security system testing, sensor checks, and monitoring best practices.',
  smart_home: 'Smart home device maintenance, updates, and troubleshooting.',
  // Inventory
  emergency_kit: 'Essential emergency supplies checklist customized for your household.',
  home_inventory: 'Equipment and systems inventory template for insurance and maintenance.',
  emergency_supplies: 'Complete emergency kit checklist for your household size and needs.',
  tool_inventory: 'Essential home maintenance tools and their locations.',
  // Household
  child_safety: 'Child safety checklist including proofing tips and hazard prevention.',
  pet_safety: 'Pet safety guide including toxic plants, secure areas, and emergency info.',
  elderly_accessibility: 'Accessibility modifications and safety features for elderly household members.',
  allergy_management: 'Air quality management and allergy reduction strategies for your home.',
  // Region-specific
  hurricane_prep: 'Hurricane preparation checklist including supplies, shutters, and evacuation.',
  tornado_safety: 'Tornado safety procedures, shelter locations, and emergency kit.',
  earthquake_prep: 'Earthquake preparedness including securing items and emergency supplies.',
  wildfire_defense: 'Wildfire defensible space, evacuation planning, and air quality.',
  winter_storm: 'Winter storm preparation for heating, pipes, and emergency supplies.',
  flood_prep: 'Flood preparation and response including insurance and documentation.',
};

// Sub-chapter overview component
function SubChapterOverview({ chapterNum, subNum, title, moduleKey, profile, binderId, sectionKey }: {
  chapterNum: number;
  subNum: number;
  title: string;
  moduleKey: string;
  profile: Profile;
  binderId?: string;
  sectionKey?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [contentBlocks, setContentBlocks] = useState<any[] | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  const description = MODULE_DESCRIPTIONS[moduleKey] || 'Personalized content based on your home profile and preferences.';

  const getQuickRef = () => {
    const refs: { label: string; value: string }[] = [];
    const cl = profile.critical_locations;

    if (moduleKey.includes('water') || moduleKey.includes('plumbing')) {
      if (cl.water_shutoff?.status === 'known') refs.push({ label: 'Shutoff', value: cl.water_shutoff.location });
      if (profile.contacts_vendors.plumber?.name) refs.push({ label: 'Plumber', value: `${profile.contacts_vendors.plumber.name} - ${profile.contacts_vendors.plumber.phone}` });
    }
    if (moduleKey.includes('gas')) {
      if (cl.gas_shutoff?.status === 'known') refs.push({ label: 'Shutoff', value: cl.gas_shutoff.location });
    }
    if (moduleKey.includes('electric') || moduleKey.includes('power')) {
      if (cl.electrical_panel?.status === 'known') refs.push({ label: 'Panel', value: cl.electrical_panel.location });
      if (profile.contacts_vendors.electrician?.name) refs.push({ label: 'Electrician', value: `${profile.contacts_vendors.electrician.name}` });
    }
    if (moduleKey.includes('hvac') || moduleKey.includes('heat') || moduleKey.includes('cool')) {
      if (cl.hvac_unit?.status === 'known') refs.push({ label: 'Unit', value: cl.hvac_unit.location });
      if (profile.contacts_vendors.hvac_tech?.name) refs.push({ label: 'HVAC Tech', value: profile.contacts_vendors.hvac_tech.name });
    }
    if (moduleKey.includes('fire') || moduleKey.includes('emergency')) {
      refs.push({ label: 'Emergency', value: '911' });
    }
    return refs;
  };

  const quickRefs = getQuickRef();

  const handleExpand = async () => {
    const willExpand = !expanded;
    setExpanded(willExpand);

    // Lazy-load content on first expand
    if (willExpand && !contentBlocks && binderId && sectionKey) {
      setContentLoading(true);
      try {
        const res = await api.get(`/binders/${binderId}/sections/${sectionKey}/content`);
        setContentBlocks(res.data.blocks || []);
      } catch {
        setContentBlocks([]);
      } finally {
        setContentLoading(false);
      }
    }
  };

  return (
    <div className={`${card} overflow-hidden hover:border-gray-300 transition`}>
      <button
        onClick={handleExpand}
        className="w-full px-4 py-4 flex items-start justify-between hover:bg-gray-50 transition text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-sm text-brand-600 font-semibold">{chapterNum}.{subNum}</span>
            <span className="text-sm font-semibold text-navy-900">{title}</span>
          </div>
          <p className="text-sm text-gray-500 line-clamp-2">{description}</p>
          {quickRefs.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {quickRefs.slice(0, 3).map((ref, i) => (
                <span key={i} className="inline-flex items-center gap-1 text-xs bg-brand-50 text-brand-700 px-2 py-0.5 rounded">
                  <span className="font-medium">{ref.label}:</span> {ref.value}
                </span>
              ))}
            </div>
          )}
          {/* Contextual ecosystem links */}
          {(moduleKey.includes('smart_home') || moduleKey.includes('security_system')) && (
            <div className="flex flex-wrap gap-2 mt-2">
              <a href="https://domuslogic.com" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-violet-600 hover:text-violet-800 font-medium">
                <Icon name="automate" className="w-3.5 h-3.5" /> Automate this →
              </a>
              <a href="https://nodeharborpro.com" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-800 font-medium">
                <Icon name="computer" className="w-3.5 h-3.5" /> Need hardware →
              </a>
            </div>
          )}
          {moduleKey.includes('seasonal_') && (
            <div className="mt-2">
              <a href="https://mysphere.me" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-sky-600 hover:text-sky-800 font-medium">
                <Icon name="calendar" className="w-3.5 h-3.5" /> Schedule these tasks →
              </a>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 ml-3">
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3 section-content">
          {contentLoading ? (
            <div className="flex items-center gap-2 py-4">
              <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-gray-500">Loading content...</span>
            </div>
          ) : contentBlocks && contentBlocks.length > 0 ? (
            <BlockRenderer blocks={contentBlocks} />
          ) : (
            <p className="text-xs text-gray-400 italic">Content available in downloaded PDF</p>
          )}
        </div>
      )}
    </div>
  );
}

// Profile section content for profile_only sections
function ProfileSectionContent({ section, profile }: { section: string; profile: Profile }) {
  if (section === 'section_2') {
    const enabledFeatures = Object.entries(profile.features || {})
      .filter(([k, v]) => typeof v === 'boolean' && v && FEATURE_LABELS[k])
      .map(([k]) => FEATURE_LABELS[k]);
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-500">Type</p>
            <p className="text-sm text-navy-900">{HOME_TYPES[profile.home_identity.home_type] || 'Not set'}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-500">Year Built</p>
            <p className="text-sm text-navy-900">{profile.home_identity.year_built || 'Not set'}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-500">Square Feet</p>
            <p className="text-sm text-navy-900">{profile.home_identity.square_feet?.toLocaleString() || 'Not set'}</p>
          </div>
        </div>
        {enabledFeatures.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Features</p>
            <div className="flex flex-wrap gap-2">
              {enabledFeatures.map(f => <span key={f} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">{f}</span>)}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (section === 'section_4') {
    return (
      <div className="space-y-4">
        {profile.guest_sitter_mode.instructions && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-500 mb-1">House Instructions</p>
            <p className="text-sm text-gray-700">{profile.guest_sitter_mode.instructions}</p>
          </div>
        )}
        {profile.guest_sitter_mode.alarm_instructions && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-500 mb-1">Alarm</p>
            <p className="text-sm text-gray-700">{profile.guest_sitter_mode.alarm_instructions}</p>
          </div>
        )}
      </div>
    );
  }

  if (section === 'section_7') {
    const cv = profile.contacts_vendors;
    const hasProviders = cv.plumber?.name || cv.electrician?.name || cv.hvac_tech?.name;
    const missingProviders = [
      !cv.plumber?.name && 'Plumber',
      !cv.electrician?.name && 'Electrician',
      !cv.hvac_tech?.name && 'HVAC Tech',
      !cv.handyman?.name && 'Handyman',
    ].filter(Boolean);

    return (
      <div className="space-y-4">
        {cv.emergency_contacts?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Emergency Contacts</p>
            {cv.emergency_contacts.map((c, i) => (
              <p key={i} className="text-sm text-gray-700">{c.name} ({c.relationship}) - {c.phone}</p>
            ))}
          </div>
        )}

        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Service Providers</p>
          {hasProviders ? (
            <div className="grid sm:grid-cols-2 gap-3 mb-3">
              {cv.plumber?.name && <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs font-medium text-gray-500">Plumber</p><p className="text-sm text-navy-900">{cv.plumber.name}</p><p className="text-xs text-gray-500">{cv.plumber.phone}</p></div>}
              {cv.electrician?.name && <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs font-medium text-gray-500">Electrician</p><p className="text-sm text-navy-900">{cv.electrician.name}</p><p className="text-xs text-gray-500">{cv.electrician.phone}</p></div>}
              {cv.hvac_tech?.name && <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs font-medium text-gray-500">HVAC</p><p className="text-sm text-navy-900">{cv.hvac_tech.name}</p><p className="text-xs text-gray-500">{cv.hvac_tech.phone}</p></div>}
              {cv.handyman?.name && <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs font-medium text-gray-500">Handyman</p><p className="text-sm text-navy-900">{cv.handyman.name}</p><p className="text-xs text-gray-500">{cv.handyman.phone}</p></div>}
            </div>
          ) : null}

          {missingProviders.length > 0 && (
            <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <span className="w-8 h-8 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0"><Icon name="tools" className="w-4 h-4" /></span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-emerald-900">Need trusted service providers?</p>
                  <p className="text-xs text-emerald-700 mt-0.5">
                    {missingProviders.length === 4
                      ? "You haven't added any service providers yet."
                      : `Missing: ${missingProviders.join(', ')}`}
                  </p>
                  <a
                    href="https://homesureapp.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 mt-2 text-sm font-semibold text-emerald-700 hover:text-emerald-800"
                  >
                    Find providers on HomeSureApp.com
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                </div>
              </div>
            </div>
          )}

          <div className="bg-brand-50 border border-brand-100 rounded-lg p-4 mt-3">
            <div className="flex items-start gap-3">
              <span className="w-8 h-8 rounded-lg bg-brand-100 text-brand-600 flex items-center justify-center flex-shrink-0"><Icon name="sparkles" className="w-4 h-4" /></span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-brand-900">Want someone to handle it all?</p>
                <p className="text-xs text-brand-700 mt-0.5">
                  GetLiberated manages your home services, providers, maintenance, and more — so you don't have to.
                </p>
                <a
                  href="https://getliberated.me"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 mt-2 text-sm font-semibold text-brand-700 hover:text-brand-800"
                >
                  Learn more at GetLiberated.me
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

/* ══════════════════════════════════════════════════════════════════
   COMMAND CENTER — action-driven home dashboard (v2 layout)
   ══════════════════════════════════════════════════════════════════ */
const PROVIDER_KEYS = [
  { key: 'plumber', label: 'Plumber', iconName: 'plumber' },
  { key: 'electrician', label: 'Electrician', iconName: 'electrician' },
  { key: 'hvac_tech', label: 'HVAC Tech', iconName: 'hvac_tech' },
  { key: 'handyman', label: 'Handyman', iconName: 'handyman' },
  { key: 'locksmith', label: 'Locksmith', iconName: 'locksmith' },
  { key: 'roofer', label: 'Roofer', iconName: 'roofer' },
  { key: 'landscaper', label: 'Landscaper', iconName: 'landscaper' },
  { key: 'pool_service', label: 'Pool Service', iconName: 'pool_service' },
  { key: 'pest_control', label: 'Pest Control', iconName: 'pest_control' },
  { key: 'restoration_company', label: 'Restoration', iconName: 'restoration' },
  { key: 'appliance_repair', label: 'Appliance Repair', iconName: 'appliance_repair' },
  { key: 'garage_door', label: 'Garage Door', iconName: 'garage_door' },
] as const;

function CommandCenter({ profile, updateProfile, updateNestedProfile, onSave, hasChanges, saving }: {
  profile: Profile;
  updateProfile: (s: string, f: string, v: any) => void;
  updateNestedProfile: (s: string, ss: string, f: string, v: any) => void;
  onSave: () => void;
  hasChanges: boolean;
  saving: boolean;
}) {
  const [editingCard, setEditingCard] = useState<string | null>(null);
  const cv = profile.contacts_vendors;
  const gsm = profile.guest_sitter_mode;
  const cl = profile.critical_locations;

  const toggleEdit = (c: string) => setEditingCard(editingCard === c ? null : c);

  const UTILITY_KEYS = [
    { key: 'power' as const, label: 'Power', iconName: 'bolt' },
    { key: 'gas' as const, label: 'Gas', iconName: 'gas' },
    { key: 'water' as const, label: 'Water', iconName: 'water' },
    { key: 'isp' as const, label: 'Internet', iconName: 'signal' },
  ];

  const filledProviders = PROVIDER_KEYS.filter(p => (cv as any)[p.key]?.name && !(cv as any)[p.key]?.skip);
  const emptyProviders = PROVIDER_KEYS.filter(p => !(cv as any)[p.key]?.name && !(cv as any)[p.key]?.skip);
  const contactCount = (cv.emergency_contacts ?? []).filter(c => c.name.trim()).length + (cv.neighbors ?? []).filter(c => c.name.trim()).length;
  const knownLocations = Object.values(cl).filter((l: any) => l?.status === 'known').length;
  const totalLocations = Object.keys(LOCATION_LABELS).length;

  return (
    <div className="space-y-4">
      {/* ── Hero Header ── */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-brand-800 via-brand-700 to-brand-900 text-white p-5 sm:p-6">
        <div className="absolute top-0 right-0 w-48 h-48 bg-brand-600/30 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-32 h-32 bg-coral-500/15 rounded-full blur-2xl translate-y-1/2 -translate-x-1/3" />
        <div className="relative z-10 flex items-start justify-between">
          <div>
            <p className="text-[10px] font-semibold text-brand-200 uppercase tracking-wider mb-1">Command Center</p>
            <h2 className="font-display text-xl sm:text-2xl">{profile.home_identity.home_nickname || 'My Home'}</h2>
            <p className="text-sm text-brand-100 mt-1">
              {[profile.home_identity.address_line1, profile.home_identity.city, profile.home_identity.state].filter(Boolean).join(', ')}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full backdrop-blur ${contactCount > 0 ? 'bg-white/20 text-white' : 'bg-white/10 text-brand-200'}`}>{contactCount} contact{contactCount !== 1 ? 's' : ''}</span>
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full backdrop-blur ${filledProviders.length > 0 ? 'bg-white/20 text-white' : 'bg-white/10 text-brand-200'}`}>{filledProviders.length} provider{filledProviders.length !== 1 ? 's' : ''}</span>
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full backdrop-blur ${knownLocations > 0 ? 'bg-white/20 text-white' : 'bg-white/10 text-brand-200'}`}>{knownLocations}/{totalLocations} locations</span>
          </div>
        </div>
      </div>

      {/* ── Row 1: Emergency Contacts + Guest & Safety ── */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* People — Emergency Contacts + Neighbors unified */}
        <div className={`${cardPrimary} p-5`}>
          <CardHeader title="People" iconName="emergency_contacts" editing={editingCard === 'contacts'} onToggleEdit={() => toggleEdit('contacts')} count={contactCount} />
          {contactCount === 0 && editingCard !== 'contacts' ? (
            <button onClick={() => toggleEdit('contacts')} className="w-full text-left text-xs text-gray-400 hover:text-brand-600 transition py-2">
              <span className="text-brand-500 font-semibold">+</span> Add contacts & neighbors — used in every playbook
            </button>
          ) : editingCard === 'contacts' ? (
            <div className="space-y-3">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className={sectionLabel}>Emergency Contacts</p>
                  <button onClick={() => { updateProfile('contacts_vendors', 'emergency_contacts', [...(cv.emergency_contacts ?? []), { name: '', phone: '', relationship: '' }]); }} className="text-xs font-semibold text-brand-600 hover:text-brand-800" type="button">+ Add</button>
                </div>
                {(cv.emergency_contacts ?? []).map((c, i) => (
                  <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-1.5 mb-1.5">
                    <input className="text-xs border border-gray-200 rounded-lg px-2 py-1.5" placeholder="Name" value={c.name} onChange={(e) => { const u = [...(cv.emergency_contacts ?? [])]; u[i] = { ...u[i], name: e.target.value }; updateProfile('contacts_vendors', 'emergency_contacts', u); }} onBlur={(e) => { const u = [...(cv.emergency_contacts ?? [])]; u[i] = { ...u[i], name: titleCase(e.target.value.trim()) }; updateProfile('contacts_vendors', 'emergency_contacts', u); }} />
                    <input className="text-xs border border-gray-200 rounded-lg px-2 py-1.5" placeholder="Phone" value={c.phone} onChange={(e) => { const u = [...(cv.emergency_contacts ?? [])]; u[i] = { ...u[i], phone: formatPhone(e.target.value) }; updateProfile('contacts_vendors', 'emergency_contacts', u); }} type="tel" />
                    <button onClick={() => updateProfile('contacts_vendors', 'emergency_contacts', (cv.emergency_contacts ?? []).filter((_, idx) => idx !== i))} className="text-red-300 hover:text-red-500 text-xs px-1" type="button">✕</button>
                  </div>
                ))}
              </div>
              <div className="border-t border-gray-100 pt-2">
                <div className="flex items-center justify-between mb-2">
                  <p className={sectionLabel}>Neighbors</p>
                  <button onClick={() => { updateProfile('contacts_vendors', 'neighbors', [...(cv.neighbors ?? []), { name: '', phone: '', relationship: '' }]); }} className="text-xs font-semibold text-brand-600 hover:text-brand-800" type="button">+ Add</button>
                </div>
                {(cv.neighbors ?? []).map((c, i) => (
                  <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-1.5 mb-1.5">
                    <input className="text-xs border border-gray-200 rounded-lg px-2 py-1.5" placeholder="Name" value={c.name} onChange={(e) => { const u = [...(cv.neighbors ?? [])]; u[i] = { ...u[i], name: e.target.value }; updateProfile('contacts_vendors', 'neighbors', u); }} onBlur={(e) => { const u = [...(cv.neighbors ?? [])]; u[i] = { ...u[i], name: titleCase(e.target.value.trim()) }; updateProfile('contacts_vendors', 'neighbors', u); }} />
                    <input className="text-xs border border-gray-200 rounded-lg px-2 py-1.5" placeholder="Phone" value={c.phone} onChange={(e) => { const u = [...(cv.neighbors ?? [])]; u[i] = { ...u[i], phone: formatPhone(e.target.value) }; updateProfile('contacts_vendors', 'neighbors', u); }} type="tel" />
                    <button onClick={() => updateProfile('contacts_vendors', 'neighbors', (cv.neighbors ?? []).filter((_, idx) => idx !== i))} className="text-red-300 hover:text-red-500 text-xs px-1" type="button">✕</button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {(cv.emergency_contacts ?? []).filter(c => c.name.trim()).map((c, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-brand-50/30 transition">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold flex-shrink-0">{c.name.charAt(0).toUpperCase()}</div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-navy-900 truncate">{c.name}</p>
                      <p className="text-[10px] text-gray-400">{c.relationship || 'Contact'}</p>
                    </div>
                  </div>
                  <PhoneLink phone={c.phone} className="text-xs flex-shrink-0 ml-2" />
                </div>
              ))}
              {(cv.neighbors ?? []).filter(c => c.name.trim()).map((c, i) => (
                <div key={`n-${i}`} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-brand-50/30 transition">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-7 h-7 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-xs font-semibold flex-shrink-0">{c.name.charAt(0).toUpperCase()}</div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-navy-900 truncate">{c.name}</p>
                      <p className="text-[10px] text-gray-400">Neighbor</p>
                    </div>
                  </div>
                  <PhoneLink phone={c.phone} className="text-xs flex-shrink-0 ml-2" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Guest & Safety */}
        <div className={`${cardSecondary} p-5`}>
          <CardHeader title="Guest & Safety" iconName="guest_safety" editing={editingCard === 'guest'} onToggleEdit={() => toggleEdit('guest')} />
          {editingCard === 'guest' ? (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div><label className="block text-xs font-medium text-gray-500 mb-0.5">Fire Meeting Point</label><input className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" value={gsm.fire_meeting_point || ''} onChange={(e) => updateProfile('guest_sitter_mode', 'fire_meeting_point', e.target.value)} placeholder="e.g., Mailbox" /></div>
                <div><label className="block text-xs font-medium text-gray-500 mb-0.5">Safe Room</label><input className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" value={gsm.safe_room_location || ''} onChange={(e) => updateProfile('guest_sitter_mode', 'safe_room_location', e.target.value)} placeholder="e.g., Basement" /></div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div><label className="block text-xs font-medium text-gray-500 mb-0.5">WiFi Password</label><input className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" value={gsm.wifi_password || ''} onChange={(e) => updateProfile('guest_sitter_mode', 'wifi_password', e.target.value)} /></div>
                <div><label className="block text-xs font-medium text-gray-500 mb-0.5">Garage Code</label><input className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" value={gsm.garage_code || ''} onChange={(e) => updateProfile('guest_sitter_mode', 'garage_code', e.target.value)} /></div>
              </div>
              <div><label className="block text-xs font-medium text-gray-500 mb-0.5">House Instructions</label><textarea className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" rows={2} value={gsm.instructions} onChange={(e) => updateProfile('guest_sitter_mode', 'instructions', e.target.value)} placeholder="Thermostat, trash day..." /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-0.5">Alarm</label><textarea className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" rows={2} value={gsm.alarm_instructions} onChange={(e) => updateProfile('guest_sitter_mode', 'alarm_instructions', e.target.value)} placeholder="Code, arm/disarm..." /></div>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Safety row */}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-xl px-2.5 py-2 bg-gray-50">
                  <p className={sectionLabel}>Meeting Point</p>
                  {gsm.fire_meeting_point ? <p className="text-xs text-navy-900 mt-0.5">{gsm.fire_meeting_point}</p> : <p className="text-xs text-gray-300 mt-0.5">Not set</p>}
                </div>
                <div className="rounded-xl px-2.5 py-2 bg-gray-50">
                  <p className={sectionLabel}>Safe Room</p>
                  {gsm.safe_room_location ? <p className="text-xs text-navy-900 mt-0.5">{gsm.safe_room_location}</p> : <p className="text-xs text-gray-300 mt-0.5">Not set</p>}
                </div>
              </div>
              {/* Access row */}
              <div className="grid grid-cols-2 gap-2">
                {gsm.wifi_password ? (
                  <div className="flex items-center justify-between bg-gray-50 rounded-xl px-2.5 py-2">
                    <div><p className={sectionLabel}>WiFi</p><p className="text-xs text-navy-900 font-mono mt-0.5">{gsm.wifi_password}</p></div>
                    <CopyButton text={gsm.wifi_password} label="WiFi" />
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-xl px-2.5 py-2"><p className={sectionLabel}>WiFi</p><p className="text-xs text-gray-300 mt-0.5">Not set</p></div>
                )}
                {gsm.garage_code ? (
                  <div className="flex items-center justify-between bg-gray-50 rounded-xl px-2.5 py-2">
                    <div><p className={sectionLabel}>Garage</p><p className="text-xs text-navy-900 font-mono mt-0.5">{gsm.garage_code}</p></div>
                    <CopyButton text={gsm.garage_code} label="code" />
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-xl px-2.5 py-2"><p className={sectionLabel}>Garage</p><p className="text-xs text-gray-300 mt-0.5">Not set</p></div>
                )}
              </div>
              {/* Instructions */}
              {(gsm.instructions || gsm.alarm_instructions) && (
                <div className="pt-1.5 border-t border-gray-50 space-y-1">
                  {gsm.instructions && <p className="text-xs text-gray-500 line-clamp-1"><span className="font-medium text-gray-400">Instructions:</span> {gsm.instructions}</p>}
                  {gsm.alarm_instructions && <p className="text-xs text-gray-500 line-clamp-1"><span className="font-medium text-gray-400">Alarm:</span> {gsm.alarm_instructions}</p>}
                </div>
              )}
              {/* Escalation */}
              {gsm.escalation_contacts?.filter(c => c.name.trim()).length > 0 && (
                <div className="pt-1.5 border-t border-gray-50">
                  {gsm.escalation_contacts.filter(c => c.name.trim()).map((c, i) => (
                    <div key={i} className="flex items-center justify-between py-0.5">
                      <p className="text-xs text-gray-600">{c.name}</p>
                      <PhoneLink phone={c.phone} className="text-xs" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Row 2: Service Providers (full width) ── */}
      <div className={`${cardSecondary} p-5`}>
        <CardHeader title="Service Providers" iconName="service_providers" editing={editingCard === 'providers'} onToggleEdit={() => toggleEdit('providers')} count={filledProviders.length} />
        {editingCard === 'providers' ? (
          <div className="space-y-2">
            <div className="grid md:grid-cols-2 gap-x-4 gap-y-2">
              {PROVIDER_KEYS.map(({ key, label, iconName }) => {
                const p = (cv as any)[key];
                return (
                  <div key={key} className="grid grid-cols-[100px_1fr_1fr] gap-1.5 items-center">
                    <span className="text-xs text-gray-500 flex items-center gap-1 truncate"><Icon name={iconName} className="w-3.5 h-3.5 text-gray-400" />{label}</span>
                    <input type="text" value={p?.name || ''} onChange={(e) => updateNestedProfile('contacts_vendors', key, 'name', e.target.value)} onBlur={(e) => updateNestedProfile('contacts_vendors', key, 'name', titleCase(e.target.value.trim()))} placeholder="Name" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                    <input type="tel" value={p?.phone || ''} onChange={(e) => updateNestedProfile('contacts_vendors', key, 'phone', formatPhone(e.target.value))} placeholder="Phone" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                  </div>
                );
              })}
            </div>
            <div className="pt-2 border-t border-gray-100">
              <a href="https://homesureapp.com" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs text-emerald-600 hover:text-emerald-700 font-medium">
                Find trusted providers on HomeSureApp.com
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            </div>
          </div>
        ) : filledProviders.length === 0 ? (
          <div>
            <button onClick={() => toggleEdit('providers')} className="w-full text-left py-3 group">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gray-100 group-hover:bg-brand-50 text-gray-400 group-hover:text-brand-500 flex items-center justify-center transition">
                  <Icon name="tools" className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600 group-hover:text-brand-700 transition">Add your service providers</p>
                  <p className="text-xs text-gray-400 mt-0.5">Plumber, electrician, HVAC, and more</p>
                </div>
              </div>
            </button>
            <a href="https://homesureapp.com" target="_blank" rel="noopener noreferrer" className="block mt-2 pt-2 border-t border-gray-50 text-xs text-emerald-500 hover:text-emerald-600 font-medium text-center">
              Find providers on HomeSure &rarr;
            </a>
          </div>
        ) : (
          <div>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
              {filledProviders.map(({ key, label, iconName }) => {
                const p = (cv as any)[key];
                return (
                  <div key={key} className="flex items-center gap-2 py-1.5 px-2.5 rounded-lg bg-gray-50 hover:bg-gray-100 transition">
                    <Icon name={iconName} className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className={sectionLabel}>{label}</p>
                      <p className="text-xs font-semibold text-navy-900 truncate">{p.name}</p>
                    </div>
                    <PhoneLink phone={p.phone} className="text-xs flex-shrink-0" />
                  </div>
                );
              })}
            </div>
            {emptyProviders.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-50 flex items-center justify-between">
                <div className="flex flex-wrap gap-1">
                  {emptyProviders.slice(0, 4).map(({ label }) => (
                    <span key={label} className="text-xs bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded">{label}</span>
                  ))}
                  {emptyProviders.length > 4 && <span className="text-xs text-gray-300">+{emptyProviders.length - 4}</span>}
                </div>
                <a href="https://homesureapp.com" target="_blank" rel="noopener noreferrer" className="text-xs text-emerald-500 hover:text-emerald-600 font-medium flex-shrink-0 ml-2">Find on HomeSure →</a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Row 3: Utilities & Insurance + Critical Locations ── */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Utilities & Insurance */}
        <div className={`${cardSecondary} p-5`}>
          <CardHeader title="Utilities & Insurance" iconName="utilities" editing={editingCard === 'utilities'} onToggleEdit={() => toggleEdit('utilities')} />
          {editingCard === 'utilities' ? (
            <div className="space-y-3">
              {UTILITY_KEYS.map(({ key, label, iconName }) => {
                const u = cv[key];
                return (
                  <div key={key}>
                    <p className={`${sectionLabel} mb-1 flex items-center gap-1`}><Icon name={iconName} className="w-3.5 h-3.5" />{label}</p>
                    <div className="grid grid-cols-3 gap-1.5">
                      <input type="text" value={u.company} onChange={(e) => updateNestedProfile('contacts_vendors', key, 'company', e.target.value)} onBlur={(e) => updateNestedProfile('contacts_vendors', key, 'company', titleCase(e.target.value.trim()))} placeholder="Company" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                      <input type="text" value={u.account_number} onChange={(e) => updateNestedProfile('contacts_vendors', key, 'account_number', e.target.value)} placeholder="Account #" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                      <input type="tel" value={u.phone} onChange={(e) => updateNestedProfile('contacts_vendors', key, 'phone', formatPhone(e.target.value))} placeholder="Phone" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                    </div>
                  </div>
                );
              })}
              <div className="border-t border-gray-100 pt-2">
                <p className={`${sectionLabel} mb-1 flex items-center gap-1`}><Icon name="insurance" className="w-3.5 h-3.5" />Insurance</p>
                <div className="grid grid-cols-3 gap-1.5">
                  <input type="text" value={cv.insurance.provider} onChange={(e) => updateNestedProfile('contacts_vendors', 'insurance', 'provider', e.target.value)} onBlur={(e) => updateNestedProfile('contacts_vendors', 'insurance', 'provider', titleCase(e.target.value.trim()))} placeholder="Provider" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                  <input type="text" value={cv.insurance.policy_number} onChange={(e) => updateNestedProfile('contacts_vendors', 'insurance', 'policy_number', e.target.value)} placeholder="Policy #" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                  <input type="tel" value={cv.insurance.claim_phone} onChange={(e) => updateNestedProfile('contacts_vendors', 'insurance', 'claim_phone', formatPhone(e.target.value))} placeholder="Claims phone" className="text-xs border border-gray-200 rounded px-2 py-1.5" />
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {UTILITY_KEYS.map(({ key, label, iconName }) => {
                const u = cv[key];
                return (
                  <div key={key} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <Icon name={iconName} className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      <div className="min-w-0">
                        {u.company ? (
                          <p className="text-xs text-navy-900 truncate">{u.company}{u.account_number ? <span className="text-gray-300 ml-1.5">#{u.account_number}</span> : ''}</p>
                        ) : (
                          <p className="text-xs text-gray-400 italic">Add {label.toLowerCase()}</p>
                        )}
                      </div>
                    </div>
                    <PhoneLink phone={u.phone} className="text-xs flex-shrink-0 ml-2" />
                  </div>
                );
              })}
              <div className="flex items-center justify-between py-1.5 pt-2 border-t border-gray-100">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon name="insurance" className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <div className="min-w-0">
                    {cv.insurance.provider ? (
                      <p className="text-xs text-navy-900 truncate">{cv.insurance.provider}{cv.insurance.policy_number ? <span className="text-gray-300 ml-1.5">#{cv.insurance.policy_number}</span> : ''}</p>
                    ) : (
                      <p className="text-xs text-gray-300">Insurance — not added</p>
                    )}
                  </div>
                </div>
                <PhoneLink phone={cv.insurance.claim_phone} className="text-xs flex-shrink-0 ml-2" />
              </div>
            </div>
          )}
        </div>

        {/* Critical Locations */}
        <div className={`${cardPrimary} p-5`}>
          <CardHeader title="Critical Locations" iconName="critical_locations" editing={editingCard === 'locations'} onToggleEdit={() => toggleEdit('locations')} count={knownLocations} />
          {editingCard === 'locations' ? (
            <div className="space-y-2">
              {Object.entries(LOCATION_LABELS).map(([key, label]) => {
                const loc = cl[key] || { status: 'unknown', location: '' };
                return (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-xs text-gray-600 w-24 flex-shrink-0">{label}</span>
                    <select value={loc.status} onChange={(e) => updateNestedProfile('critical_locations', key, 'status', e.target.value)} className="text-xs border border-gray-200 rounded px-1.5 py-1.5">
                      <option value="unknown">Unknown</option>
                      <option value="known">Known</option>
                    </select>
                    {loc.status === 'known' && (
                      <input type="text" value={loc.location} onChange={(e) => updateNestedProfile('critical_locations', key, 'location', e.target.value)} placeholder="Where?" className="flex-1 text-xs border border-gray-200 rounded px-2 py-1.5" />
                    )}
                  </div>
                );
              })}
            </div>
          ) : (() => {
              const entries = Object.entries(LOCATION_LABELS);
              const known = entries.filter(([k]) => (cl[k] || { status: 'unknown' }).status === 'known');
              const unknown = entries.filter(([k]) => (cl[k] || { status: 'unknown' }).status !== 'known');
              return (
                <div className="space-y-2">
                  {known.length > 0 && (
                    <div className="space-y-1">
                      {known.map(([key, label]) => {
                        const loc = cl[key];
                        return (
                          <div key={key} className="flex items-center gap-2.5 py-1.5 px-2.5 rounded-lg bg-brand-50/50">
                            <span className="w-2 h-2 rounded-full bg-brand-500 flex-shrink-0" />
                            <span className="text-xs font-medium text-navy-900 w-28 flex-shrink-0">{label}</span>
                            <span className="text-xs text-brand-700 truncate">{loc.location}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {unknown.length > 0 && (
                    <button onClick={() => toggleEdit('locations')} className="w-full text-left">
                      <div className="flex items-center justify-between px-2.5 py-2.5 rounded-lg bg-gray-50 hover:bg-amber-50 transition group">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-amber-300 flex-shrink-0" />
                          <span className="text-xs text-gray-500">
                            <span className="font-semibold text-amber-600">{unknown.length}</span> location{unknown.length !== 1 ? 's' : ''} to identify
                          </span>
                        </div>
                        <span className="text-xs font-medium text-amber-600 opacity-0 group-hover:opacity-100 transition">
                          Add now
                        </span>
                      </div>
                    </button>
                  )}
                </div>
              );
            })()}
        </div>
      </div>

      {/* ── Home Details (collapsed) ── */}
      <InfoSection title="Home Details & Systems" expanded={editingCard === 'details'} onToggle={() => toggleEdit('details')}>
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Input label="Address" value={profile.home_identity.address_line1} onChange={(v) => updateProfile('home_identity', 'address_line1', v)} capitalize="title" />
            <Input label="City" value={profile.home_identity.city} onChange={(v) => updateProfile('home_identity', 'city', v)} capitalize="title" />
            <div className="grid grid-cols-2 gap-3">
              <Input label="State" value={profile.home_identity.state} onChange={(v) => updateProfile('home_identity', 'state', v)} capitalize="upper" />
              <Input label="ZIP" value={profile.home_identity.zip_code} onChange={(v) => updateProfile('home_identity', 'zip_code', v)} />
            </div>
            <Select label="Home Type" value={profile.home_identity.home_type} options={HOME_TYPES} onChange={(v) => updateProfile('home_identity', 'home_type', v)} />
            <Input label="Year Built" type="number" value={profile.home_identity.year_built?.toString() || ''} onChange={(v) => updateProfile('home_identity', 'year_built', v ? parseInt(v) : null)} />
            <Input label="Square Feet" type="number" value={profile.home_identity.square_feet?.toString() || ''} onChange={(v) => updateProfile('home_identity', 'square_feet', v ? parseInt(v) : null)} />
          </div>
          <div className="border-t border-gray-100 pt-3">
            <p className="text-xs font-semibold text-gray-500 mb-2">HVAC</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <Input label="Filter Size" value={profile.system_details?.hvac_filter_size || ''} onChange={(v) => updateProfile('system_details', 'hvac_filter_size', v)} placeholder="e.g., 20x25x1" />
              <Input label="Filter Location" value={profile.system_details?.hvac_filter_location || ''} onChange={(v) => updateProfile('system_details', 'hvac_filter_location', v)} />
              <Input label="Make/Model" value={profile.system_details?.hvac_model || ''} onChange={(v) => updateProfile('system_details', 'hvac_model', v)} />
              <Input label="Last Serviced" value={profile.system_details?.hvac_last_serviced || ''} onChange={(v) => updateProfile('system_details', 'hvac_last_serviced', v)} />
            </div>
          </div>
          <div className="border-t border-gray-100 pt-3">
            <p className="text-xs font-semibold text-gray-500 mb-2">Water Heater</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <Select label="Type" value={profile.system_details?.water_heater_type || ''} options={{ gas: 'Gas Tank', electric: 'Electric Tank', tankless_gas: 'Tankless Gas', tankless_electric: 'Tankless Electric' }} onChange={(v) => updateProfile('system_details', 'water_heater_type', v)} />
              <Input label="Location" value={profile.system_details?.water_heater_location || ''} onChange={(v) => updateProfile('system_details', 'water_heater_location', v)} />
            </div>
          </div>
          {profile.features?.has_generator && (
            <div className="border-t border-gray-100 pt-3">
              <p className="text-xs font-semibold text-gray-500 mb-2">Generator</p>
              <div className="grid sm:grid-cols-3 gap-3">
                <Input label="Location" value={profile.system_details?.generator_location || ''} onChange={(v) => updateProfile('system_details', 'generator_location', v)} />
                <Select label="Fuel" value={profile.system_details?.generator_fuel_type || ''} options={{ gasoline: 'Gasoline', propane: 'Propane', natural_gas: 'Natural Gas', diesel: 'Diesel' }} onChange={(v) => updateProfile('system_details', 'generator_fuel_type', v)} />
                <Input label="Wattage" value={profile.system_details?.generator_wattage || ''} onChange={(v) => updateProfile('system_details', 'generator_wattage', v)} />
              </div>
            </div>
          )}
          {profile.features?.has_security_system && (
            <div className="border-t border-gray-100 pt-3">
              <p className="text-xs font-semibold text-gray-500 mb-2">Security System</p>
              <div className="grid sm:grid-cols-3 gap-3">
                <Input label="Company" value={profile.system_details?.alarm_company || ''} onChange={(v) => updateProfile('system_details', 'alarm_company', v)} />
                <Input label="Company Phone" value={profile.system_details?.alarm_company_phone || ''} onChange={(v) => updateProfile('system_details', 'alarm_company_phone', v)} />
                <Input label="Panel Location" value={profile.system_details?.alarm_panel_location || ''} onChange={(v) => updateProfile('system_details', 'alarm_panel_location', v)} />
              </div>
            </div>
          )}
        </div>
      </InfoSection>

      {/* Floating save bar */}
      {hasChanges && (
        <div className="sticky bottom-4 z-30">
          <div className="bg-navy-900 text-white rounded-lg shadow-lg px-5 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-sm font-medium">Unsaved changes</span>
            </div>
            <button onClick={onSave} disabled={saving} className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-1.5 rounded-lg text-sm font-semibold transition disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoSection({ title, expanded, onToggle, children }: { title: string; expanded: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <div className={`${cardSecondary} overflow-hidden`}>
      <button onClick={onToggle} className="w-full px-5 py-3.5 flex items-center justify-between hover:bg-gray-50 transition bg-gray-50/50">
        <span className="font-semibold text-navy-900 text-sm">{title}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && <div className="px-4 pb-4 pt-3">{children}</div>}
    </div>
  );
}

function Input({ label, value, onChange, type = 'text', placeholder, capitalize }: { label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string; capitalize?: 'title' | 'upper' }) {
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const v = e.target.value.trim();
    if (!v) return;
    if (capitalize === 'title') onChange(titleCase(v));
    else if (capitalize === 'upper') onChange(v.toUpperCase());
  };
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} onBlur={handleBlur} placeholder={placeholder} className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2" />
    </div>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: Record<string, string>; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2">
        <option value="">Select...</option>
        {Object.entries(options).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
    </div>
  );
}
