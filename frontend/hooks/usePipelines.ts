import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Pipeline, Stage } from '@/lib/types';

export function usePipelines() {
  return useQuery<Pipeline[]>({
    queryKey: ['pipelines'],
    queryFn: async () => {
      const res = await api.get('/api/v1/pipelines');
      return res.data;
    },
  });
}

export function useStages(pipelineId: string | undefined) {
  return useQuery<Stage[]>({
    queryKey: ['stages', pipelineId],
    queryFn: async () => {
      const res = await api.get('/api/v1/stages', {
        params: { pipeline_id: pipelineId },
      });
      return res.data;
    },
    enabled: !!pipelineId,
  });
}

export function useCreatePipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; description?: string; is_default?: boolean }) => {
      const res = await api.post('/api/v1/pipelines', data);
      return res.data as Pipeline;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pipelines'] }),
  });
}

export function useCreateStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      name: string;
      pipeline_id: string;
      order: number;
      color?: string;
      probability?: number;
      is_won?: boolean;
      is_lost?: boolean;
    }) => {
      const res = await api.post('/api/v1/stages', data);
      return res.data as Stage;
    },
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['stages', vars.pipeline_id] });
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
    },
  });
}
