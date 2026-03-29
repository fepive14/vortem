'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  Contact,
  Briefcase,
  BarChart2,
  Settings,
  LogOut,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { useLogout } from '@/hooks/useAuth';
import { useLeadsQueue } from '@/hooks/useSupervisor';
import type { User } from '@/lib/types';

const navItems = [
  { href: '/dashboard', label: 'Home', icon: LayoutDashboard },
  { href: '/dashboard/leads', label: 'Leads', icon: Users },
  { href: '/dashboard/contacts', label: 'Contactos', icon: Contact },
  { href: '/dashboard/deals', label: 'Deals', icon: Briefcase },
  { href: '/dashboard/reports', label: 'Reportes', icon: BarChart2 },
] as const;

interface SidebarProps {
  user: User;
}

function QueueSubItem({ pathname }: { pathname: string }) {
  const { data: queue } = useLeadsQueue();
  const count = queue?.length ?? 0;
  const isActive = pathname === '/dashboard/leads/queue';

  return (
    <li>
      <Link
        href="/dashboard/leads/queue"
        className={cn(
          'flex items-center gap-2 rounded-md py-1.5 pl-10 pr-3 text-sm transition-colors',
          isActive
            ? 'bg-blue-50 font-medium text-blue-700'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
        )}
      >
        <span className="flex-1">Cola de Asignación</span>
        {count > 0 && (
          <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {count}
          </span>
        )}
      </Link>
    </li>
  );
}

export function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const logout = useLogout();
  const isAdminOrSupervisor = user.role === 'admin' || user.role === 'supervisor';

  const allNavItems = [
    ...navItems,
    ...(user.role === 'admin'
      ? [{ href: '/dashboard/settings' as const, label: 'Configuración', icon: Settings }]
      : []),
  ];

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-gray-200 bg-white">
      {/* Wordmark */}
      <div className="flex h-16 items-center px-6">
        <span className="text-xl font-bold text-blue-600">Vortem</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        <ul className="space-y-1">
          {allNavItems.map(({ href, label, icon: Icon }) => {
            const isActive =
              href === '/dashboard'
                ? pathname === href
                : href === '/dashboard/leads'
                ? pathname === href || (pathname.startsWith(href) && pathname !== '/dashboard/leads/queue')
                : pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </Link>

                {/* Queue sub-item under Leads */}
                {href === '/dashboard/leads' && isAdminOrSupervisor && (
                  <ul className="mt-0.5">
                    <QueueSubItem pathname={pathname} />
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User info + logout */}
      <div className="border-t border-gray-200 px-4 py-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
            {user.full_name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-gray-900">{user.full_name}</p>
            <Badge variant={user.role}>{user.role}</Badge>
          </div>
        </div>
        <button
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 disabled:opacity-50"
        >
          {logout.isPending ? (
            <Spinner size="sm" />
          ) : (
            <LogOut className="h-4 w-4 shrink-0" />
          )}
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
