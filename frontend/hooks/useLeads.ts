import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Lead } from '@/lib/types';

export function useLeads(params?: { status?: string; skip?: number; limit?: number }) {
  return useQuery<Lead[]>({
    queryKey: ['leads', params],
    queryFn: async () => {
      const res = await api.get('/api/v1/leads', { params });
      return res.data;
    },
  });
}

export function useLead(id: string) {
  return useQuery<Lead>({
    queryKey: ['leads', id],
    queryFn: async () => {
      const res = await api.get(`/api/v1/leads/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Lead>) => {
      const res = await api.post('/api/v1/leads', data);
      return res.data as Lead;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['leads'] }),
  });
}

export function useUpdateLead(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Lead>) => {
      const res = await api.patch(`/api/v1/leads/${id}`, data);
      return res.data as Lead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['leads', id] });
    },
  });
}

export function useDeleteLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/leads/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['leads'] }),
  });
}

export function useConvertLead(leadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      assigned_to?: string;
      create_deal?: boolean;
      deal_name?: string;
      stage_id?: string;
      pipeline_id?: string;
      value?: number;
      currency?: string;
    }) => {
      const res = await api.post(`/api/v1/leads/${leadId}/convert`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
}
