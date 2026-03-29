'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Menu } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { NotificationPanel } from '@/components/layout/NotificationPanel';
import { Spinner } from '@/components/ui/Spinner';
import { useMe } from '@/hooks/useAuth';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading, error } = useMe();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace('/login');
    }
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar
        user={user}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top header */}
        <header className="flex h-16 shrink-0 items-center border-b border-gray-200 bg-white px-4 md:px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="mr-3 rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 md:hidden"
            aria-label="Abrir menú"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex-1" />
          <NotificationPanel />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
