'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useCreateLead, useUpdateLead } from '@/hooks/useLeads';
import type { Lead } from '@/lib/types';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/lib/types';

const schema = z.object({
  first_name: z.string().min(1, 'Requerido'),
  last_name: z.string().min(1, 'Requerido'),
  email: z.string().email('Email inválido').or(z.literal('')).optional(),
  phone: z.string().optional(),
  country: z.string().optional(),
  source: z.string(),
  status: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const SOURCE_OPTIONS = [
  { value: 'manual', label: 'Manual' },
  { value: 'csv_import', label: 'CSV Import' },
  { value: 'api', label: 'API' },
  { value: 'voicehire', label: 'VoiceHire' },
];

const STATUS_OPTIONS = [
  { value: 'new', label: 'Nuevo' },
  { value: 'contacted', label: 'Contactado' },
  { value: 'qualified', label: 'Calificado' },
  { value: 'discarded', label: 'Descartado' },
];

interface LeadFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  lead?: Lead;
}

export function LeadFormModal({ isOpen, onClose, lead }: LeadFormModalProps) {
  const { toast } = useToast();
  const isEdit = !!lead;
  const createLead = useCreateLead();
  const updateLead = useUpdateLead(lead?.id ?? '');

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      country: '',
      source: 'manual',
      status: 'new',
    },
  });

  useEffect(() => {
    if (lead) {
      reset({
        first_name: lead.first_name,
        last_name: lead.last_name,
        email: lead.email ?? '',
        phone: lead.phone ?? '',
        country: lead.country ?? '',
        source: lead.source,
        status: lead.status,
      });
    } else {
      reset({ first_name: '', last_name: '', email: '', phone: '', country: '', source: 'manual', status: 'new' });
    }
  }, [lead, reset, isOpen]);

  const mutation = isEdit ? updateLead : createLead;
  const serverError =
    mutation.error &&
    ((mutation.error as AxiosError<ApiError>).response?.data?.detail ?? 'Error al guardar');

  const onSubmit = (values: FormValues) => {
    const payload = {
      first_name: values.first_name,
      last_name: values.last_name,
      email: values.email || undefined,
      phone: values.phone || undefined,
      country: values.country || undefined,
      source: values.source as Lead['source'],
      ...(isEdit && { status: values.status as Lead['status'] }),
    };

    mutation.mutate(payload as Partial<Lead>, {
      onSuccess: () => {
        toast(isEdit ? 'Lead actualizado' : 'Lead creado', 'success');
        onClose();
      },
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={isEdit ? 'Editar Lead' : 'Nuevo Lead'}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Nombre *</label>
            <input
              {...register('first_name')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {errors.first_name && (
              <p className="mt-1 text-xs text-red-600">{errors.first_name.message}</p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Apellido *</label>
            <input
              {...register('last_name')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {errors.last_name && (
              <p className="mt-1 text-xs text-red-600">{errors.last_name.message}</p>
            )}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700">Email</label>
          <input
            type="email"
            {...register('email')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.email && (
            <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Teléfono</label>
            <input
              {...register('phone')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">País</label>
            <input
              {...register('country')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Fuente</label>
            <Select
              className="mt-1"
              options={SOURCE_OPTIONS}
              value={watch('source')}
              onChange={(v) => setValue('source', v)}
            />
          </div>
          {isEdit && (
            <div>
              <label className="block text-xs font-medium text-gray-700">Estado</label>
              <Select
                className="mt-1"
                options={STATUS_OPTIONS}
                value={watch('status') ?? 'new'}
                onChange={(v) => setValue('status', v)}
              />
            </div>
          )}
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
            disabled={mutation.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {mutation.isPending && <Spinner size="sm" className="text-white" />}
            {isEdit ? 'Guardar' : 'Crear'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
