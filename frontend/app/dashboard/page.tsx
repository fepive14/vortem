'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useMe } from '@/hooks/useAuth';
import { Card } from '@/components/ui/Card';

interface FunnelData {
  new: number;
  contacted: number;
  qualified: number;
  converted: number;
  discarded: number;
}

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: number | undefined;
  loading: boolean;
}) {
  return (
    <Card className="p-6">
      {loading ? (
        <div className="space-y-3">
          <div className="h-8 w-20 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-28 animate-pulse rounded bg-gray-200" />
        </div>
      ) : (
        <>
          <p className="text-3xl font-bold text-gray-900">{value ?? 0}</p>
          <p className="mt-1 text-sm text-gray-500">{label}</p>
        </>
      )}
    </Card>
  );
}

export default function DashboardPage() {
  const { data: user } = useMe();

  const { data: funnel, isLoading: funnelLoading } = useQuery<FunnelData>({
    queryKey: ['reports', 'funnel'],
    queryFn: async () => {
      const res = await api.get('/api/v1/reports/funnel');
      return res.data;
    },
  });

  const { data: contacts, isLoading: contactsLoading } = useQuery<unknown[]>({
    queryKey: ['contacts', 'count'],
    queryFn: async () => {
      const res = await api.get('/api/v1/contacts?limit=1');
      return res.data;
    },
  });

  const totalLeads =
    funnel &&
    Object.values(funnel).reduce((sum: number, v) => sum + (v as number), 0);

  const stats = [
    {
      label: 'Total Leads',
      value: totalLeads,
      loading: funnelLoading,
    },
    {
      label: 'Leads Calificados',
      value: funnel?.qualified,
      loading: funnelLoading,
    },
    {
      label: 'Contactos',
      value: Array.isArray(contacts) ? contacts.length : undefined,
      loading: contactsLoading,
    },
    {
      label: 'Deals Activos',
      value: funnel?.converted,
      loading: funnelLoading,
    },
  ];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">
        Bienvenido, {user?.full_name ?? '…'}
      </h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} loading={s.loading} />
        ))}
      </div>
    </div>
  );
}
