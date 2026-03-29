'use client';

import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import Link from 'next/link';
import { useQueryClient } from '@tanstack/react-query';
import { Select } from '@/components/ui/Select';
import { DealCard } from '@/components/deals/DealCard';
import { DealDrawer } from '@/components/deals/DealDrawer';
import { DealFormModal } from '@/components/deals/DealFormModal';
import { useDeals, useUpdateDeal } from '@/hooks/useDeals';
import { usePipelines, useStages } from '@/hooks/usePipelines';
import { useUsers } from '@/hooks/useUsers';
import { useMe } from '@/hooks/useAuth';
import { useToast } from '@/components/ui/Toast';
import type { Deal } from '@/lib/types';

const PIPELINE_KEY = 'vortem_selected_pipeline';

export default function DealsPage() {
  const { toast } = useToast();
  const { data: me } = useMe();
  const queryClient = useQueryClient();
  const { data: pipelines = [], isLoading: pipelinesLoading } = usePipelines();

  const [selectedPipelineId, setSelectedPipelineId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(PIPELINE_KEY) ?? '';
    }
    return '';
  });

  const { data: stages = [], isLoading: stagesLoading } = useStages(
    selectedPipelineId || undefined
  );
  const dealsParams = selectedPipelineId ? { pipeline_id: selectedPipelineId } : undefined;
  const { data: deals = [], isLoading: dealsLoading } = useDeals(dealsParams);
  const { data: users = [] } = useUsers();
  const updateDeal = useUpdateDeal();

  const [activeDeal, setActiveDeal] = useState<Deal | null>(null);
  const [createStageId, setCreateStageId] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [dragOverStageId, setDragOverStageId] = useState<string | null>(null);

  const canCreate = me?.role !== 'viewer';

  // Auto-select first pipeline when loaded
  useEffect(() => {
    if (!selectedPipelineId && pipelines.length > 0) {
      const firstId = pipelines[0].id;
      setSelectedPipelineId(firstId);
      localStorage.setItem(PIPELINE_KEY, firstId);
    }
  }, [pipelines, selectedPipelineId]);

  // Sync active deal object with updated query cache
  useEffect(() => {
    if (activeDeal) {
      const updated = deals.find((d) => d.id === activeDeal.id);
      if (updated) setActiveDeal(updated);
    }
  }, [deals]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePipelineChange = (id: string) => {
    setSelectedPipelineId(id);
    localStorage.setItem(PIPELINE_KEY, id);
  };

  const handleDragStart = (e: React.DragEvent, dealId: string, stageId: string) => {
    e.dataTransfer.setData('dealId', dealId);
    e.dataTransfer.setData('originStageId', stageId);
  };

  const handleDragOver = (e: React.DragEvent, stageId: string) => {
    e.preventDefault();
    setDragOverStageId(stageId);
  };

  const handleDragLeave = () => setDragOverStageId(null);

  const handleDrop = (e: React.DragEvent, targetStageId: string) => {
    e.preventDefault();
    setDragOverStageId(null);
    const dealId = e.dataTransfer.getData('dealId');
    const originStageId = e.dataTransfer.getData('originStageId');
    if (!dealId || originStageId === targetStageId) return;

    // Optimistic update
    queryClient.setQueryData<Deal[]>(['deals', dealsParams], (old) =>
      old?.map((d) => (d.id === dealId ? { ...d, stage_id: targetStageId } : d)) ?? []
    );

    updateDeal.mutate(
      { id: dealId, data: { stage_id: targetStageId } },
      {
        onError: () => {
          toast('Error al mover el deal', 'error');
          // Revert optimistic update
          queryClient.setQueryData<Deal[]>(['deals', dealsParams], (old) =>
            old?.map((d) => (d.id === dealId ? { ...d, stage_id: originStageId } : d)) ?? []
          );
        },
      }
    );
  };

  const pipelineOptions = pipelines.map((p) => ({ value: p.id, label: p.name }));
  const sortedStages = [...stages].sort((a, b) => a.order - b.order);
  const isLoading = pipelinesLoading || stagesLoading || dealsLoading;

  if (!pipelinesLoading && pipelines.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center text-gray-500">
        <p className="text-sm">No hay pipelines configurados. Crea uno en Configuración.</p>
        <Link href="/dashboard/settings" className="mt-2 text-sm text-blue-600 hover:underline">
          Ir a Configuración →
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col space-y-4">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Deals</h1>
        {pipelineOptions.length > 0 && (
          <Select
            options={pipelineOptions}
            value={selectedPipelineId}
            onChange={handlePipelineChange}
            className="w-52"
          />
        )}
      </div>

      {/* Kanban board */}
      <div className="flex-1 overflow-x-auto pb-4">
        <div
          className="flex gap-4"
          style={{ minWidth: `${Math.max(sortedStages.length, 3) * 296}px` }}
        >
          {isLoading
            ? Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="flex w-[280px] min-w-[280px] flex-col rounded-xl bg-gray-50 p-3"
                >
                  <div className="mb-3 h-5 w-24 animate-pulse rounded bg-gray-200" />
                  {Array.from({ length: 2 }).map((_, j) => (
                    <div key={j} className="mb-2 h-16 animate-pulse rounded-lg bg-gray-200" />
                  ))}
                </div>
              ))
            : sortedStages.map((stage) => {
                const stageDeals = deals.filter((d) => d.stage_id === stage.id);
                const totalValue = stageDeals.reduce((sum, d) => sum + (d.value ?? 0), 0);
                const isDragTarget = dragOverStageId === stage.id;

                return (
                  <div
                    key={stage.id}
                    className={`flex w-[280px] min-w-[280px] flex-col rounded-xl transition-colors ${
                      isDragTarget ? 'bg-blue-50 ring-2 ring-blue-300' : 'bg-gray-50'
                    }`}
                    onDragOver={(e) => handleDragOver(e, stage.id)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, stage.id)}
                  >
                    {/* Column header */}
                    <div className="flex items-center justify-between px-3 pb-2 pt-3">
                      <div className="flex items-center gap-2 min-w-0">
                        {stage.color && (
                          <span
                            className="h-2.5 w-2.5 shrink-0 rounded-full"
                            style={{ backgroundColor: stage.color }}
                          />
                        )}
                        <span className="truncate text-sm font-semibold text-gray-700">
                          {stage.name}
                        </span>
                        <span className="shrink-0 rounded-full bg-gray-200 px-1.5 py-0.5 text-xs font-medium text-gray-600">
                          {stageDeals.length}
                        </span>
                      </div>
                      {totalValue > 0 && (
                        <span className="shrink-0 text-xs text-gray-400">
                          ${totalValue.toLocaleString()}
                        </span>
                      )}
                    </div>

                    {/* Cards */}
                    <div
                      className="flex-1 space-y-2 overflow-y-auto px-3 pb-2"
                      style={{ maxHeight: 'calc(100vh - 220px)' }}
                    >
                      {stageDeals.length === 0 ? (
                        <div className="flex h-16 items-center justify-center rounded-lg border-2 border-dashed border-gray-200 text-xs text-gray-400">
                          Arrastra deals aquí
                        </div>
                      ) : (
                        stageDeals.map((deal) => (
                          <DealCard
                            key={deal.id}
                            deal={deal}
                            users={users}
                            onDragStart={handleDragStart}
                            onClick={setActiveDeal}
                          />
                        ))
                      )}
                    </div>

                    {/* Add deal button */}
                    {canCreate && (
                      <button
                        onClick={() => {
                          setCreateStageId(stage.id);
                          setCreateOpen(true);
                        }}
                        className="mx-3 mb-3 flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        Agregar deal
                      </button>
                    )}
                  </div>
                );
              })}
        </div>
      </div>

      <DealDrawer
        deal={activeDeal}
        onClose={() => setActiveDeal(null)}
      />

      <DealFormModal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        defaultPipelineId={selectedPipelineId}
        defaultStageId={createStageId}
      />
    </div>
  );
}
