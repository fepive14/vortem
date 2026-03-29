'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { useMe } from '@/hooks/useAuth';
import { useFunnel, useAgentPerformance, useActivityByCampaign } from '@/hooks/useReports';

const DAY_OPTIONS = [7, 30, 90, 365];

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
        </td>
      ))}
    </tr>
  );
}

export default function ReportsPage() {
  const router = useRouter();
  const { data: me, isLoading: meLoading } = useMe();
  const [days, setDays] = useState(30);

  const { data: funnel, isLoading: funnelLoading } = useFunnel(days);
  const { data: agentPerf = [], isLoading: agentLoading } = useAgentPerformance(days);
  const { data: campaigns = [], isLoading: campaignLoading } = useActivityByCampaign(days);

  useEffect(() => {
    if (!meLoading && me && me.role !== 'admin' && me.role !== 'supervisor') {
      router.replace('/dashboard');
    }
  }, [me, meLoading, router]);

  if (meLoading || !me) return null;
  if (me.role !== 'admin' && me.role !== 'supervisor') return null;

  const sortedAgents = [...agentPerf].sort(
    (a, b) => (b.conversion_rate ?? 0) - (a.conversion_rate ?? 0)
  );

  const funnelCards = [
    { label: 'Total Leads', value: funnel?.leads_total ?? 0 },
    { label: 'Calificados', value: funnel?.leads_qualified ?? 0 },
    { label: 'Convertidos', value: funnel?.leads_converted ?? 0 },
    { label: 'Contactos', value: funnel?.contacts_total ?? 0 },
    { label: 'Deals', value: funnel?.deals_total ?? 0 },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Reportes</h1>
        <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white p-1">
          {DAY_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                days === d
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Section 1 — Funnel */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Embudo de conversión</h2>
        {funnelLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <Card key={i} className="p-5">
                <div className="h-8 w-16 animate-pulse rounded bg-gray-200" />
                <div className="mt-2 h-4 w-20 animate-pulse rounded bg-gray-200" />
              </Card>
            ))}
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              {funnelCards.map((card, idx) => (
                <div key={card.label} className="flex items-center gap-2">
                  <Card className="p-5 text-center min-w-[110px]">
                    <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                    <p className="mt-1 text-xs text-gray-500">{card.label}</p>
                  </Card>
                  {idx < funnelCards.length - 1 && (
                    <ArrowRight className="h-4 w-4 shrink-0 text-gray-300" />
                  )}
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-3">
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                Tasa Lead→Contacto:{' '}
                {((funnel?.conversion_rate_lead_to_contact ?? 0) * 100).toFixed(1)}%
              </span>
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                Tasa Contacto→Deal:{' '}
                {((funnel?.conversion_rate_contact_to_deal ?? 0) * 100).toFixed(1)}%
              </span>
            </div>
          </>
        )}
      </div>

      {/* Section 2 — Agent Performance */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Rendimiento por Agente</h2>
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {[
                    'Agente',
                    'Leads Asignados',
                    'Leads Convertidos',
                    'Deals Creados',
                    'Deals Ganados',
                    'Actividades',
                    'Tasa Conversión',
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {agentLoading ? (
                  Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
                ) : sortedAgents.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-4 py-8 text-center text-sm text-gray-400"
                    >
                      Sin datos para el período seleccionado
                    </td>
                  </tr>
                ) : (
                  sortedAgents.map((agent) => (
                    <tr key={agent.user_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {agent.full_name}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{agent.leads_assigned}</td>
                      <td className="px-4 py-3 text-gray-600">{agent.leads_converted}</td>
                      <td className="px-4 py-3 text-gray-600">{agent.deals_created}</td>
                      <td className="px-4 py-3 text-gray-600">{agent.deals_won}</td>
                      <td className="px-4 py-3 text-gray-600">{agent.activities_logged}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                          {((agent.conversion_rate ?? 0) * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Section 3 — Activity by Campaign */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Actividad por Campaña</h2>
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50">
                <tr>
                  {[
                    'Campaign ID',
                    'Leads',
                    'Calificados',
                    'Convertidos',
                    'Llamadas',
                    'Tasa',
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {campaignLoading ? (
                  Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
                ) : campaigns.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-sm text-gray-400"
                    >
                      No hay campañas con actividad en este período
                    </td>
                  </tr>
                ) : (
                  campaigns.map((c) => (
                    <tr key={c.campaign_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">
                        {c.campaign_id.slice(0, 8)}…
                      </td>
                      <td className="px-4 py-3 text-gray-600">{c.leads_total}</td>
                      <td className="px-4 py-3 text-gray-600">{c.leads_qualified}</td>
                      <td className="px-4 py-3 text-gray-600">{c.leads_converted}</td>
                      <td className="px-4 py-3 text-gray-600">{c.calls_completed}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                          {((c.conversion_rate ?? 0) * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
