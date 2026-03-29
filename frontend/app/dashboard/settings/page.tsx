'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, ChevronDown, ChevronRight, UserX, UserCheck } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { UserFormModal } from '@/components/settings/UserFormModal';
import { PipelineFormModal } from '@/components/settings/PipelineFormModal';
import { StageFormModal } from '@/components/settings/StageFormModal';
import { useUsers, useDeactivateUser } from '@/hooks/useUsers';
import { usePipelines, useStages } from '@/hooks/usePipelines';
import { useMe } from '@/hooks/useAuth';
import type { Pipeline } from '@/lib/types';

type Tab = 'users' | 'pipeline';

function PipelineRow({ pipeline }: { pipeline: Pipeline }) {
  const { toast } = useToast();
  const [expanded, setExpanded] = useState(false);
  const [stageModalOpen, setStageModalOpen] = useState(false);
  const { data: stages = [], isLoading } = useStages(expanded ? pipeline.id : undefined);
  const sortedStages = [...stages].sort((a, b) => a.order - b.order);

  return (
    <div className="border-b border-gray-100 last:border-0">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-gray-400 hover:text-gray-600"
            aria-label={expanded ? 'Colapsar' : 'Expandir'}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
          <span className="text-sm font-medium text-gray-900">{pipeline.name}</span>
          {pipeline.is_default && (
            <Badge variant="active">
              <span className="text-xs">Por defecto</span>
            </Badge>
          )}
        </div>
        <button
          onClick={() => { setExpanded(true); setStageModalOpen(true); }}
          className="flex items-center gap-1 rounded-md border border-gray-300 px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          <Plus className="h-3.5 w-3.5" />
          Nueva Etapa
        </button>
      </div>

      {expanded && (
        <div className="px-10 pb-3">
          {isLoading ? (
            <div className="flex items-center gap-2 py-2 text-xs text-gray-400">
              <Spinner size="sm" />
              Cargando etapas...
            </div>
          ) : sortedStages.length === 0 ? (
            <p className="py-2 text-xs text-gray-400">No hay etapas. Agrega la primera.</p>
          ) : (
            <div className="space-y-1">
              {sortedStages.map((stage) => (
                <div
                  key={stage.id}
                  className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  {stage.color && (
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: stage.color }}
                    />
                  )}
                  <span className="flex-1">{stage.name}</span>
                  <span className="text-xs text-gray-400">#{stage.order}</span>
                  <span className="text-xs text-gray-400">{stage.probability}%</span>
                  {stage.is_won && (
                    <span className="rounded-full bg-green-50 px-1.5 py-0.5 text-[10px] font-medium text-green-700">
                      Won
                    </span>
                  )}
                  {stage.is_lost && (
                    <span className="rounded-full bg-red-50 px-1.5 py-0.5 text-[10px] font-medium text-red-700">
                      Lost
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <StageFormModal
        isOpen={stageModalOpen}
        onClose={() => setStageModalOpen(false)}
        pipelineId={pipeline.id}
        nextOrder={sortedStages.length}
      />
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { data: me, isLoading: meLoading } = useMe();
  const [tab, setTab] = useState<Tab>('users');
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [pipelineModalOpen, setPipelineModalOpen] = useState(false);

  const { data: users = [], isLoading: usersLoading } = useUsers();
  const { data: pipelines = [], isLoading: pipelinesLoading } = usePipelines();
  const deactivateUser = useDeactivateUser();

  useEffect(() => {
    if (!meLoading && me && me.role !== 'admin') {
      router.replace('/dashboard');
    }
  }, [me, meLoading, router]);

  if (meLoading || !me) return null;
  if (me.role !== 'admin') return null;

  const handleDeactivate = (userId: string, userName: string) => {
    if (!confirm(`¿Desactivar a ${userName}? El usuario no podrá iniciar sesión.`)) return;
    deactivateUser.mutate(userId, {
      onSuccess: () => toast('Usuario desactivado', 'success'),
      onError: () => toast('Error al desactivar', 'error'),
    });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Configuración</h1>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {(['users', 'pipeline'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === t
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'users' ? 'Usuarios' : 'Pipeline'}
          </button>
        ))}
      </div>

      {/* Users tab */}
      {tab === 'users' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">{users.length} usuario(s) en la organización</p>
            <button
              onClick={() => setUserModalOpen(true)}
              className="flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Invitar Usuario
            </button>
          </div>

          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-100 bg-gray-50">
                  <tr>
                    {['Nombre', 'Email', 'Rol', 'Estado', 'Acciones'].map((h) => (
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
                  {usersLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <tr key={i}>
                        {Array.from({ length: 5 }).map((_, j) => (
                          <td key={j} className="px-4 py-3">
                            <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    users.map((u) => {
                      const isSelf = u.id === me.id;
                      return (
                        <tr key={u.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">
                            {u.full_name}
                          </td>
                          <td className="px-4 py-3 text-gray-600">{u.email}</td>
                          <td className="px-4 py-3">
                            <Badge variant={u.role}>{u.role}</Badge>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                                u.is_active
                                  ? 'bg-green-50 text-green-700'
                                  : 'bg-gray-100 text-gray-500'
                              }`}
                            >
                              {u.is_active ? 'Activo' : 'Inactivo'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {isSelf ? (
                              <span
                                title="No puedes desactivarte a ti mismo"
                                className="cursor-not-allowed text-xs text-gray-300"
                              >
                                <UserX className="h-4 w-4" />
                              </span>
                            ) : u.is_active ? (
                              <button
                                onClick={() => handleDeactivate(u.id, u.full_name)}
                                disabled={deactivateUser.isPending}
                                title="Desactivar usuario"
                                className="text-red-400 hover:text-red-600 disabled:opacity-50"
                              >
                                <UserX className="h-4 w-4" />
                              </button>
                            ) : (
                              <span title="Usuario inactivo" className="text-gray-300">
                                <UserCheck className="h-4 w-4" />
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <UserFormModal isOpen={userModalOpen} onClose={() => setUserModalOpen(false)} />
        </div>
      )}

      {/* Pipeline tab */}
      {tab === 'pipeline' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">{pipelines.length} pipeline(s)</p>
            <button
              onClick={() => setPipelineModalOpen(true)}
              className="flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Nuevo Pipeline
            </button>
          </div>

          <Card>
            {pipelinesLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner size="lg" />
              </div>
            ) : pipelines.length === 0 ? (
              <p className="py-8 text-center text-sm text-gray-400">
                No hay pipelines. Crea el primero.
              </p>
            ) : (
              pipelines.map((p) => <PipelineRow key={p.id} pipeline={p} />)
            )}
          </Card>

          <PipelineFormModal
            isOpen={pipelineModalOpen}
            onClose={() => setPipelineModalOpen(false)}
          />
        </div>
      )}
    </div>
  );
}
