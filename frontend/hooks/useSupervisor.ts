import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Lead } from '@/lib/types';

export function useLeadsQueue() {
  return useQuery<Lead[]>({
    queryKey: ['supervisor', 'queue'],
    queryFn: async () => {
      const res = await api.get('/api/v1/supervisor/leads/queue');
      return res.data;
    },
    refetchInterval: 30_000,
  });
}

export function useAssignLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      leadId,
      assignedTo,
    }: {
      leadId: string;
      assignedTo: string;
    }) => {
      const res = await api.patch(`/api/v1/supervisor/leads/${leadId}/assign`, {
        assigned_to: assignedTo,
      });
      return res.data as Lead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supervisor', 'queue'] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
}
