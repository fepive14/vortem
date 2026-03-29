import { cn } from '@/lib/utils';

type BadgeVariant =
  | 'admin'
  | 'supervisor'
  | 'agent'
  | 'viewer'
  | 'new'
  | 'contacted'
  | 'qualified'
  | 'converted'
  | 'discarded'
  | 'active'
  | 'inactive'
  | 'high'
  | 'normal';

const variantClasses: Record<BadgeVariant, string> = {
  admin: 'bg-purple-100 text-purple-800',
  supervisor: 'bg-blue-100 text-blue-800',
  agent: 'bg-green-100 text-green-800',
  viewer: 'bg-gray-100 text-gray-700',
  new: 'bg-sky-100 text-sky-800',
  contacted: 'bg-yellow-100 text-yellow-800',
  qualified: 'bg-indigo-100 text-indigo-800',
  converted: 'bg-green-100 text-green-800',
  discarded: 'bg-red-100 text-red-700',
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-600',
  high: 'bg-orange-100 text-orange-800',
  normal: 'bg-gray-100 text-gray-700',
};

interface BadgeProps {
  variant: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
