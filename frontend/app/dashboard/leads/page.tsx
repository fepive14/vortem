'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Eye, Plus } from 'lucide-react';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { LeadFormModal } from '@/components/leads/LeadFormModal';
import { useLeads } from '@/hooks/useLeads';
import { useMe } from '@/hooks/useAuth';
import { relativeTime } from '@/lib/utils';
import type { Lead } from '@/lib/types';

const STATUS_OPTIONS = [
  { value: '', label: 'Todos los estados' },
  { value: 'new', label: 'Nuevo' },
  { value: 'contacted', label: 'Contactado' },
  { value: 'qualified', label: 'Calificado' },
  { value: 'converted', label: 'Convertido' },
  { value: 'discarded', label: 'Descartado' },
];

const SOURCE_OPTIONS = [
  { value: '', label: 'Todas las fuentes' },
  { value: 'manual', label: 'Manual' },
  { value: 'csv_import', label: 'CSV Import' },
  { value: 'api', label: 'API' },
  { value: 'voicehire', label: 'VoiceHire' },
];

const STATUS_LABEL: Record<string, string> = {
  new: 'Nuevo',
  contacted: 'Contactado',
  qualified: 'Calificado',
  converted: 'Convertido',
  discarded: 'Descartado',
};

const SOURCE_LABEL: Record<string, string> = {
  manual: 'Manual',
  csv_import: 'CSV',
  api: 'API',
  voicehire: 'VoiceHire',
};

export default function LeadsPage() {
  const { data: me } = useMe();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data: leads = [], isLoading } = useLeads({
    skip: page * limit,
    limit,
    ...(statusFilter ? { status: statusFilter } : {}),
  });

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return leads.filter((l) => {
      if (
        q &&
        !l.first_name.toLowerCase().includes(q) &&
        !l.last_name.toLowerCase().includes(q) &&
        !(l.email ?? '').toLowerCase().includes(q) &&
        !(l.phone ?? '').includes(q)
      ) {
        return false;
      }
      if (sourceFilter && l.source !== sourceFilter) return false;
      return true;
    });
  }, [leads, search, sourceFilter]);

  const canCreate = me?.role !== 'viewer';

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
      key: 'status',
      header: 'Estado',
      render: (l: Lead) => (
        <Badge variant={l.status}>{STATUS_LABEL[l.status] ?? l.status}</Badge>
      ),
    },
    {
      key: 'source',
      header: 'Fuente',
      render: (l: Lead) => (
        <span className="text-xs text-gray-500">{SOURCE_LABEL[l.source] ?? l.source}</span>
      ),
    },
    {
      key: 'assigned',
      header: 'Asignado a',
      render: (l: Lead) => (
        <span className="text-gray-600">{l.assigned_to ? l.assigned_to : 'Sin asignar'}</span>
      ),
    },
    {
      key: 'created',
      header: 'Creado',
      render: (l: Lead) => (
        <span className="text-xs text-gray-400">{relativeTime(l.created_at)}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (l: Lead) => (
        <Link
          href={`/dashboard/leads/${l.id}`}
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
          aria-label="Ver lead"
        >
          <Eye className="h-4 w-4" />
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Leads</h1>
        {canCreate && (
          <button
            onClick={() => setCreateOpen(true)}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Nuevo Lead
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Buscar por nombre, email o teléfono..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <Select
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={(v) => { setStatusFilter(v); setPage(0); }}
          className="w-44"
        />
        <Select
          options={SOURCE_OPTIONS}
          value={sourceFilter}
          onChange={(v) => { setSourceFilter(v); setPage(0); }}
          className="w-44"
        />
      </div>

      <Table<Lead>
        columns={columns}
        rows={filtered}
        keyFn={(l) => l.id}
        loading={isLoading}
        emptyMessage="No hay leads que coincidan con los filtros."
      />

      {/* Pagination */}
      {!isLoading && (leads.length === limit || page > 0) && (
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">Página {page + 1}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={leads.length < limit}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40"
          >
            Siguiente
          </button>
        </div>
      )}

      <LeadFormModal isOpen={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
