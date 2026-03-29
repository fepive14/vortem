'use client';

import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { useAssignLead } from '@/hooks/useSupervisor';
import { useUsers } from '@/hooks/useUsers';

interface AssignLeadModalProps {
  isOpen: boolean;
  onClose: () => void;
  leadId: string;
  leadName: string;
}

export function AssignLeadModal({ isOpen, onClose, leadId, leadName }: AssignLeadModalProps) {
  const { toast } = useToast();
  const [assignedTo, setAssignedTo] = useState('');
  const { data: agents = [], isLoading: loadingUsers } = useUsers('agent');
  const assign = useAssignLead();

  const agentOptions = agents.map((u) => ({ value: u.id, label: u.full_name }));

  const handleSubmit = () => {
    if (!assignedTo) return;
    assign.mutate(
      { leadId, assignedTo },
      {
        onSuccess: () => {
          toast('Lead asignado exitosamente', 'success');
          setAssignedTo('');
          onClose();
        },
        onError: () => toast('Error al asignar el lead', 'error'),
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Asignar: ${leadName}`}>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Agente</label>
          {loadingUsers ? (
            <div className="mt-2 flex justify-center">
              <Spinner size="sm" />
            </div>
          ) : (
            <Select
              className="mt-1"
              options={agentOptions}
              value={assignedTo}
              onChange={setAssignedTo}
              placeholder="Seleccionar agente..."
            />
          )}
        </div>

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
            disabled={!assignedTo || assign.isPending}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {assign.isPending && <Spinner size="sm" className="text-white" />}
            Asignar
          </button>
        </div>
      </div>
    </Modal>
  );
}
