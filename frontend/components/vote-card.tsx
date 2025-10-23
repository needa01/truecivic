'use client';

import Link from 'next/link';
import { ArrowRight, Calendar } from 'lucide-react';
import { GlassCard } from '@/components/glass-card';
import { StatusBadge } from '@/components/status-badge';
import { cn } from '@/lib/utils';

interface VoteCardProps {
  naturalId: string;
  date: string | null;
  description: string;
  result: string;
  yeas: number;
  nays: number;
  abstentions: number;
}

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function mapVoteResult(result: string): 'completed' | 'active' | 'pending' {
  if (!result) return 'pending';
  const lower = result.toLowerCase();
  if (lower.includes('passed') || lower.includes('agreed')) return 'completed';
  if (lower.includes('defeated') || lower.includes('rejected')) return 'active';
  return 'pending';
}

const total = (yeas: number, nays: number, abstentions: number): number => yeas + nays + abstentions;

export function VoteCard({
  naturalId,
  date,
  description,
  result,
  yeas,
  nays,
  abstentions,
}: VoteCardProps) {
  const mappedStatus = mapVoteResult(result);
  const formattedDate = formatDate(date);
  const totalVotes = total(yeas, nays, abstentions);

  return (
    <GlassCard variant="hover" className="flex flex-col gap-4 group">
      {/* Header with ID and result status */}
      <div className="flex items-start justify-between gap-3">
        <Link href={`/votes/${encodeURIComponent(naturalId)}`} className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-text-primary group-hover:text-accent-liberal transition-colors truncate">
            {naturalId}
          </div>
        </Link>
        <StatusBadge status={mappedStatus} size="sm" />
      </div>

      {/* Description */}
      <Link href={`/votes/${encodeURIComponent(naturalId)}`} className="group/desc">
        <h3 className="text-base font-semibold text-text-primary group-hover/desc:text-accent-liberal transition-colors line-clamp-2">
          {description}
        </h3>
      </Link>

      {/* Vote breakdown */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-surface-secondary/50 rounded-md p-2 text-center">
          <div className="text-status-active font-semibold">{yeas}</div>
          <div className="text-text-tertiary text-xs mt-1">Yeas</div>
        </div>
        <div className="bg-surface-secondary/50 rounded-md p-2 text-center">
          <div className="text-status-failed font-semibold">{nays}</div>
          <div className="text-text-tertiary text-xs mt-1">Nays</div>
        </div>
        <div className="bg-surface-secondary/50 rounded-md p-2 text-center">
          <div className="text-text-secondary font-semibold">{abstentions}</div>
          <div className="text-text-tertiary text-xs mt-1">Abstain</div>
        </div>
      </div>
      {/* Spacer with total votes for reference */}
      <div className="text-xs text-text-tertiary text-center">
        Total: {totalVotes} votes
      </div>

      {/* Date and action */}
      <div className="flex items-center justify-between pt-2 border-t border-glass">
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <Calendar className="h-3.5 w-3.5 text-text-tertiary" />
          {formattedDate}
        </div>
        <Link
          href={`/votes/${encodeURIComponent(naturalId)}`}
          className={cn(
            'inline-flex items-center gap-1 text-xs font-semibold',
            'text-accent-liberal group-hover:text-accent-liberal/80',
            'transition-colors opacity-0 group-hover:opacity-100'
          )}
        >
          View
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </GlassCard>
  );
}
