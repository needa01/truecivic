'use client';

import Link from 'next/link';
import { ArrowRight, Calendar } from 'lucide-react';
import { GlassCard } from '@/components/glass-card';
import { cn } from '@/lib/utils';

interface DebateCardProps {
  naturalId: string;
  date: string | null;
  topicEn: string | null;
  topicFr: string | null;
  debateType: string;
  chamber: string;
  parliament: number;
  session: number;
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

export function DebateCard({
  naturalId,
  date,
  topicEn,
  topicFr,
  debateType,
  chamber,
  parliament,
  session,
}: DebateCardProps) {
  const formattedDate = formatDate(date);
  const title = topicEn || debateType || 'Unnamed Debate';

  return (
    <GlassCard variant="hover" className="flex flex-col gap-4 group">
      {/* Header with ID and chamber */}
      <div className="flex items-start justify-between gap-3">
        <Link href={`/debates/${encodeURIComponent(naturalId)}`} className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-text-primary group-hover:text-accent-ndp transition-colors truncate">
            {naturalId}
          </div>
        </Link>
        <div className="text-xs font-semibold px-2 py-1 rounded-md bg-surface-secondary/50 text-text-secondary">
          {chamber}
        </div>
      </div>

      {/* Title */}
      <Link href={`/debates/${encodeURIComponent(naturalId)}`} className="group/title">
        <h3 className="text-base font-semibold text-text-primary group-hover/title:text-accent-ndp transition-colors line-clamp-2">
          {title}
        </h3>
      </Link>

      {/* French title if different */}
      {topicFr && topicFr !== topicEn && (
        <p className="text-sm text-text-tertiary italic line-clamp-1">{topicFr}</p>
      )}

      {/* Meta info */}
      <div className="text-xs text-text-tertiary space-y-1">
        <div>Parliament {parliament} • Session {session}</div>
        <div>Debate type: {debateType}</div>
      </div>

      {/* Date and action */}
      <div className="flex items-center justify-between pt-2 border-t border-glass">
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <Calendar className="h-3.5 w-3.5 text-text-tertiary" />
          {formattedDate}
        </div>
        <Link
          href={`/debates/${encodeURIComponent(naturalId)}`}
          className={cn(
            'inline-flex items-center gap-1 text-xs font-semibold',
            'text-accent-ndp group-hover:text-accent-ndp/80',
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
