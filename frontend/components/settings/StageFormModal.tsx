'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useCreateStage } from '@/hooks/usePipelines';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/lib/types';

const schema = z.object({
  name: z.string().min(1, 'Requerido'),
  order: z.string().min(1, 'Requerido'),
  color: z.string().optional(),
  probability: z.string().optional(),
  is_won: z.boolean().optional(),
  is_lost: z.boolean().optional(),
});

type FormValues = z.infer<typeof schema>;

interface StageFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  pipelineId: string;
  nextOrder: number;
}

export function StageFormModal({ isOpen, onClose, pipelineId, nextOrder }: StageFormModalProps) {
  const { toast } = useToast();
  const createStage = useCreateStage();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      order: String(nextOrder),
      color: '#6366f1',
      probability: '0',
      is_won: false,
      is_lost: false,
    },
  });

  useEffect(() => {
    if (isOpen) {
      reset({
        name: '',
        order: String(nextOrder),
        color: '#6366f1',
        probability: '0',
        is_won: false,
        is_lost: false,
      });
    }
  }, [isOpen, nextOrder, reset]);

  const serverError =
    createStage.error &&
    ((createStage.error as AxiosError<ApiError>).response?.data?.detail ?? 'Error al crear etapa');

  const onSubmit = (values: FormValues) => {
    createStage.mutate(
      {
        name: values.name,
        pipeline_id: pipelineId,
        order: Number(values.order),
        color: values.color || undefined,
        probability: values.probability ? Number(values.probability) : 0,
        is_won: values.is_won ?? false,
        is_lost: values.is_lost ?? false,
      },
      {
        onSuccess: () => {
          toast('Etapa creada', 'success');
          onClose();
        },
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Nueva Etapa" className="max-w-md">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-700">Nombre *</label>
          <input
            {...register('name')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Orden *</label>
            <input
              type="number"
              {...register('order')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {errors.order && (
              <p className="mt-1 text-xs text-red-600">{errors.order.message}</p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Probabilidad (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              {...register('probability')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700">Color</label>
          <input
            type="color"
            {...register('color')}
            className="mt-1 h-9 w-full cursor-pointer rounded-md border border-gray-300 p-1"
          />
        </div>

        <div className="flex gap-6">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_won"
              {...register('is_won')}
              className="h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <label htmlFor="is_won" className="text-sm text-gray-700">
              Etapa ganada
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_lost"
              {...register('is_lost')}
              className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
            />
            <label htmlFor="is_lost" className="text-sm text-gray-700">
              Etapa perdida
            </label>
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
            disabled={createStage.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {createStage.isPending && <Spinner size="sm" className="text-white" />}
            Crear
          </button>
        </div>
      </form>
    </Modal>
  );
}
