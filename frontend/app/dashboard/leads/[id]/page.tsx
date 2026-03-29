'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ChevronDown, ChevronRight, Edit, Trash2, MessageSquare } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { LeadFormModal } from '@/components/leads/LeadFormModal';
import { AssignLeadModal } from '@/components/leads/AssignLeadModal';
import { ConvertLeadModal } from '@/components/leads/ConvertLeadModal';
import { useLead, useUpdateLead, useDeleteLead } from '@/hooks/useLeads';
import { useMe } from '@/hooks/useAuth';
import { relativeTime } from '@/lib/utils';

const STATUS_OPTIONS = [
  { value: 'new', label: 'Nuevo' },
  { value: 'contacted', label: 'Contactado' },
  { value: 'qualified', label: 'Calificado' },
  { value: 'discarded', label: 'Descartado' },
];

const STATUS_LABEL: Record<string, string> = {
  new: 'Nuevo',
  contacted: 'Contactado',
  qualified: 'Calificado',
  converted: 'Convertido',
  discarded: 'Descartado',
};

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const { data: me } = useMe();
  const { data: lead, isLoading } = useLead(id);
  const updateLead = useUpdateLead(id);
  const deleteLead = useDeleteLead();

  const [editOpen, setEditOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [convertOpen, setConvertOpen] = useState(false);
  const [voiceExpanded, setVoiceExpanded] = useState(false);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="py-12 text-center text-gray-500">Lead no encontrado.</div>
    );
  }

  const isAdmin = me?.role === 'admin' || me?.role === 'supervisor';
  const canEdit = me?.role !== 'viewer';
  const hasVoicehireData =
    lead.voicehire_data && Object.keys(lead.voicehire_data).length > 0;

  const handleStatusChange = (status: string) => {
    updateLead.mutate({ status: status as Lead['status'] }, {
      onSuccess: () => toast('Estado actualizado', 'success'),
      onError: () => toast('Error al actualizar', 'error'),
    });
  };

  const handleDelete = () => {
    if (!confirm('¿Eliminar este lead?')) return;
    deleteLead.mutate(id, {
      onSuccess: () => {
        toast('Lead eliminado', 'success');
        router.push('/dashboard/leads');
      },
      onError: () => toast('Error al eliminar', 'error'),
    });
  };

  return (
    <div className="space-y-6">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ChevronRight className="h-4 w-4 rotate-180" />
        Volver a Leads
      </button>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* ── Left column (3/5) ── */}
        <div className="space-y-6 lg:col-span-3">
          {/* Lead info card */}
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">
                  {lead.first_name} {lead.last_name}
                </h1>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge variant={lead.status as any}>
                    {STATUS_LABEL[lead.status] ?? lead.status}
                  </Badge>
                  <Badge variant="normal">{lead.source}</Badge>
                </div>
              </div>
              {canEdit && (
                <button
                  onClick={() => setEditOpen(true)}
                  className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
                >
                  <Edit className="h-4 w-4" />
                  Editar
                </button>
              )}
            </div>

            <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="font-medium text-gray-500">Email</dt>
                <dd className="mt-0.5 text-gray-900">{lead.email ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Teléfono</dt>
                <dd className="mt-0.5 text-gray-900">{lead.phone ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">País</dt>
                <dd className="mt-0.5 text-gray-900">{lead.country ?? '—'}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Creado</dt>
                <dd className="mt-0.5 text-gray-900">{relativeTime(lead.created_at)}</dd>
              </div>
            </dl>

            {/* VoiceHire data */}
            {hasVoicehireData && (
              <div className="mt-5 border-t border-gray-100 pt-4">
                <button
                  onClick={() => setVoiceExpanded((v) => !v)}
                  className="flex items-center gap-2 text-sm font-medium text-gray-700"
                >
                  {voiceExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  Datos VoiceHire
                </button>
                {voiceExpanded && (
                  <pre className="mt-3 max-h-48 overflow-auto rounded-md bg-gray-50 p-3 text-xs text-gray-700">
                    {JSON.stringify(lead.voicehire_data, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </Card>

          {/* Activity timeline placeholder */}
          <Card className="p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-700">Actividades</h2>
            <div className="flex flex-col items-center py-8 text-center text-gray-400">
              <MessageSquare className="mb-3 h-10 w-10 opacity-30" />
              <p className="text-sm">Actividades próximamente</p>
              <p className="mt-1 text-xs">El historial de actividades estará disponible en la próxima versión.</p>
            </div>
          </Card>
        </div>

        {/* ── Right column (2/5) ── */}
        <div className="space-y-4 lg:col-span-2">
          <Card className="p-5">
            <h2 className="mb-4 text-sm font-semibold text-gray-700">Acciones</h2>

            <div className="space-y-3">
              {lead.status !== 'converted' && canEdit && (
                <button
                  onClick={() => setConvertOpen(true)}
                  className="w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
                >
                  Convertir Lead
                </button>
              )}

              {lead.status === 'qualified' && !lead.assigned_to && isAdmin && (
                <button
                  onClick={() => setAssignOpen(true)}
                  className="w-full rounded-md border border-blue-600 px-4 py-2.5 text-sm font-semibold text-blue-600 hover:bg-blue-50"
                >
                  Asignar Lead
                </button>
              )}

              {lead.status !== 'converted' && canEdit && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Cambiar estado
                  </label>
                  <Select
                    options={STATUS_OPTIONS}
                    value={lead.status}
                    onChange={handleStatusChange}
                    disabled={updateLead.isPending}
                  />
                </div>
              )}

              {isAdmin && (
                <button
                  onClick={handleDelete}
                  disabled={deleteLead.isPending}
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

      {/* Modals */}
      <LeadFormModal isOpen={editOpen} onClose={() => setEditOpen(false)} lead={lead} />
      <AssignLeadModal
        isOpen={assignOpen}
        onClose={() => setAssignOpen(false)}
        leadId={lead.id}
        leadName={`${lead.first_name} ${lead.last_name}`}
      />
      <ConvertLeadModal
        isOpen={convertOpen}
        onClose={() => setConvertOpen(false)}
        leadId={lead.id}
        leadName={`${lead.first_name} ${lead.last_name}`}
      />
    </div>
  );
}

// Needed for the status type cast
type Lead = import('@/lib/types').Lead;
