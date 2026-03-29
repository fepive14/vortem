'use client';

import { useState, useRef, useEffect } from 'react';
import { Bell } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNotifications, useUnreadCount, useMarkAsRead } from '@/hooks/useNotifications';
import type { Notification } from '@/lib/types';

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return 'ahora';
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

function NotificationItem({ notification }: { notification: Notification }) {
  const markAsRead = useMarkAsRead();

  return (
    <div
      className={cn(
        'border-l-4 px-4 py-3',
        notification.priority === 'high'
          ? 'border-orange-400 bg-orange-50'
          : 'border-transparent',
        !notification.read_at && 'bg-blue-50/30'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900">{notification.title}</p>
          <p className="mt-0.5 text-xs text-gray-600 line-clamp-2">{notification.body}</p>
          <p className="mt-1 text-xs text-gray-400">{timeAgo(notification.created_at)}</p>
        </div>
        {!notification.read_at && (
          <button
            onClick={() => markAsRead.mutate(notification.id)}
            disabled={markAsRead.isPending}
            className="shrink-0 text-xs text-blue-600 hover:underline disabled:opacity-50"
          >
            Marcar leído
          </button>
        )}
      </div>
    </div>
  );
}

export function NotificationPanel() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const { data: unreadData } = useUnreadCount();
  const { data: notifications } = useNotifications();

  const unreadCount = unreadData?.count ?? 0;
  const displayed = notifications?.slice(0, 10) ?? [];

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={panelRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-full text-gray-600 hover:bg-gray-100"
        aria-label="Notificaciones"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-50 w-80 rounded-lg border border-gray-200 bg-white shadow-lg">
          <div className="border-b border-gray-200 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-900">Notificaciones</h3>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-100">
            {displayed.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-gray-500">
                Sin notificaciones
              </p>
            ) : (
              displayed.map((n) => <NotificationItem key={n.id} notification={n} />)
            )}
          </div>
        </div>
      )}
    </div>
  );
}
