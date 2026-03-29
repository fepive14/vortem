'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Eye, Plus } from 'lucide-react';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { ContactFormModal } from '@/components/contacts/ContactFormModal';
import { useContacts } from '@/hooks/useContacts';
import { useMe } from '@/hooks/useAuth';
import { relativeTime } from '@/lib/utils';
import type { Contact } from '@/lib/types';

const STATUS_OPTIONS = [
  { value: '', label: 'Todos los estados' },
  { value: 'active', label: 'Activo' },
  { value: 'inactive', label: 'Inactivo' },
  { value: 'do_not_contact', label: 'No contactar' },
];

const STATUS_LABEL: Record<string, string> = {
  active: 'Activo',
  inactive: 'Inactivo',
  do_not_contact: 'No contactar',
};

export default function ContactsPage() {
  const { data: me } = useMe();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data: contacts = [], isLoading } = useContacts({
    skip: page * limit,
    limit,
    ...(statusFilter ? { status: statusFilter } : {}),
  });

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return contacts;
    return contacts.filter(
      (c) =>
        c.first_name.toLowerCase().includes(q) ||
        c.last_name.toLowerCase().includes(q) ||
        (c.email ?? '').toLowerCase().includes(q) ||
        (c.company ?? '').toLowerCase().includes(q)
    );
  }, [contacts, search]);

  const canCreate = me?.role !== 'viewer';

  const columns = [
    {
      key: 'name',
      header: 'Nombre',
      render: (c: Contact) => (
        <span className="font-medium text-gray-900">
          {c.first_name} {c.last_name}
        </span>
      ),
    },
    {
      key: 'email',
      header: 'Email',
      render: (c: Contact) => <span className="text-gray-600">{c.email ?? '—'}</span>,
    },
    {
      key: 'company',
      header: 'Empresa',
      render: (c: Contact) => <span className="text-gray-600">{c.company ?? '—'}</span>,
    },
    {
      key: 'phone',
      header: 'Teléfono',
      render: (c: Contact) => <span className="text-gray-600">{c.phone ?? '—'}</span>,
    },
    {
      key: 'status',
      header: 'Estado',
      render: (c: Contact) => (
        <Badge variant={c.status as any}>{STATUS_LABEL[c.status] ?? c.status}</Badge>
      ),
    },
    {
      key: 'assigned',
      header: 'Asignado a',
      render: (c: Contact) => (
        <span className="text-gray-600">{c.assigned_to ?? 'Sin asignar'}</span>
      ),
    },
    {
      key: 'created',
      header: 'Creado',
      render: (c: Contact) => (
        <span className="text-xs text-gray-400">{relativeTime(c.created_at)}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (c: Contact) => (
        <Link
          href={`/dashboard/contacts/${c.id}`}
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
          aria-label="Ver contacto"
        >
          <Eye className="h-4 w-4" />
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Contactos</h1>
        {canCreate && (
          <button
            onClick={() => setCreateOpen(true)}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Nuevo Contacto
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Buscar por nombre, email o empresa..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-72 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <Select
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={(v) => { setStatusFilter(v); setPage(0); }}
          className="w-48"
        />
      </div>

      <Table<Contact>
        columns={columns}
        rows={filtered}
        keyFn={(c) => c.id}
        loading={isLoading}
        emptyMessage="No hay contactos aún."
      />

      {!isLoading && (contacts.length === limit || page > 0) && (
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
            disabled={contacts.length < limit}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40"
          >
            Siguiente
          </button>
        </div>
      )}

      <ContactFormModal isOpen={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
