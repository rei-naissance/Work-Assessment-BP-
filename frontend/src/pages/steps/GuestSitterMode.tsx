import StepCard from '../../components/StepCard';
import type { Profile, EmergencyContact } from '../../types';
import { inputClass, labelClass, hintClass, checkboxClass, textareaClass } from '../../styles/form';
import { Icon } from '../../components/Icons';

const EMPTY_CONTACT: EmergencyContact = { name: '', phone: '', relationship: '' };

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 10);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

function SectionStatus({ filled, label }: { filled: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full ${filled ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-100 text-gray-500 border border-gray-200'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${filled ? 'bg-emerald-500' : 'bg-gray-300'}`} />
      {label}
    </span>
  );
}

export default function GuestSitterMode({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  const gm = profile.guest_sitter_mode;
  const hasPets = profile.household.has_pets;

  const updateGM = (field: string, value: any) => {
    onChange({ ...profile, guest_sitter_mode: { ...gm, [field]: value } });
  };

  const updatePetInfo = (field: string, value: string) => {
    onChange({ ...profile, guest_sitter_mode: { ...gm, pet_sitter_info: { ...gm.pet_sitter_info, [field]: value } } });
  };

  const contacts = gm.escalation_contacts;
  const addContact = () => updateGM('escalation_contacts', [...contacts, { ...EMPTY_CONTACT }]);
  const removeContact = (i: number) => updateGM('escalation_contacts', contacts.filter((_: any, idx: number) => idx !== i));
  const updateContact = (i: number, field: string, value: string) => {
    const updated = contacts.map((c: EmergencyContact, idx: number) => (idx === i ? { ...c, [field]: value } : c));
    updateGM('escalation_contacts', updated);
  };

  // Status tracking
  const hasMeetingPoint = !!gm.fire_meeting_point?.trim();
  const hasWifi = !!gm.wifi_password?.trim();
  const hasGarageCode = !!gm.garage_code?.trim();
  const hasSafeRoom = !!gm.safe_room_location?.trim();
  const hasInstructions = gm.skip_instructions || !!gm.instructions?.trim();
  const hasAlarm = gm.skip_alarm || !!gm.alarm_instructions?.trim();
  const hasEscalation = gm.skip_escalation || contacts.length > 0;
  const hasPetInfo = !hasPets || gm.skip_pet_sitter || !!(gm.pet_sitter_info.feeding_instructions?.trim() || gm.pet_sitter_info.vet_name?.trim());

  const quickAccessCount = [hasWifi, hasGarageCode, hasSafeRoom].filter(Boolean).length;

  return (
    <StepCard title="Guest & Sitter Mode" subtitle="This information generates a standalone Guest & Sitter Packet — a separate printable document you can leave for anyone watching your home.">
      <div className="space-y-6">
        {/* Impact callout */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="w-9 h-9 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0"><Icon name="checklist" className="w-4.5 h-4.5" /></span>
            <div>
              <p className="text-sm font-semibold text-navy-900">This generates a separate printable document</p>
              <p className="text-xs text-gray-500 mt-0.5">Your <strong>Guest & Sitter Packet</strong> is a standalone PDF with everything a house sitter, guest, or family member needs — WiFi, alarm codes, pet care, emergency contacts, and who to call if something breaks. Print it and leave it on the counter.</p>
            </div>
          </div>
        </div>

        {/* Status pills */}
        <div className="flex flex-wrap gap-2">
          <SectionStatus filled={hasMeetingPoint} label="Meeting Point" />
          <SectionStatus filled={quickAccessCount === 3} label={`Quick Access (${quickAccessCount}/3)`} />
          <SectionStatus filled={hasInstructions} label="Instructions" />
          <SectionStatus filled={hasAlarm} label="Alarm" />
          <SectionStatus filled={hasEscalation} label="Escalation Contacts" />
          {hasPets && <SectionStatus filled={hasPetInfo} label="Pet Info" />}
        </div>

        {/* Critical Safety Info */}
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="w-9 h-9 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-sm font-semibold">!</span>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-rose-800 mb-1">Emergency Meeting Point</h3>
              <p className="text-xs text-rose-700 mb-3">Where should everyone meet if there's a fire or emergency evacuation? This appears in your emergency playbooks <strong>and</strong> your Guest & Sitter Packet.</p>
              <input
                className={inputClass}
                placeholder="e.g., Mailbox at end of driveway, neighbor's front yard"
                value={gm.fire_meeting_point || ''}
                onChange={(e) => updateGM('fire_meeting_point', e.target.value)}
              />
              {!hasMeetingPoint && (
                <p className="text-[11px] text-rose-600 mt-1.5 font-medium">This is the most important safety field on this page. A fire evacuation plan needs a designated meeting point.</p>
              )}
            </div>
          </div>
        </div>

        {/* Quick Access Info */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Quick Access Info</h3>
            <span className="text-[11px] text-gray-400">{quickAccessCount} of 3 filled</span>
          </div>
          <p className="text-xs text-gray-500 mb-3">These appear on the first page of your Guest & Sitter Packet — the essentials a guest needs within the first 5 minutes of arriving.</p>
          <div className="grid sm:grid-cols-3 gap-3">
            <div>
              <label className={labelClass}>WiFi Password</label>
              <input
                className={inputClass}
                placeholder="Your WiFi password"
                value={gm.wifi_password || ''}
                onChange={(e) => updateGM('wifi_password', e.target.value)}
              />
              {!hasWifi && <p className="text-[11px] text-amber-600 mt-1">Guests will ask for this first!</p>}
            </div>
            <div>
              <label className={labelClass}>Garage Code</label>
              <input
                className={inputClass}
                placeholder="Keypad code"
                value={gm.garage_code || ''}
                onChange={(e) => updateGM('garage_code', e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>Safe Room Location</label>
              <input
                className={inputClass}
                placeholder="For severe weather"
                value={gm.safe_room_location || ''}
                onChange={(e) => updateGM('safe_room_location', e.target.value)}
              />
              <p className={hintClass}>Interior room on lowest floor</p>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Sensitive fields (WiFi, garage code, alarm) are encrypted at rest and only included in your Sitter Packet — not your main binder.</p>
        </div>

        {/* General Instructions */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-sm font-semibold text-gray-800">General Instructions</label>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-gray-500">Not needed</span>
              <input
                type="checkbox"
                checked={gm.skip_instructions ?? false}
                onChange={(e) => updateGM('skip_instructions', e.target.checked)}
                className={checkboxClass}
              />
            </label>
          </div>
          <div className={gm.skip_instructions ? 'opacity-40 pointer-events-none' : ''}>
            <textarea
              className={`${textareaClass} h-24`}
              placeholder="e.g., Thermostat is set to 72, trash goes out Tuesday night, mail key is in the kitchen drawer..."
              value={gm.instructions}
              onChange={(e) => updateGM('instructions', e.target.value)}
              disabled={gm.skip_instructions}
            />
            <p className={hintClass}>Key info a guest or sitter needs on arrival. Think: what would you text someone if they were staying at your house?</p>
          </div>
        </div>

        {/* Alarm Instructions */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-sm font-semibold text-gray-800">Alarm System Instructions</label>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-gray-500">No alarm system</span>
              <input
                type="checkbox"
                checked={gm.skip_alarm ?? false}
                onChange={(e) => updateGM('skip_alarm', e.target.checked)}
                className={checkboxClass}
              />
            </label>
          </div>
          <div className={gm.skip_alarm ? 'opacity-40 pointer-events-none' : ''}>
            <textarea
              className={`${textareaClass} h-20`}
              placeholder="e.g., Code is 1234, arm when leaving, panel by front door..."
              value={gm.alarm_instructions}
              onChange={(e) => updateGM('alarm_instructions', e.target.value)}
              disabled={gm.skip_alarm}
            />
            {!gm.skip_alarm && !gm.alarm_instructions?.trim() && (
              <p className="text-[11px] text-amber-600 mt-1">If you have an alarm, a guest who doesn't know the code will trigger a false alarm — include disarm instructions here.</p>
            )}
          </div>
        </div>

        {/* Escalation Contacts */}
        <div className="border-t border-gray-200 pt-5">
          <div className="flex items-center justify-between mb-1">
            <p className="text-sm font-semibold text-gray-800">Escalation Contacts <span className="text-gray-400 font-normal">(in priority order)</span></p>
            <div className="flex items-center gap-4">
              <button onClick={addContact} className={`text-xs font-semibold text-brand-600 hover:text-brand-800 bg-brand-50 hover:bg-brand-100 px-3 py-1.5 rounded-md transition ${gm.skip_escalation ? 'opacity-40 pointer-events-none' : ''}`} type="button">+ Add Contact</button>
              <label className="flex items-center gap-2 cursor-pointer">
                <span className="text-xs text-gray-500">Not needed</span>
                <input
                  type="checkbox"
                  checked={gm.skip_escalation ?? false}
                  onChange={(e) => updateGM('skip_escalation', e.target.checked)}
                  className={checkboxClass}
                />
              </label>
            </div>
          </div>
          <div className={gm.skip_escalation ? 'opacity-40 pointer-events-none' : ''}>
            <p className={hintClass + ' mb-3'}>Who should a guest call if something goes wrong? These appear in order on your Sitter Packet.</p>
            <div className="space-y-2">
              {contacts.map((c: EmergencyContact, i: number) => (
                <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2">
                  <input className={inputClass} placeholder="Name" value={c.name} onChange={(e) => updateContact(i, 'name', e.target.value)} disabled={gm.skip_escalation} />
                  <input className={inputClass} placeholder="(555) 555-1234" type="tel" value={c.phone} onChange={(e) => updateContact(i, 'phone', formatPhone(e.target.value))} disabled={gm.skip_escalation} />
                  <input className={inputClass} placeholder="Relationship" value={c.relationship} onChange={(e) => updateContact(i, 'relationship', e.target.value)} disabled={gm.skip_escalation} />
                  <button onClick={() => removeContact(i)} className="text-red-400 hover:text-red-600 text-sm px-2 transition" type="button">Remove</button>
                </div>
              ))}
            </div>
            {contacts.length === 0 && !gm.skip_escalation && (
              <div className="mt-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                <p className="text-xs text-amber-800 font-medium">No escalation contacts added yet</p>
                <p className="text-xs text-amber-600 mt-0.5">If your sitter can't reach you and something goes wrong — a water leak, power outage, or alarm going off — who should they call next? Add at least one backup contact.</p>
              </div>
            )}
          </div>
        </div>

        {/* Pet Sitter Information */}
        {hasPets && (
          <div className="border-t border-gray-200 pt-5">
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Pet Sitter Information</p>
              <label className="flex items-center gap-2 cursor-pointer">
                <span className="text-xs text-gray-500">Not needed</span>
                <input
                  type="checkbox"
                  checked={gm.skip_pet_sitter ?? false}
                  onChange={(e) => updateGM('skip_pet_sitter', e.target.checked)}
                  className={checkboxClass}
                />
              </label>
            </div>
            {!gm.skip_pet_sitter && (
              <p className="text-xs text-gray-500 mb-3">Your pet care details get a dedicated section in the Guest & Sitter Packet — feeding schedule, medications, and vet info all in one place.</p>
            )}
            <div className={`space-y-3 ${gm.skip_pet_sitter ? 'opacity-40 pointer-events-none' : ''}`}>
              <div>
                <label className={labelClass}>Pet Name(s)</label>
                <input className={inputClass} placeholder="e.g., Luna, Max" value={gm.pet_sitter_info.pet_names} onChange={(e) => updatePetInfo('pet_names', e.target.value)} disabled={gm.skip_pet_sitter} />
              </div>
              <div>
                <label className={labelClass}>Feeding Instructions</label>
                <textarea
                  className={`${textareaClass} h-20`}
                  placeholder="e.g., Luna eats 1 cup dry food at 7am and 5pm. Max gets half a can of wet food at 6pm only..."
                  value={gm.pet_sitter_info.feeding_instructions}
                  onChange={(e) => updatePetInfo('feeding_instructions', e.target.value)}
                  disabled={gm.skip_pet_sitter}
                />
              </div>
              <div>
                <label className={labelClass}>Medications</label>
                <input className={inputClass} placeholder="Medications and schedule (or 'None')" value={gm.pet_sitter_info.medications} onChange={(e) => updatePetInfo('medications', e.target.value)} disabled={gm.skip_pet_sitter} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Vet Name</label>
                  <input className={inputClass} placeholder="Vet name" value={gm.pet_sitter_info.vet_name} onChange={(e) => updatePetInfo('vet_name', e.target.value)} disabled={gm.skip_pet_sitter} />
                </div>
                <div>
                  <label className={labelClass}>Vet Phone</label>
                  <input className={inputClass} placeholder="(555) 555-1234" type="tel" value={gm.pet_sitter_info.vet_phone} onChange={(e) => updatePetInfo('vet_phone', formatPhone(e.target.value))} disabled={gm.skip_pet_sitter} />
                  {!gm.skip_pet_sitter && !gm.pet_sitter_info.vet_phone?.trim() && gm.pet_sitter_info.pet_names?.trim() && (
                    <p className="text-[11px] text-amber-600 mt-1">If your pet has an emergency while you're away, a sitter needs this number.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* What's generated summary */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-3">
          <p className="text-xs font-semibold text-purple-800 mb-1.5">What your Guest & Sitter Packet will include:</p>
          <div className="grid grid-cols-2 gap-1.5">
            {[
              { label: 'Quick reference card (WiFi, codes, contacts)', filled: hasWifi || hasGarageCode },
              { label: 'Emergency meeting point & safe room', filled: hasMeetingPoint },
              { label: 'General house instructions', filled: hasInstructions },
              { label: 'Alarm arm/disarm instructions', filled: hasAlarm },
              { label: 'Escalation contact list (priority order)', filled: hasEscalation },
              ...(hasPets ? [{ label: 'Pet care sheet with feeding & vet info', filled: hasPetInfo }] : []),
              { label: 'Emergency playbook excerpts', filled: true },
              { label: 'Key system locations from your profile', filled: true },
            ].map((item) => (
              <span key={item.label} className={`inline-flex items-center gap-1.5 text-[11px] ${item.filled ? 'text-purple-700' : 'text-gray-400'}`}>
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${item.filled ? 'bg-purple-500' : 'bg-gray-300'}`} />
                {item.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </StepCard>
  );
}
