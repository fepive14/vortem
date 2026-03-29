'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useConvertLead } from '@/hooks/useLeads';
import { useUsers } from '@/hooks/useUsers';
import { usePipelines, useStages } from '@/hooks/usePipelines';

interface ConvertLeadModalProps {
  isOpen: boolean;
  onClose: () => void;
  leadId: string;
  leadName: string;
}

export function ConvertLeadModal({
  isOpen,
  onClose,
  leadId,
  leadName,
}: ConvertLeadModalProps) {
  const router = useRouter();
  const { toast } = useToast();

  const [assignedTo, setAssignedTo] = useState('');
  const [createDeal, setCreateDeal] = useState(false);
  const [dealName, setDealName] = useState('');
  const [pipelineId, setPipelineId] = useState('');
  const [stageId, setStageId] = useState('');

  const { data: users = [], isLoading: loadingUsers } = useUsers();
  const { data: pipelines = [], isLoading: loadingPipelines } = usePipelines();
  const { data: stages = [], isLoading: loadingStages } = useStages(pipelineId || undefined);
  const convert = useConvertLead(leadId);

  const userOptions = users.map((u) => ({ value: u.id, label: u.full_name }));
  const pipelineOptions = pipelines.map((p) => ({ value: p.id, label: p.name }));
  const stageOptions = stages.map((s) => ({ value: s.id, label: s.name }));

  const handlePipelineChange = (id: string) => {
    setPipelineId(id);
    setStageId('');
  };

  const handleSubmit = () => {
    convert.mutate(
      {
        assigned_to: assignedTo || undefined,
        create_deal: createDeal,
        deal_name: createDeal ? dealName || undefined : undefined,
        pipeline_id: createDeal ? pipelineId || undefined : undefined,
        stage_id: createDeal ? stageId || undefined : undefined,
      },
      {
        onSuccess: (data) => {
          toast('Lead convertido exitosamente', 'success');
          onClose();
          router.push(`/dashboard/contacts/${data.contact.id}`);
        },
        onError: () => toast('Error al convertir el lead', 'error'),
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Convertir: ${leadName}`} className="max-w-xl">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Asignar a (opcional)
          </label>
          <Select
            className="mt-1"
            options={userOptions}
            value={assignedTo}
            onChange={setAssignedTo}
            placeholder="Sin asignar"
            disabled={loadingUsers}
          />
        </div>

        <div className="flex items-center gap-3">
          <input
            id="create_deal"
            type="checkbox"
            checked={createDeal}
            onChange={(e) => setCreateDeal(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="create_deal" className="text-sm font-medium text-gray-700">
            Crear deal al convertir
          </label>
        </div>

        {createDeal && (
          <div className="space-y-3 rounded-lg border border-gray-200 p-4">
            <div>
              <label className="block text-xs font-medium text-gray-700">Nombre del deal</label>
              <input
                value={dealName}
                onChange={(e) => setDealName(e.target.value)}
                placeholder="Deal de..."
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700">Pipeline</label>
              <Select
                className="mt-1"
                options={pipelineOptions}
                value={pipelineId}
                onChange={handlePipelineChange}
                placeholder="Seleccionar pipeline..."
                disabled={loadingPipelines}
              />
            </div>
            {pipelineId && (
              <div>
                <label className="block text-xs font-medium text-gray-700">Etapa</label>
                <Select
                  className="mt-1"
                  options={stageOptions}
                  value={stageId}
                  onChange={setStageId}
                  placeholder="Seleccionar etapa..."
                  disabled={loadingStages}
                />
              </div>
            )}
          </div>
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
            onClick={handleSubmit}
            disabled={convert.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {convert.isPending && <Spinner size="sm" className="text-white" />}
            Convertir
          </button>
        </div>
      </div>
    </Modal>
  );
}
