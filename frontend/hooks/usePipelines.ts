import { useQuery } from '@tanstack/react-query';
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
