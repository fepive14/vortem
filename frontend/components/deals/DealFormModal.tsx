'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useCreateDeal } from '@/hooks/useDeals';
import { usePipelines, useStages } from '@/hooks/usePipelines';
import { useContacts } from '@/hooks/useContacts';
import { useUsers } from '@/hooks/useUsers';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/lib/types';

const schema = z.object({
  name: z.string().min(1, 'Requerido'),
  contact_id: z.string().min(1, 'Requerido'),
  pipeline_id: z.string().min(1, 'Requerido'),
  stage_id: z.string().min(1, 'Requerido'),
  value: z.string().optional(),
  currency: z.string().optional(),
  assigned_to: z.string().optional(),
  expected_close_date: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const CURRENCIES = [
  { value: 'USD', label: 'USD' },
  { value: 'COP', label: 'COP' },
  { value: 'EUR', label: 'EUR' },
  { value: 'MXN', label: 'MXN' },
];

interface DealFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultPipelineId?: string;
  defaultStageId?: string;
  defaultContactId?: string;
}

export function DealFormModal({
  isOpen,
  onClose,
  defaultPipelineId,
  defaultStageId,
  defaultContactId,
}: DealFormModalProps) {
  const { toast } = useToast();
  const createDeal = useCreateDeal();
  const { data: pipelines = [] } = usePipelines();
  const { data: contacts = [] } = useContacts();
  const { data: users = [] } = useUsers();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      contact_id: defaultContactId ?? '',
      pipeline_id: defaultPipelineId ?? '',
      stage_id: defaultStageId ?? '',
      value: '',
      currency: 'USD',
      assigned_to: '',
      expected_close_date: '',
      notes: '',
    },
  });

  const selectedPipelineId = watch('pipeline_id');
  const { data: stages = [] } = useStages(selectedPipelineId || undefined);

  useEffect(() => {
    if (isOpen) {
      reset({
        name: '',
        contact_id: defaultContactId ?? '',
        pipeline_id: defaultPipelineId ?? '',
        stage_id: defaultStageId ?? '',
        value: '',
        currency: 'USD',
        assigned_to: '',
        expected_close_date: '',
        notes: '',
      });
    }
  }, [isOpen, defaultPipelineId, defaultStageId, defaultContactId, reset]);

  // Reset stage when pipeline changes (unless a default was provided)
  const prevPipelineRef = { current: defaultPipelineId };
  useEffect(() => {
    if (selectedPipelineId !== prevPipelineRef.current && !defaultStageId) {
      setValue('stage_id', '');
    }
    prevPipelineRef.current = selectedPipelineId;
  }, [selectedPipelineId, setValue, defaultStageId]); // eslint-disable-line react-hooks/exhaustive-deps

  const contactOptions = contacts.map((c) => ({
    value: c.id,
    label: `${c.first_name} ${c.last_name}${c.company ? ` — ${c.company}` : ''}`,
  }));
  const pipelineOptions = pipelines.map((p) => ({ value: p.id, label: p.name }));
  const stageOptions = [...stages]
    .sort((a, b) => a.order - b.order)
    .map((s) => ({ value: s.id, label: s.name }));
  const userOptions = [
    { value: '', label: 'Sin asignar' },
    ...users.map((u) => ({ value: u.id, label: u.full_name })),
  ];

  const serverError =
    createDeal.error &&
    ((createDeal.error as AxiosError<ApiError>).response?.data?.detail ?? 'Error al guardar');

  const onSubmit = (values: FormValues) => {
    createDeal.mutate(
      {
        name: values.name,
        contact_id: values.contact_id,
        pipeline_id: values.pipeline_id,
        stage_id: values.stage_id,
        value: values.value ? Number(values.value) : null,
        currency: values.currency ?? 'USD',
        assigned_to: values.assigned_to || undefined,
        expected_close_date: values.expected_close_date || null,
        notes: values.notes || null,
      },
      {
        onSuccess: () => {
          toast('Deal creado', 'success');
          onClose();
        },
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Nuevo Deal" className="max-w-xl">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-700">Nombre *</label>
          <input
            {...register('name')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700">Contacto *</label>
          <Select
            className="mt-1"
            options={contactOptions}
            value={watch('contact_id')}
            onChange={(v) => setValue('contact_id', v)}
            placeholder="Seleccionar contacto..."
          />
          {errors.contact_id && (
            <p className="mt-1 text-xs text-red-600">{errors.contact_id.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Pipeline *</label>
            <Select
              className="mt-1"
              options={pipelineOptions}
              value={watch('pipeline_id')}
              onChange={(v) => setValue('pipeline_id', v)}
              placeholder="Seleccionar pipeline..."
            />
            {errors.pipeline_id && (
              <p className="mt-1 text-xs text-red-600">{errors.pipeline_id.message}</p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Etapa *</label>
            <Select
              className="mt-1"
              options={stageOptions}
              value={watch('stage_id')}
              onChange={(v) => setValue('stage_id', v)}
              placeholder="Seleccionar etapa..."
              disabled={!selectedPipelineId}
            />
            {errors.stage_id && (
              <p className="mt-1 text-xs text-red-600">{errors.stage_id.message}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Valor</label>
            <input
              type="number"
              {...register('value')}
              placeholder="0"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Moneda</label>
            <Select
              className="mt-1"
              options={CURRENCIES}
              value={watch('currency') ?? 'USD'}
              onChange={(v) => setValue('currency', v)}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Asignar a</label>
            <Select
              className="mt-1"
              options={userOptions}
              value={watch('assigned_to') ?? ''}
              onChange={(v) => setValue('assigned_to', v)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">
              Fecha cierre estimada
            </label>
            <input
              type="date"
              {...register('expected_close_date')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700">Notas</label>
          <textarea
            {...register('notes')}
            rows={3}
            className="mt-1 block w-full resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {serverError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{serverError}</p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={createDeal.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {createDeal.isPending && <Spinner size="sm" className="text-white" />}
            Crear
          </button>
        </div>
      </form>
    </Modal>
  );
}
