'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useMe } from '@/hooks/useAuth';
import { Spinner } from '@/components/ui/Spinner';

export default function RootPage() {
  const router = useRouter();
  const { data: user, isLoading } = useMe();

  useEffect(() => {
    if (!isLoading) {
      router.replace(user ? '/dashboard' : '/login');
    }
  }, [isLoading, user, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <Spinner size="lg" />
    </div>
  );
}
