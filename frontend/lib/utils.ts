import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const rtf = new Intl.RelativeTimeFormat('es', { numeric: 'auto' });

export function relativeTime(dateStr: string): string {
  const diff = (new Date(dateStr).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return rtf.format(Math.round(diff), 'second');
  if (abs < 3600) return rtf.format(Math.round(diff / 60), 'minute');
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), 'hour');
  return rtf.format(Math.round(diff / 86400), 'day');
}

export function formatCurrency(value: number | null, currency: string): string {
  if (value === null) return 'Sin valor';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

const INITIALS_COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-purple-500',
  'bg-yellow-500',
  'bg-pink-500',
  'bg-indigo-500',
  'bg-red-500',
  'bg-teal-500',
];

export function initialsColor(userId: string): string {
  const code = userId.charCodeAt(0) + userId.charCodeAt(userId.length - 1);
  return INITIALS_COLORS[code % INITIALS_COLORS.length];
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    new: 'bg-sky-100 text-sky-800',
    contacted: 'bg-yellow-100 text-yellow-800',
    qualified: 'bg-indigo-100 text-indigo-800',
    converted: 'bg-green-100 text-green-800',
    discarded: 'bg-red-100 text-red-700',
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-gray-100 text-gray-600',
    do_not_contact: 'bg-red-100 text-red-700',
  };
  return map[status] ?? 'bg-gray-100 text-gray-700';
}
