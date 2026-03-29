'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useCreatePipeline } from '@/hooks/usePipelines';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/lib/types';

const schema = z.object({
  name: z.string().min(1, 'Requerido'),
  description: z.string().optional(),
  is_default: z.boolean().optional(),
});

type FormValues = z.infer<typeof schema>;

interface PipelineFormModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PipelineFormModal({ isOpen, onClose }: PipelineFormModalProps) {
  const { toast } = useToast();
  const createPipeline = useCreatePipeline();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', description: '', is_default: false },
  });

  useEffect(() => {
    if (isOpen) reset({ name: '', description: '', is_default: false });
  }, [isOpen, reset]);

  const serverError =
    createPipeline.error &&
    ((createPipeline.error as AxiosError<ApiError>).response?.data?.detail ??
      'Error al crear pipeline');

  const onSubmit = (values: FormValues) => {
    createPipeline.mutate(
      {
        name: values.name,
        description: values.description || undefined,
        is_default: values.is_default ?? false,
      },
      {
        onSuccess: () => {
          toast('Pipeline creado', 'success');
          onClose();
        },
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Nuevo Pipeline" className="max-w-md">
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
          <label className="block text-xs font-medium text-gray-700">Descripción</label>
          <textarea
            {...register('description')}
            rows={3}
            className="mt-1 block w-full resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_default"
            {...register('is_default')}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="is_default" className="text-sm text-gray-700">
            Pipeline por defecto
          </label>
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
            disabled={createPipeline.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {createPipeline.isPending && <Spinner size="sm" className="text-white" />}
            Crear
          </button>
        </div>
      </form>
    </Modal>
  );
}
