'use client';

import Link from 'next/link';
import { ArrowRight, Gavel } from 'lucide-react';
import { GlassCard } from '@/components/glass-card';
import { cn } from '@/lib/utils';

interface CommitteeCardProps {
  naturalId: string;
  slug: string;
  nameEn: string | null;
  nameFr: string | null;
  chamber: string;
  parliament?: number;
  session?: number;
  acronymEn: string | null;
  acronymFr: string | null;
  sourceUrl?: string | null;
}

function getSourceLabel(url?: string | null) {
  if (!url) return 'Internal';
  const normalized = url.toLowerCase();
  if (normalized.includes('ourcommons.ca')) return 'Our Commons';
  if (normalized.includes('openparliament.ca')) return 'OpenParliament';
  return 'External';
}

export function CommitteeCard({
  naturalId,
  slug,
  nameEn,
  nameFr,
  chamber,
  parliament,
  session,
  acronymEn,
  acronymFr,
  sourceUrl,
}: CommitteeCardProps) {
  const displayName = nameEn || acronymEn || 'Unknown Committee';
  const acronym = acronymEn || acronymFr;

  return (
    <GlassCard variant="hover" className="flex flex-col gap-4 group">
      {/* Header with slug and chamber */}
      <div className="flex items-start justify-between gap-3">
        <Link
          href={`/committees/${encodeURIComponent(naturalId)}`}
          className="flex-1 min-w-0"
        >
          <div className="text-sm font-semibold text-text-primary group-hover:text-accent-conservative transition-colors truncate">
            {slug}
          </div>
        </Link>
        <div className="text-xs font-semibold px-2 py-1 rounded-md bg-surface-secondary/50 text-text-secondary whitespace-nowrap">
          {chamber}
        </div>
      </div>

      {/* Committee name */}
      <Link href={`/committees/${encodeURIComponent(naturalId)}`} className="group/title">
        <h3 className="text-base font-semibold text-text-primary group-hover/title:text-accent-conservative transition-colors line-clamp-2">
          {displayName}
        </h3>
      </Link>

      {/* French name if different */}
      {nameFr && nameFr !== nameEn && (
        <p className="text-sm text-text-tertiary line-clamp-1">{nameFr}</p>
      )}

      {/* Meta info */}
      <div className="text-xs text-text-tertiary space-y-1">
        {parliament && session && (
          <div>Parliament {parliament} • Session {session}</div>
        )}
        {acronym && <div>Acronym: {acronym}</div>}
      </div>

      {/* Footer with source */}
      <div className="flex items-center justify-between pt-2 border-t border-glass">
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <Gavel className="h-3.5 w-3.5 text-text-tertiary" />
          {getSourceLabel(sourceUrl)}
        </div>
        <Link
          href={`/committees/${encodeURIComponent(naturalId)}`}
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
