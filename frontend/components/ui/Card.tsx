import { cn } from '@/lib/utils';

interface CardProps {
  className?: string;
  children: React.ReactNode;
}

export function Card({ className, children }: CardProps) {
  return (
    <div className={cn('rounded-lg bg-white shadow-sm border border-gray-100', className)}>
      {children}
    </div>
  );
}
