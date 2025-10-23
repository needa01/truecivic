'use client';

import Link from 'next/link';
import { ArrowRight, Calendar } from 'lucide-react';
import { GlassCard } from '@/components/glass-card';
import { StatusBadge } from '@/components/status-badge';
import { cn } from '@/lib/utils';

interface BillCardProps {
  id: string | number;
  number: string;
  title: string;
  status: string;
  introducedDate: string | null;
  sponsorName: string | null;
  sponsorId: string | number | null;
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

function mapBillStatus(
  status: string | null
): 'active' | 'pending' | 'completed' | 'failed' | 'first-reading' | 'second-reading' | 'third-reading' | 'royal-assent' {
  if (!status) return 'pending';

  const lower = status.toLowerCase();
  if (lower.includes('royal assent') || lower.includes('assented')) return 'royal-assent';
  if (lower.includes('third reading') || lower.includes('3rd reading')) return 'third-reading';
  if (lower.includes('second reading') || lower.includes('2nd reading')) return 'second-reading';
  if (lower.includes('first reading') || lower.includes('1st reading')) return 'first-reading';
  if (lower.includes('withdrawn') || lower.includes('died')) return 'failed';
  if (lower.includes('active')) return 'active';

  return 'pending';
}

export function BillCard({
  id,
  number,
  title,
  status,
  introducedDate,
  sponsorName,
  sponsorId,
}: BillCardProps) {
  const mappedStatus = mapBillStatus(status);
  const formattedDate = formatDate(introducedDate);

  return (
    <GlassCard variant="hover" className="flex flex-col gap-4 group">
      {/* Header with number and status */}
      <div className="flex items-start justify-between gap-3">
        <Link href={`/bills/${id}`} className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-text-primary group-hover:text-accent-conservative transition-colors">
            {number}
          </div>
        </Link>
        <StatusBadge status={mappedStatus} size="sm" />
      </div>

      {/* Title */}
      <Link href={`/bills/${id}`} className="group/title">
        <h3 className="text-base font-semibold text-text-primary group-hover/title:text-accent-conservative transition-colors line-clamp-2">
          {title}
        </h3>
      </Link>

      {/* Sponsor */}
      {sponsorName && (
        <div className="text-xs text-text-secondary">
          Sponsor:{' '}
          {sponsorId ? (
            <Link
              href={`/politicians/${sponsorId}`}
              className="text-accent-liberal hover:text-accent-liberal/80 transition-colors underline"
            >
              {sponsorName}
            </Link>
          ) : (
            <span>{sponsorName}</span>
          )}
        </div>
      )}

      {/* Date and action */}
      <div className="flex items-center justify-between pt-2 border-t border-glass">
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <Calendar className="h-3.5 w-3.5 text-text-tertiary" />
          {formattedDate}
        </div>
        <Link
          href={`/bills/${id}`}
          className={cn(
            'inline-flex items-center gap-1 text-xs font-semibold',
            'text-accent-conservative group-hover:text-accent-conservative/80',
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
