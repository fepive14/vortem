'use client';

import { formatCurrency, initialsColor } from '@/lib/utils';
import type { Deal, User } from '@/lib/types';

interface DealCardProps {
  deal: Deal;
  users: User[];
  onDragStart: (e: React.DragEvent, dealId: string, stageId: string) => void;
  onClick: (deal: Deal) => void;
}

export function DealCard({ deal, users, onDragStart, onClick }: DealCardProps) {
  const assignedUser = users.find((u) => u.id === deal.assigned_to);

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, deal.id, deal.stage_id)}
      onClick={() => onClick(deal)}
      className="cursor-pointer rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow-md active:opacity-70 select-none"
    >
      <p className="truncate text-sm font-medium text-gray-900">{deal.name}</p>
      <p className="mt-1 text-xs text-gray-500">
        {formatCurrency(deal.value, deal.currency)}
      </p>
      {assignedUser && (
        <div className="mt-2 flex items-center gap-1.5">
          <span
            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white ${initialsColor(assignedUser.id)}`}
          >
            {assignedUser.full_name.charAt(0).toUpperCase()}
          </span>
          <span className="truncate text-xs text-gray-400">{assignedUser.full_name}</span>
        </div>
      )}
    </div>
  );
}
