'use client';

import { useState, KeyboardEvent } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ChevronRight, Edit, Trash2, Link2, MessageSquare, X } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { ContactFormModal } from '@/components/contacts/ContactFormModal';
import { useContact, useUpdateContact, useDeleteContact } from '@/hooks/useContacts';
import { useUsers } from '@/hooks/useUsers';
import { useMe } from '@/hooks/useAuth';
import { relativeTime } from '@/lib/utils';
import Link from 'next/link';
import type { Contact } from '@/lib/types';

const STATUS_OPTIONS = [
  { value: 'active', label: 'Activo' },
  { value: 'inactive', label: 'Inactivo' },
  { value: 'do_not_contact', label: 'No contactar' },
];

const STATUS_LABEL: Record<string, string> = {
  active: 'Activo',
  inactive: 'Inactivo',
  do_not_contact: 'No contactar',
};

export default function ContactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const { data: me } = useMe();
  const { data: contact, isLoading } = useContact(id);
  const updateContact = useUpdateContact(id);
  const deleteContact = useDeleteContact();
  const { data: users = [] } = useUsers();

  const [editOpen, setEditOpen] = useState(false);
  const [tagInput, setTagInput] = useState('');

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!contact) {
    return <div className="py-12 text-center text-gray-500">Contacto no encontrado.</div>;
  }

  const isAdminOrSupervisor = me?.role === 'admin' || me?.role === 'supervisor';

  const userOptions = [
    { value: '', label: 'Sin asignar' },
    ...users.map((u) => ({ value: u.id, label: u.full_name })),
  ];

  const handleStatusChange = (status: string) => {
    updateContact.mutate({ status: status as Contact['status'] }, {
      onSuccess: () => toast('Estado actualizado', 'success'),
      onError: () => toast('Error al actualizar', 'error'),
    });
  };

  const handleAssignChange = (userId: string) => {
    updateContact.mutate({ assigned_to: userId || undefined }, {
      onSuccess: () => toast('Asignación actualizada', 'success'),
      onError: () => toast('Error al actualizar', 'error'),
    });
  };

  const handleAddTag = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const tag = tagInput.trim();
    if (!tag || contact.tags.includes(tag)) { setTagInput(''); return; }
    updateContact.mutate(
      { tags: [...contact.tags, tag] },
      {
        onSuccess: () => { toast('Tag agregado', 'success'); setTagInput(''); },
        onError: () => toast('Error al agregar tag', 'error'),
      }
    );
  };

  const handleRemoveTag = (tag: string) => {
    updateContact.mutate(
      { tags: contact.tags.filter((t) => t !== tag) },
      {
        onSuccess: () => toast('Tag eliminado', 'success'),
        onError: () => toast('Error al eliminar tag', 'error'),
      }
    );
  };

  const handleDelete = () => {
    if (!confirm('¿Eliminar este contacto? Esta acción no se puede deshacer.')) return;
    deleteContact.mutate(id, {
      onSuccess: () => {
        toast('Contacto eliminado', 'success');
        router.push('/dashboard/contacts');
      },
      onError: () => toast('Error al eliminar', 'error'),
    });
  };

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ChevronRight className="h-4 w-4 rotate-180" />
        Volver a Contactos
      </button>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* ── Left column ── */}
        <div className="space-y-6 lg:col-span-3">
          {/* Info card */}
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">
                  {contact.first_name} {contact.last_name}
                </h1>
                <div className="mt-2">
                  <Badge variant={contact.status as any}>
                    {STATUS_LABEL[contact.status] ?? contact.status}
                  </Badge>
                </div>
              </div>
              <button
                onClick={() => setEditOpen(true)}
                className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
              >
                <Edit className="h-4 w-4" />
                Editar
              </button>
            </div>

            <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="font-medium text-gray-500">Email</dt>
                <dd className="mt-0.5 text-gray-900">{contact.email ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Teléfono</dt>
                <dd className="mt-0.5 text-gray-900">{contact.phone ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Empresa</dt>
                <dd className="mt-0.5 text-gray-900">{contact.company ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Cargo</dt>
                <dd className="mt-0.5 text-gray-900">{contact.position ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">País</dt>
                <dd className="mt-0.5 text-gray-900">{contact.country ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Creado</dt>
                <dd className="mt-0.5 text-gray-900">{relativeTime(contact.created_at)}</dd>
              </div>
            </dl>

            {/* Tags */}
            <div className="mt-5 border-t border-gray-100 pt-4">
              <p className="mb-2 text-xs font-medium text-gray-500">Tags</p>
              <div className="flex flex-wrap items-center gap-2">
                {contact.tags.map((tag) => (
                  <span
                    key={tag}
                    className="flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700"
                  >
                    {tag}
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="text-blue-400 hover:text-blue-700"
                      aria-label={`Eliminar tag ${tag}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleAddTag}
                  placeholder="Agregar tag…"
                  className="rounded-full border border-dashed border-gray-300 px-2.5 py-0.5 text-xs text-gray-500 placeholder-gray-300 focus:border-blue-400 focus:outline-none"
                />
              </div>
            </div>
          </Card>

          {/* Lead origin card */}
          {contact.lead_id && (
            <Card className="p-5">
              <div className="flex items-center gap-3">
                <Link2 className="h-5 w-5 text-indigo-500" />
                <div>
                  <p className="text-sm font-medium text-gray-700">Originado de Lead</p>
                  <Link
                    href={`/dashboard/leads/${contact.lead_id}`}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    Ver lead origen →
                  </Link>
                </div>
              </div>
            </Card>
          )}

          {/* Activity placeholder */}
          <Card className="p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-700">Actividades</h2>
            <div className="flex flex-col items-center py-8 text-center text-gray-400">
              <MessageSquare className="mb-3 h-10 w-10 opacity-30" />
              <p className="text-sm">Actividades próximamente</p>
              <p className="mt-1 text-xs">
                El historial de actividades estará disponible en la próxima versión.
              </p>
            </div>
          </Card>
        </div>

        {/* ── Right column ── */}
        <div className="space-y-4 lg:col-span-2">
          <Card className="p-5">
            <h2 className="mb-4 text-sm font-semibold text-gray-700">Acciones</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Estado</label>
                <Select
                  options={STATUS_OPTIONS}
                  value={contact.status}
                  onChange={handleStatusChange}
                  disabled={updateContact.isPending}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Asignar a</label>
                <Select
                  options={userOptions}
                  value={contact.assigned_to ?? ''}
                  onChange={handleAssignChange}
                  disabled={updateContact.isPending}
                />
              </div>

              {isAdminOrSupervisor && (
                <button
                  onClick={handleDelete}
                  disabled={deleteContact.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Eliminar
                </button>
              )}
            </div>
          </Card>
        </div>
      </div>

      <ContactFormModal
        isOpen={editOpen}
        onClose={() => setEditOpen(false)}
        contact={contact}
      />
    </div>
  );
}
