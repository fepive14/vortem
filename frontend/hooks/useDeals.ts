import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Deal } from '@/lib/types';

export function useDeals(params?: { pipeline_id?: string; skip?: number; limit?: number }) {
  return useQuery<Deal[]>({
    queryKey: ['deals', params],
    queryFn: async () => {
      const res = await api.get('/api/v1/deals', { params });
      return res.data;
    },
  });
}

export function useDeal(id: string) {
  return useQuery<Deal>({
    queryKey: ['deals', id],
    queryFn: async () => {
      const res = await api.get(`/api/v1/deals/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateDeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Deal>) => {
      const res = await api.post('/api/v1/deals', data);
      return res.data as Deal;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  });
}

export function useUpdateDeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Deal> }) => {
      const res = await api.patch(`/api/v1/deals/${id}`, data);
      return res.data as Deal;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['deals', id] });
    },
  });
}

export function useDeleteDeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/deals/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  });
}
