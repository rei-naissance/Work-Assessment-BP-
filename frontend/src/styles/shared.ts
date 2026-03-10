// Layout — single content width for consistent spacing site-wide
export const contentWidth = 'max-w-5xl mx-auto px-4 sm:px-6';
export const pageContainer = 'max-w-5xl mx-auto px-4 sm:px-6 py-8';
export const pageContainerWide = 'max-w-5xl mx-auto px-4 sm:px-6 py-6';

// Typography
export const pageTitle = 'font-display text-2xl text-navy-900';
export const pageSubtitle = 'text-sm text-gray-500 mt-1';
export const sectionTitle = 'text-lg font-semibold text-navy-900';
export const sectionSubtitle = 'text-sm text-gray-500 mt-0.5';

// Semantic labels
export const sectionLabel = 'text-xs font-medium text-gray-500';
export const cardTitleStyle = 'text-sm font-semibold text-navy-900';

// Cards / Panels
export const card = 'bg-white rounded-lg border border-gray-200';
export const cardPadded = 'bg-white rounded-lg border border-gray-200 p-6';
export const cardPrimary = 'bg-gradient-to-b from-white to-brand-50/30 rounded-xl border border-brand-100/60 shadow-sm';
export const cardSecondary = 'bg-gradient-to-b from-white to-gray-50/50 rounded-xl border border-gray-200/70 shadow-sm';
export const cardHeader = 'px-6 py-4 border-b border-gray-100';
export const cardBody = 'px-6 py-4';

// Buttons
export const btnPrimary = 'bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-brand-700 disabled:opacity-50 transition';
export const btnSecondary = 'border border-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition';
export const btnDanger = 'bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-100 transition';
export const btnGhost = 'text-sm font-medium text-gray-600 hover:text-gray-800 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition';

// Badges
export const badge = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
export const badgeColors: Record<string, string> = {
  green: 'bg-green-100 text-green-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red: 'bg-red-100 text-red-800',
  blue: 'bg-blue-100 text-blue-800',
  orange: 'bg-orange-100 text-orange-800',
  purple: 'bg-purple-100 text-purple-800',
  gray: 'bg-gray-100 text-gray-700',
  amber: 'bg-amber-100 text-amber-700',
};

// Tables
export const tableWrapper = 'overflow-hidden overflow-x-auto';
export const table = 'w-full text-sm';
export const tableHead = 'bg-gray-50';
export const th = 'px-4 py-3 text-left text-xs font-medium text-gray-500';
export const td = 'px-4 py-3';
export const tableRow = 'hover:bg-gray-50 transition';
export const tableDivider = 'divide-y divide-gray-100';

// Modals
export const modalOverlay = 'fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50';
export const modalContent = 'bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto';

// Status indicators
export const statusDot = 'w-2 h-2 rounded-full';
