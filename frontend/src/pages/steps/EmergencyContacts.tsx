import StepCard from '../../components/StepCard';
import type { Profile, EmergencyContact } from '../../types';
import { inputClass, labelClass, selectClass, hintClass, titleCase } from '../../styles/form';
import { Icon } from '../../components/Icons';

const EMPTY_CONTACT: EmergencyContact = { name: '', phone: '', relationship: '' };

const RELATIONSHIP_OPTIONS = [
  'Spouse / Partner',
  'Parent',
  'Sibling',
  'Child',
  'Relative',
  'Friend',
  'Neighbor',
  'Landlord',
  'Property Manager',
  'Other',
];

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 10);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

function ContactList({
  label,
  hint,
  contacts,
  onChange,
  showRelationship = true,
  emptyMessage,
  emptyEncouragement,
}: {
  label: string;
  hint?: string;
  contacts: EmergencyContact[];
  onChange: (contacts: EmergencyContact[]) => void;
  showRelationship?: boolean;
  emptyMessage?: string;
  emptyEncouragement?: string;
}) {
  const add = () => onChange([...contacts, { ...EMPTY_CONTACT }]);
  const remove = (i: number) => onChange(contacts.filter((_, idx) => idx !== i));
  const update = (i: number, field: string, value: string) => {
    const updated = contacts.map((c, idx) => (idx === i ? { ...c, [field]: value } : c));
    onChange(updated);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-gray-800">{label}</p>
          {contacts.length > 0 && (
            <span className="inline-flex items-center gap-1 text-xs font-semibold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
              {contacts.filter(c => c.name.trim() && c.phone.trim()).length} added
            </span>
          )}
        </div>
        <button onClick={add} className="text-xs font-semibold text-brand-600 hover:text-brand-800 bg-brand-50 hover:bg-brand-100 px-3 py-1.5 rounded-md transition" type="button">+ Add Contact</button>
      </div>
      {hint && <p className={hintClass + ' mb-3'}>{hint}</p>}
      <div className="space-y-2">
        {contacts.map((c, i) => (
          <div key={i} className={`grid ${showRelationship ? 'grid-cols-[1fr_1fr_1fr_auto]' : 'grid-cols-[1fr_1fr_auto]'} gap-2`}>
            <input className={inputClass} placeholder="Name" value={c.name} onChange={(e) => update(i, 'name', e.target.value)} onBlur={(e) => update(i, 'name', titleCase(e.target.value.trim()))} />
            <input
              className={inputClass}
              placeholder="(555) 555-1234"
              value={c.phone}
              onChange={(e) => update(i, 'phone', formatPhone(e.target.value))}
              type="tel"
            />
            {showRelationship && (
              <select className={selectClass} value={c.relationship} onChange={(e) => update(i, 'relationship', e.target.value)}>
                <option value="">Relationship</option>
                {RELATIONSHIP_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            )}
            <button onClick={() => remove(i)} className="text-red-400 hover:text-red-600 text-sm px-2 transition" type="button">Remove</button>
          </div>
        ))}
      </div>
      {contacts.length === 0 && (
        <div className="mt-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
          <p className="text-xs text-amber-800 font-medium">{emptyMessage || 'None added yet.'}</p>
          {emptyEncouragement && <p className="text-xs text-amber-600 mt-0.5">{emptyEncouragement}</p>}
        </div>
      )}
    </div>
  );
}

export default function EmergencyContacts({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const cv = profile.contacts_vendors;
  const contactCount = cv.emergency_contacts.filter(c => c.name.trim() && c.phone.trim()).length;
  const neighborCount = cv.neighbors.filter(c => c.name.trim() && c.phone.trim()).length;

  return (
    <StepCard title="Emergency Contacts" subtitle="Add who you can now — our AI can build a ready-to-fill contact page for anyone you haven't added yet.">
  <div className="space-y-6">
        {/* Impact callout */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="w-9 h-9 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0"><Icon name="emergency_contacts" className="w-4.5 h-4.5" /></span>
            <div>
              <p className="text-sm font-semibold text-navy-900">These contacts appear throughout your emergency playbooks</p>
              <p className="text-xs text-gray-500 mt-0.5">When a pipe bursts at 2 AM or you smell gas, your binder tells you <strong>exactly who to call</strong> — no searching through your phone. Contacts you add here are woven into every relevant emergency procedure.</p>
            </div>
          </div>
        </div>

        {/* Quick status */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${contactCount > 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-100 text-gray-500 border border-gray-200'}`}>
            <span className={`w-2 h-2 rounded-full ${contactCount > 0 ? 'bg-emerald-500' : 'bg-gray-300'}`} />
            {contactCount > 0 ? `${contactCount} emergency contact${contactCount > 1 ? 's' : ''}` : 'No emergency contacts yet'}
          </div>
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${neighborCount > 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-100 text-gray-500 border border-gray-200'}`}>
            <span className={`w-2 h-2 rounded-full ${neighborCount > 0 ? 'bg-emerald-500' : 'bg-gray-300'}`} />
            {neighborCount > 0 ? `${neighborCount} neighbor${neighborCount > 1 ? 's' : ''}` : 'No neighbors yet'}
          </div>
        </div>

        <ContactList
          label="Emergency Contacts"
          hint="Family, friends, or anyone who should be reachable in a crisis."
          contacts={cv.emergency_contacts}
          onChange={(contacts) => onChange({ ...profile, contacts_vendors: { ...cv, emergency_contacts: contacts } })}
          emptyMessage="No emergency contacts added yet"
          emptyEncouragement="We recommend at least 2 emergency contacts. These appear on your Emergency Quick-Start Cards and in every playbook that involves calling for help."
        />
  <div className="border-t border-gray-200 pt-5">
          <ContactList
            label="Neighbors"
            hint="Trusted neighbors who can check on your home."
            contacts={cv.neighbors}
            onChange={(contacts) => onChange({ ...profile, contacts_vendors: { ...cv, neighbors: contacts } })}
            showRelationship={false}
            emptyMessage="No neighbors added yet"
            emptyEncouragement="A trusted neighbor can check on your home during emergencies, accept packages, or call you if something looks wrong. Even one neighbor makes a difference."
          />
        </div>

        {/* What gets generated */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
          <p className="text-xs font-semibold text-gray-700 mb-1">Where these contacts appear in your binder:</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
            {[
              'Emergency Quick-Start Cards',
              'Fire Emergency Playbook',
              'Water Leak Playbook',
              'Power Outage Playbook',
              'Security Incident Playbook',
              'Guest & Sitter Packet',
            ].map((item) => (
              <span key={item} className="inline-flex items-center gap-1 text-[11px] text-gray-500">
                <span className="w-1 h-1 rounded-full bg-brand-400 flex-shrink-0" />
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </StepCard>
  );
}
