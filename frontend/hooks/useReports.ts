import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface FunnelReport {
  leads_total: number;
  leads_qualified: number;
  leads_converted: number;
  contacts_total: number;
  deals_total: number;
  deals_won: number;
  conversion_rate_lead_to_contact: number;
  conversion_rate_contact_to_deal: number;
}

export interface AgentPerformance {
  user_id: string;
  full_name: string;
  leads_assigned: number;
  leads_converted: number;
  deals_created: number;
  deals_won: number;
  activities_logged: number;
  conversion_rate: number;
}

export interface CampaignActivity {
  campaign_id: string;
  leads_total: number;
  leads_qualified: number;
  leads_converted: number;
  calls_completed: number;
  conversion_rate: number;
}

export function useFunnel(days: number = 30) {
  return useQuery<FunnelReport>({
    queryKey: ['reports', 'funnel', days],
    queryFn: async () => {
      const res = await api.get('/api/v1/reports/funnel', { params: { days } });
      return res.data;
    },
  });
}

export function useAgentPerformance(days: number = 30) {
  return useQuery<AgentPerformance[]>({
    queryKey: ['reports', 'agent-performance', days],
    queryFn: async () => {
      const res = await api.get('/api/v1/reports/agent-performance', { params: { days } });
      return res.data;
    },
  });
}

export function useActivityByCampaign(days: number = 30) {
  return useQuery<CampaignActivity[]>({
    queryKey: ['reports', 'activity-by-campaign', days],
    queryFn: async () => {
      const res = await api.get('/api/v1/reports/activity-by-campaign', { params: { days } });
      return res.data;
    },
  });
}
