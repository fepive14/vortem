'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle } from 'lucide-react';
import { Table } from '@/components/ui/Table';
import { AssignLeadModal } from '@/components/leads/AssignLeadModal';
import { useLeadsQueue } from '@/hooks/useSupervisor';
import { useMe } from '@/hooks/useAuth';
import { relativeTime } from '@/lib/utils';
import type { Lead } from '@/lib/types';

export default function QueuePage() {
  const router = useRouter();
  const { data: me, isLoading: authLoading } = useMe();
  const { data: queue = [], isLoading } = useLeadsQueue();
  const [assignLead, setAssignLead] = useState<Lead | null>(null);

  // Role gate
  useEffect(() => {
    if (!authLoading && me && me.role !== 'admin' && me.role !== 'supervisor') {
      router.replace('/dashboard');
    }
  }, [me, authLoading, router]);

  const voicePreview = (lead: Lead): string => {
    const data = lead.voicehire_data as Record<string, unknown>;
    if (!data || Object.keys(data).length === 0) return '—';
    const summary = data.summary ?? data.notes ?? JSON.stringify(data);
    return String(summary).slice(0, 50);
  };

  const columns = [
    {
      key: 'name',
      header: 'Nombre',
      render: (l: Lead) => (
        <span className="font-medium text-gray-900">
          {l.first_name} {l.last_name}
        </span>
      ),
    },
    {
      key: 'email',
      header: 'Email',
      render: (l: Lead) => <span className="text-gray-600">{l.email ?? '—'}</span>,
    },
    {
      key: 'phone',
      header: 'Teléfono',
      render: (l: Lead) => <span className="text-gray-600">{l.phone ?? '—'}</span>,
    },
    {
      key: 'qualified',
      header: 'Calificado hace',
      render: (l: Lead) => (
        <span className="text-xs text-gray-400">{relativeTime(l.created_at)}</span>
      ),
    },
    {
      key: 'voicehire',
      header: 'VoiceHire',
      render: (l: Lead) => (
        <span className="max-w-xs truncate text-xs text-gray-500">{voicePreview(l)}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (l: Lead) => (
        <button
          onClick={() => setAssignLead(l)}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
        >
          Asignar
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Cola de Asignación</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Leads calificados pendientes de asignación · se actualiza cada 30s
          </p>
        </div>
        {!isLoading && (
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-medium text-indigo-700">
            {queue.length} pendiente{queue.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      <Table<Lead>
        columns={columns}
        rows={queue}
        keyFn={(l) => l.id}
        loading={isLoading}
        emptyMessage=""
      />

      {!isLoading && queue.length === 0 && (
        <div className="flex flex-col items-center py-16 text-center text-gray-400">
          <CheckCircle className="mb-3 h-12 w-12 text-green-400" />
          <p className="text-base font-medium text-gray-600">Todo al día</p>
          <p className="mt-1 text-sm">No hay leads calificados pendientes de asignación</p>
        </div>
      )}

      {assignLead && (
        <AssignLeadModal
          isOpen={!!assignLead}
          onClose={() => setAssignLead(null)}
          leadId={assignLead.id}
          leadName={`${assignLead.first_name} ${assignLead.last_name}`}
        />
      )}
    </div>
  );
}
