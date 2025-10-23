'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, MessageSquare, AlertCircle } from 'lucide-react';
import { apiClient, DebateListResponse } from '@/lib/api-client';
import { DebateCard } from '@/components/debate-card';
import { DebateFilters } from '@/components/debate-filters';

const PAGE_SIZE = 20;
const DEFAULT_PARLIAMENT = 44;
const DEFAULT_SESSION = 2;

export default function DebatesPage() {
  const [page, setPage] = useState(0);
  const [chamberFilter, setChamberFilter] = useState('all');

  const { data, isLoading, isError, isFetching } = useQuery<DebateListResponse>({
    queryKey: ['debates', { page }],
    queryFn: () =>
      apiClient.getDebates({
        parliament: DEFAULT_PARLIAMENT,
        session: DEFAULT_SESSION,
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
      }),
  });

  const debates = useMemo(() => data?.debates ?? [], [data?.debates]);
  const total = data?.total ?? 0;
  const totalPages = total ? Math.ceil(total / PAGE_SIZE) : 1;

  // Filter debates based on chamber
  const filteredDebates = useMemo(() => {
    if (!debates || chamberFilter === 'all') return debates;

    return debates.filter((debate) => {
      const chamber = (debate.chamber || '').toLowerCase();
      switch (chamberFilter) {
        case 'house of commons':
          return chamber.includes('house') || chamber.includes('commons');
        case 'senate':
          return chamber.includes('senate');
        default:
          return true;
      }
    });
  }, [debates, chamberFilter]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-primary via-surface-primary to-surface-secondary transition-colors duration-300">
      {/* Header */}
      <div className="border-b border-glass bg-surface-primary/40 backdrop-filter backdrop-blur sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="rounded-lg sm:rounded-xl bg-gradient-to-br from-accent-ndp/20 to-accent-ndp/10 p-2 sm:p-2.5 text-accent-ndp flex-shrink-0">
              <MessageSquare className="h-5 w-5 sm:h-6 sm:w-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg sm:text-2xl font-bold text-text-primary truncate">Debates (Hansard)</h1>
              <p className="text-xs sm:text-sm text-text-secondary mt-0.5 sm:mt-1 line-clamp-1">
                {total.toLocaleString()} debates • Parliamentary speeches
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <DebateFilters chamber={chamberFilter} onChamberChange={setChamberFilter} />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {isLoading && !data ? (
          <div className="flex flex-col items-center justify-center py-12 sm:py-16 gap-3 text-text-secondary">
            <Loader2 className="h-8 w-8 animate-spin text-accent-ndp" />
            <p className="text-sm sm:text-base">Loading debates…</p>
          </div>
        ) : isError ? (
          <div className="rounded-lg sm:rounded-2xl border border-status-failed/30 bg-status-failed/10 p-4 sm:p-6">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-status-failed flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-status-failed text-sm sm:text-base">Unable to load debates</p>
                <p className="mt-2 text-xs sm:text-sm text-status-failed/80">Ensure debate ingestion has been executed.</p>
              </div>
            </div>
          </div>
        ) : !debates.length ? (
          <div className="rounded-lg sm:rounded-2xl border border-glass bg-surface-secondary/40 p-6 sm:p-8 text-center">
            <MessageSquare className="h-10 sm:h-12 w-10 sm:w-12 text-text-tertiary mx-auto mb-2 sm:mb-3 opacity-50" />
            <p className="text-sm sm:text-base text-text-secondary">No debates available. Run the debate ingestion flow to populate data.</p>
          </div>
        ) : filteredDebates.length === 0 ? (
          <div className="rounded-lg sm:rounded-2xl border border-glass bg-surface-secondary/40 p-6 sm:p-8 text-center">
            <MessageSquare className="h-10 sm:h-12 w-10 sm:w-12 text-text-tertiary mx-auto mb-2 sm:mb-3 opacity-50" />
            <p className="text-sm sm:text-base text-text-secondary">No debates match the selected filters.</p>
          </div>
        ) : (
          <>
            {/* Debate Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 mb-6 sm:mb-8">
              {filteredDebates.map((debate) => (
                <DebateCard
                  key={debate.natural_id}
                  naturalId={debate.natural_id}
                  date={debate.debate_date}
                  topicEn={debate.topic_en || null}
                  topicFr={debate.topic_fr || null}
                  debateType={debate.debate_type}
                  chamber={debate.chamber}
                  parliament={debate.parliament}
                  session={debate.session}
                />
              ))}
            </div>

            {/* Pagination Info */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4 py-4 border-t border-glass text-xs sm:text-sm">
              <p className="text-text-secondary">
                Showing page <span className="font-semibold text-text-primary">{page + 1}</span> of{' '}
                <span className="font-semibold text-text-primary">{totalPages || 1}</span>
              </p>
              <div className="text-text-secondary">
                {filteredDebates.length} of {total.toLocaleString()} debates
              </div>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-center gap-2 sm:gap-3 mt-6">
              <button
                onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
                disabled={page === 0 || isFetching}
                className="px-3 sm:px-4 py-2 sm:py-2.5 min-w-[44px] min-h-[44px] sm:min-w-auto rounded-lg border border-glass bg-surface-secondary hover:bg-surface-secondary/80 text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:border-accent-ndp/50 text-sm sm:text-base font-medium"
              >
                ← <span className="hidden sm:inline">Previous</span>
              </button>
              <span className="text-xs sm:text-sm text-text-secondary whitespace-nowrap">
                {page + 1} / {totalPages || 1}
              </span>
              <button
                onClick={() => setPage((prev) => prev + 1)}
                disabled={isFetching || page + 1 >= totalPages}
                className="px-3 sm:px-4 py-2 sm:py-2.5 min-w-[44px] min-h-[44px] sm:min-w-auto rounded-lg border border-glass bg-surface-secondary hover:bg-surface-secondary/80 text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:border-accent-ndp/50 text-sm sm:text-base font-medium"
              >
                <span className="hidden sm:inline">Next</span> →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
