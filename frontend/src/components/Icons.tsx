/**
 * Centralized icon system — replaces all emojis with Heroicon SVGs.
 *
 * Usage:
 *   import { Icon } from '../components/Icons';
 *   <Icon name="emergency" className="w-5 h-5" />
 */
import {
  HomeIcon,
  HomeModernIcon,
  PuzzlePieceIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  CalendarDaysIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  RectangleStackIcon,
  SparklesIcon,
  WrenchScrewdriverIcon,
  WrenchIcon,
  FireIcon,
  SunIcon,
  BoltIcon,
  LockClosedIcon,
  CpuChipIcon,
  ArrowUpIcon,
  BeakerIcon,
  MapPinIcon,
  LightBulbIcon,
  QuestionMarkCircleIcon,
  BugAntIcon,
  HeartIcon,
  ShieldCheckIcon,
  CloudIcon,
  SignalIcon,
  PhoneIcon,
  ClipboardDocumentListIcon,
  BuildingStorefrontIcon,
  TruckIcon,
  ComputerDesktopIcon,
  ShoppingBagIcon,
  ArchiveBoxIcon,
  TrashIcon,
  ArrowPathIcon,
  ChatBubbleLeftRightIcon,
  StarIcon,
  CheckBadgeIcon,
  ServerIcon,
  Square3Stack3DIcon,
  PaintBrushIcon,
  HandRaisedIcon,
  AdjustmentsHorizontalIcon,
  GlobeAltIcon,
  BriefcaseIcon,
} from '@heroicons/react/24/outline';

import type { ComponentType, SVGProps } from 'react';

type HeroIcon = ComponentType<SVGProps<SVGSVGElement>>;

/**
 * Semantic icon map — one import, every icon in the app.
 * Grouped by usage context.
 */
const icons: Record<string, HeroIcon> = {
  // ── Home & property ──────────────────────────
  home:               HomeIcon,
  home_modern:        HomeModernIcon,
  house:              HomeIcon,
  building:           BuildingStorefrontIcon,

  // ── Emergency & safety ───────────────────────
  emergency:          ExclamationTriangleIcon,
  fire:               FireIcon,
  water:              BeakerIcon,
  water_drop:         BeakerIcon,
  power:              BoltIcon,
  bolt:               BoltIcon,
  hvac:               AdjustmentsHorizontalIcon,
  storm:              CloudIcon,
  security:           LockClosedIcon,
  shield:             ShieldCheckIcon,
  lock:               LockClosedIcon,

  // ── Service providers ────────────────────────
  wrench:             WrenchIcon,
  tools:              WrenchScrewdriverIcon,
  plumber:            WrenchIcon,
  electrician:        BoltIcon,
  hvac_tech:          AdjustmentsHorizontalIcon,
  handyman:           WrenchScrewdriverIcon,
  locksmith:          LockClosedIcon,
  roofer:             HomeIcon,
  landscaper:         GlobeAltIcon,
  pool_service:       SparklesIcon,
  pest_control:       BugAntIcon,
  restoration:        BuildingStorefrontIcon,
  appliance_repair:   Cog6ToothIcon,
  garage_door:        TruckIcon,

  // ── Utilities ────────────────────────────────
  utilities:          ClipboardDocumentListIcon,
  gas:                FireIcon,
  insurance:          ShieldCheckIcon,

  // ── Systems & features ───────────────────────
  pool:               SparklesIcon,
  hot_tub:            SparklesIcon,
  garage:             TruckIcon,
  basement:           HomeIcon,
  attic:              ArrowUpIcon,
  fireplace:          FireIcon,
  septic:             WrenchIcon,
  well_water:         BeakerIcon,
  water_softener:     BeakerIcon,
  water_filtration:   BeakerIcon,
  sump_pump:          ArrowUpIcon,
  solar:              SunIcon,
  generator:          BoltIcon,
  ev_charger:         BoltIcon,
  sprinklers:         GlobeAltIcon,
  smart_home:         CpuChipIcon,
  washer_dryer:       ShoppingBagIcon,
  dishwasher:         SparklesIcon,
  refrigerator:       ArchiveBoxIcon,
  garbage_disposal:   ArrowPathIcon,
  radon:              ExclamationTriangleIcon,

  // ── Household ────────────────────────────────
  family:             UserGroupIcon,
  pets:               HeartIcon,
  children:           UserGroupIcon,
  elderly:            HandRaisedIcon,
  allergies:          AdjustmentsHorizontalIcon,

  // ── Dashboard cards ──────────────────────────
  emergency_contacts: ExclamationTriangleIcon,
  guest_safety:       HomeModernIcon,
  service_providers:  WrenchScrewdriverIcon,
  critical_locations: MapPinIcon,

  // ── Binder sections ──────────────────────────
  inventory:          ClipboardDocumentListIcon,
  supply_kit:         BriefcaseIcon,
  seasonal:           CalendarDaysIcon,
  calendar:           CalendarDaysIcon,
  maintenance:        WrenchIcon,
  cleaning:           PaintBrushIcon,
  contacts:           RectangleStackIcon,
  document:           DocumentTextIcon,

  // ── Landing / onboarding ─────────────────────
  puzzle:             PuzzlePieceIcon,
  gear:               Cog6ToothIcon,
  tree:               GlobeAltIcon,
  party:              StarIcon,
  checklist:          ClipboardDocumentListIcon,

  // ── HelpBubble ───────────────────────────────
  bug:                BugAntIcon,
  idea:               LightBulbIcon,
  help:               QuestionMarkCircleIcon,

  // ── Cross-links ──────────────────────────────
  automate:           CpuChipIcon,
  computer:           ComputerDesktopIcon,
  schedule:           CalendarDaysIcon,
  phone:              PhoneIcon,
  signal:             SignalIcon,
  chat:               ChatBubbleLeftRightIcon,
  badge:              CheckBadgeIcon,
  server:             ServerIcon,
  stack:              Square3Stack3DIcon,
  sparkles:           SparklesIcon,
  map_pin:            MapPinIcon,
  star:               StarIcon,
  trash:              TrashIcon,
};

/* ────────────────────────────────────────────── */

interface IconProps {
  name: string;
  className?: string;
}

/**
 * Render a named icon.  Falls back to a neutral dot if the name is unknown.
 *
 *   <Icon name="emergency" className="w-5 h-5 text-gray-600" />
 */
export function Icon({ name, className = 'w-5 h-5' }: IconProps) {
  const Comp = icons[name];
  if (!Comp) {
    // Fallback: small neutral circle — never breaks layout
    return <span className={`inline-block rounded-full bg-gray-300 ${className}`} />;
  }
  return <Comp className={className} />;
}

/**
 * Icon inside a tinted container — for feature lists, card headers, etc.
 *
 *   <IconBadge name="emergency" />                  // default gray
 *   <IconBadge name="fire" size="lg" />             // large variant
 */
interface IconBadgeProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const badgeSizes = {
  sm: { container: 'w-7 h-7',  icon: 'w-3.5 h-3.5' },
  md: { container: 'w-9 h-9',  icon: 'w-4.5 h-4.5' },
  lg: { container: 'w-10 h-10', icon: 'w-5 h-5' },
};

export function IconBadge({ name, size = 'md', className = '' }: IconBadgeProps) {
  const s = badgeSizes[size];
  return (
    <span className={`${s.container} rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0 ${className}`}>
      <Icon name={name} className={s.icon} />
    </span>
  );
}

export { icons };
export default Icon;
