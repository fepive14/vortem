'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useUpdateDeal, useDeleteDeal } from '@/hooks/useDeals';
import { useUsers } from '@/hooks/useUsers';
import { useStages } from '@/hooks/usePipelines';
import { useMe } from '@/hooks/useAuth';
import type { Deal } from '@/lib/types';

const CURRENCIES = [
  { value: 'USD', label: 'USD' },
  { value: 'COP', label: 'COP' },
  { value: 'EUR', label: 'EUR' },
  { value: 'MXN', label: 'MXN' },
];

interface DealDrawerProps {
  deal: Deal | null;
  onClose: () => void;
}

export function DealDrawer({ deal, onClose }: DealDrawerProps) {
  const { toast } = useToast();
  const { data: me } = useMe();
  const updateDeal = useUpdateDeal();
  const deleteDeal = useDeleteDeal();
  const { data: users = [] } = useUsers();
  const { data: stages = [] } = useStages(deal?.pipeline_id);

  const [nameEditing, setNameEditing] = useState(false);
  const [nameValue, setNameValue] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const notesTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isAdminOrSupervisor = me?.role === 'admin' || me?.role === 'supervisor';

  useEffect(() => {
    if (deal) {
      setNameValue(deal.name);
      setNotes(deal.notes ?? '');
      setNameEditing(false);
    }
  }, [deal]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const patch = useCallback(
    (data: Partial<Deal>) => {
      if (!deal) return;
      setSaving(true);
      updateDeal.mutate(
        { id: deal.id, data },
        {
          onSuccess: () => setSaving(false),
          onError: () => {
            toast('Error al guardar', 'error');
            setSaving(false);
          },
        }
      );
    },
    [deal, updateDeal, toast]
  );

  const handleNotesChange = (value: string) => {
    setNotes(value);
    if (notesTimerRef.current) clearTimeout(notesTimerRef.current);
    notesTimerRef.current = setTimeout(() => patch({ notes: value }), 800);
  };

  const handleNameSave = () => {
    setNameEditing(false);
    if (nameValue.trim() && nameValue !== deal?.name) {
      patch({ name: nameValue.trim() });
    }
  };

  const handleDelete = () => {
    if (!deal) return;
    if (!confirm('¿Eliminar este deal? Esta acción no se puede deshacer.')) return;
    deleteDeal.mutate(deal.id, {
      onSuccess: () => {
        toast('Deal eliminado', 'success');
        onClose();
      },
      onError: () => toast('Error al eliminar', 'error'),
    });
  };

  const sortedStages = [...stages].sort((a, b) => a.order - b.order);
  const currentStageIdx = sortedStages.findIndex((s) => s.id === deal?.stage_id);

  const userOptions = [
    { value: '', label: 'Sin asignar' },
    ...users.map((u) => ({ value: u.id, label: u.full_name })),
  ];

  if (!deal) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[480px] flex-col bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <div className="mr-3 min-w-0 flex-1">
            {nameEditing ? (
              <input
                autoFocus
                value={nameValue}
                onChange={(e) => setNameValue(e.target.value)}
                onBlur={handleNameSave}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleNameSave();
                }}
                className="w-full rounded border border-blue-400 px-2 py-1 text-base font-semibold text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            ) : (
              <h2
                onClick={() => setNameEditing(true)}
                className="cursor-text truncate text-base font-semibold text-gray-900 hover:text-blue-600"
                title="Clic para editar"
              >
                {deal.name}
              </h2>
            )}
          </div>
          <div className="flex items-center gap-2">
            {saving && <Spinner size="sm" className="text-gray-400" />}
            {!saving && updateDeal.isPending && (
              <span className="text-xs text-gray-400">Guardando...</span>
            )}
            <button
              onClick={onClose}
              className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              aria-label="Cerrar"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Scrollable body — keyed by deal.id so uncontrolled inputs reset */}
        <div key={deal.id} className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          {/* Stage progress */}
          {sortedStages.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium text-gray-500">Etapa</p>
              <div className="flex items-end gap-1">
                {sortedStages.map((stage, idx) => (
                  <div key={stage.id} className="flex flex-1 flex-col items-center gap-1">
                    <div
                      className={`h-1.5 w-full rounded-full ${
                        idx <= currentStageIdx
                          ? stage.color
                            ? ''
                            : 'bg-blue-500'
                          : 'bg-gray-200'
                      }`}
                      style={
                        idx <= currentStageIdx && stage.color
                          ? { backgroundColor: stage.color }
                          : undefined
                      }
                    />
                    {idx === currentStageIdx && (
                      <span className="max-w-full truncate text-[10px] font-medium text-gray-600">
                        {stage.name}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  disabled={currentStageIdx <= 0 || updateDeal.isPending}
                  onClick={() => patch({ stage_id: sortedStages[currentStageIdx - 1].id })}
                  className="flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                >
                  <ChevronLeft className="h-3 w-3" />
                  Anterior
                </button>
                <button
                  disabled={
                    currentStageIdx >= sortedStages.length - 1 || updateDeal.isPending
                  }
                  onClick={() => patch({ stage_id: sortedStages[currentStageIdx + 1].id })}
                  className="flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                >
                  Siguiente
                  <ChevronRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          )}

          <hr className="border-gray-100" />

          {/* Contact */}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500">Contacto</p>
            <Link
              href={`/dashboard/contacts/${deal.contact_id}`}
              className="text-sm text-blue-600 hover:underline"
            >
              Ver contacto →
            </Link>
          </div>

          {/* Value + currency */}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500">Valor</p>
            <div className="flex gap-2">
              <input
                type="number"
                defaultValue={deal.value ?? ''}
                onBlur={(e) =>
                  patch({ value: e.target.value !== '' ? Number(e.target.value) : null })
                }
                placeholder="0"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <Select
                options={CURRENCIES}
                value={deal.currency}
                onChange={(v) => patch({ currency: v })}
                className="w-28"
              />
            </div>
          </div>

          {/* Assigned to */}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500">Asignar a</p>
            <Select
              options={userOptions}
              value={deal.assigned_to ?? ''}
              onChange={(v) => patch({ assigned_to: v || undefined })}
            />
          </div>

          {/* Expected close date */}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500">Fecha cierre estimada</p>
            <input
              type="date"
              defaultValue={deal.expected_close_date?.slice(0, 10) ?? ''}
              onBlur={(e) => patch({ expected_close_date: e.target.value || null })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Notes */}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500">Notas</p>
            <textarea
              value={notes}
              onChange={(e) => handleNotesChange(e.target.value)}
              rows={4}
              className="w-full resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Delete */}
          {isAdminOrSupervisor && (
            <>
              <hr className="border-gray-100" />
              <button
                onClick={handleDelete}
                disabled={deleteDeal.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" />
                Eliminar Deal
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
