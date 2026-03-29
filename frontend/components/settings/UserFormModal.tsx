'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useCreateUser } from '@/hooks/useUsers';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/lib/types';

const schema = z.object({
  full_name: z.string().min(1, 'Requerido'),
  email: z.string().email('Email inválido'),
  password: z.string().min(8, 'Mínimo 8 caracteres'),
  role: z.string().min(1, 'Requerido'),
  timezone: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const ROLE_OPTIONS = [
  { value: 'agent', label: 'Agente' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'admin', label: 'Admin' },
  { value: 'viewer', label: 'Viewer' },
];

interface UserFormModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UserFormModal({ isOpen, onClose }: UserFormModalProps) {
  const { toast } = useToast();
  const createUser = useCreateUser();

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
      full_name: '',
      email: '',
      password: '',
      role: 'agent',
      timezone: 'America/Bogota',
    },
  });

  useEffect(() => {
    if (isOpen) {
      reset({
        full_name: '',
        email: '',
        password: '',
        role: 'agent',
        timezone: 'America/Bogota',
      });
    }
  }, [isOpen, reset]);

  const serverError =
    createUser.error &&
    ((createUser.error as AxiosError<ApiError>).response?.data?.detail ?? 'Error al crear usuario');

  const onSubmit = (values: FormValues) => {
    createUser.mutate(
      {
        full_name: values.full_name,
        email: values.email,
        password: values.password,
        role: values.role,
        timezone: values.timezone || 'America/Bogota',
      },
      {
        onSuccess: () => {
          toast('Usuario creado', 'success');
          onClose();
        },
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Invitar Usuario" className="max-w-md">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-700">Nombre completo *</label>
          <input
            {...register('full_name')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.full_name && (
            <p className="mt-1 text-xs text-red-600">{errors.full_name.message}</p>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700">Email *</label>
          <input
            type="email"
            {...register('email')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.email && (
            <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700">Contraseña *</label>
          <input
            type="password"
            {...register('password')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.password && (
            <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Rol *</label>
            <Select
              className="mt-1"
              options={ROLE_OPTIONS}
              value={watch('role')}
              onChange={(v) => setValue('role', v)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Zona horaria</label>
            <input
              {...register('timezone')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
            disabled={createUser.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {createUser.isPending && <Spinner size="sm" className="text-white" />}
            Crear
          </button>
        </div>
      </form>
    </Modal>
  );
}
