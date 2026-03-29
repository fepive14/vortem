'use client';

import { useMe } from '@/hooks/useAuth';
import { useFunnel } from '@/hooks/useReports';
import { Card } from '@/components/ui/Card';

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
  const { data: funnel, isLoading: funnelLoading } = useFunnel(30);

  const stats = [
    { label: 'Total Leads', value: funnel?.leads_total },
    { label: 'Leads Calificados', value: funnel?.leads_qualified },
    { label: 'Contactos', value: funnel?.contacts_total },
    { label: 'Deals Activos', value: funnel?.deals_total },
  ];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">
        Bienvenido, {user?.full_name ?? '…'}
      </h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} loading={funnelLoading} />
        ))}
      </div>
    </div>
  );
}
