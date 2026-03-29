'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useCreateContact, useUpdateContact } from '@/hooks/useContacts';
import { useUsers } from '@/hooks/useUsers';
import type { Contact } from '@/lib/types';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/lib/types';

const schema = z.object({
  first_name: z.string().min(1, 'Requerido'),
  last_name: z.string().min(1, 'Requerido'),
  email: z.string().email('Email inválido').or(z.literal('')).optional(),
  phone: z.string().optional(),
  company: z.string().optional(),
  position: z.string().optional(),
  country: z.string().optional(),
  status: z.string().optional(),
  assigned_to: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const STATUS_OPTIONS = [
  { value: 'active', label: 'Activo' },
  { value: 'inactive', label: 'Inactivo' },
  { value: 'do_not_contact', label: 'No contactar' },
];

interface ContactFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  contact?: Contact;
}

export function ContactFormModal({ isOpen, onClose, contact }: ContactFormModalProps) {
  const { toast } = useToast();
  const isEdit = !!contact;
  const createContact = useCreateContact();
  const updateContact = useUpdateContact(contact?.id ?? '');
  const { data: users = [] } = useUsers();

  const userOptions = [
    { value: '', label: 'Sin asignar' },
    ...users.map((u) => ({ value: u.id, label: u.full_name })),
  ];

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
      company: '',
      position: '',
      country: '',
      status: 'active',
      assigned_to: '',
    },
  });

  useEffect(() => {
    if (contact) {
      reset({
        first_name: contact.first_name,
        last_name: contact.last_name,
        email: contact.email ?? '',
        phone: contact.phone ?? '',
        company: contact.company ?? '',
        position: contact.position ?? '',
        country: contact.country ?? '',
        status: contact.status,
        assigned_to: contact.assigned_to ?? '',
      });
    } else {
      reset({
        first_name: '', last_name: '', email: '', phone: '',
        company: '', position: '', country: '', status: 'active', assigned_to: '',
      });
    }
  }, [contact, reset, isOpen]);

  const mutation = isEdit ? updateContact : createContact;
  const serverError =
    mutation.error &&
    ((mutation.error as AxiosError<ApiError>).response?.data?.detail ?? 'Error al guardar');

  const onSubmit = (values: FormValues) => {
    const payload: Partial<Contact> = {
      first_name: values.first_name,
      last_name: values.last_name,
      email: values.email || undefined,
      phone: values.phone || undefined,
      company: values.company || undefined,
      position: values.position || undefined,
      country: values.country || undefined,
      assigned_to: values.assigned_to || undefined,
      ...(isEdit && { status: values.status as Contact['status'] }),
    };

    mutation.mutate(payload, {
      onSuccess: () => {
        toast(isEdit ? 'Contacto actualizado' : 'Contacto creado', 'success');
        onClose();
      },
    });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? 'Editar Contacto' : 'Nuevo Contacto'}
      className="max-w-xl"
    >
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
            <label className="block text-xs font-medium text-gray-700">Empresa</label>
            <input
              {...register('company')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Cargo</label>
            <input
              {...register('position')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {isEdit && (
            <div>
              <label className="block text-xs font-medium text-gray-700">Estado</label>
              <Select
                className="mt-1"
                options={STATUS_OPTIONS}
                value={watch('status') ?? 'active'}
                onChange={(v) => setValue('status', v)}
              />
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-700">Asignar a</label>
            <Select
              className="mt-1"
              options={userOptions}
              value={watch('assigned_to') ?? ''}
              onChange={(v) => setValue('assigned_to', v)}
            />
          </div>
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
