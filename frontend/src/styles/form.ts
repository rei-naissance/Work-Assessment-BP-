export const inputClass = 'w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 transition';
export const inputErrorClass = 'w-full rounded-lg border border-red-400 bg-white px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm focus:border-red-500 focus:ring-2 focus:ring-red-200 transition';
export const labelClass = 'block text-sm font-semibold text-gray-800 mb-1.5';
export const selectClass = 'w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 transition';
export const hintClass = 'text-xs text-gray-500 mt-1.5';
export const errorClass = 'text-xs text-red-600 mt-1.5';
export const checkboxClass = 'h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-200';
export const textareaClass = 'w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-200 transition resize-y';

/** Title Case a string — capitalizes the first letter of each word */
export function titleCase(s: string): string {
  if (!s) return s;
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}
