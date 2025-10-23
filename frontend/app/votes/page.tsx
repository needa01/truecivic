'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Vote as VoteIcon, AlertCircle } from 'lucide-react';
import { apiClient, VoteListResponse } from '@/lib/api-client';
import { VoteCard } from '@/components/vote-card';
import { VoteFilters } from '@/components/vote-filters';

const PAGE_SIZE = 25;
const DEFAULT_PARLIAMENT = 44;
const DEFAULT_SESSION = 2;

export default function VotesPage() {
  const [page, setPage] = useState(0);
  const [resultFilter, setResultFilter] = useState('all');

  const { data, isLoading, isError, isFetching } = useQuery<VoteListResponse>({
    queryKey: ['votes', { page }],
    queryFn: () =>
      apiClient.getVotes({
        parliament: DEFAULT_PARLIAMENT,
        session: DEFAULT_SESSION,
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
      }),
  });

  const votes = useMemo(() => data?.votes ?? [], [data?.votes]);
  const total = data?.total ?? 0;
  const totalPages = total ? Math.ceil(total / PAGE_SIZE) : 1;

  // Filter votes based on result
  const filteredVotes = useMemo(() => {
    if (!votes || resultFilter === 'all') return votes;

    return votes.filter((vote) => {
      const result = (vote.result || '').toLowerCase();
      switch (resultFilter) {
        case 'passed':
          return result.includes('passed') || result.includes('agreed');
        case 'defeated':
          return result.includes('defeated') || result.includes('rejected');
        default:
          return true;
      }
    });
  }, [votes, resultFilter]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-primary via-surface-primary to-surface-secondary transition-colors duration-300">
      {/* Header */}
      <div className="border-b border-glass bg-surface-primary/40 backdrop-filter backdrop-blur sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="rounded-lg sm:rounded-xl bg-gradient-to-br from-accent-liberal/20 to-accent-liberal/10 p-2 sm:p-2.5 text-accent-liberal flex-shrink-0">
              <VoteIcon className="h-5 w-5 sm:h-6 sm:w-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg sm:text-2xl font-bold text-text-primary truncate">Votes</h1>
              <p className="text-xs sm:text-sm text-text-secondary mt-0.5 sm:mt-1 line-clamp-1">
                {total.toLocaleString()} votes • See ballots
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <VoteFilters result={resultFilter} onResultChange={setResultFilter} />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {isLoading && !data ? (
          <div className="flex flex-col items-center justify-center py-12 sm:py-16 gap-3 text-text-secondary">
            <Loader2 className="h-8 w-8 animate-spin text-accent-liberal" />
            <p className="text-sm sm:text-base">Loading votes…</p>
          </div>
        ) : isError ? (
          <div className="rounded-lg sm:rounded-2xl border border-status-failed/30 bg-status-failed/10 p-4 sm:p-6">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-status-failed flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-status-failed text-sm sm:text-base">Unable to load votes</p>
                <p className="mt-2 text-xs sm:text-sm text-status-failed/80">Populate data via the ingestion scripts first.</p>
              </div>
            </div>
          </div>
        ) : !votes.length ? (
          <div className="rounded-lg sm:rounded-2xl border border-glass bg-surface-secondary/40 p-6 sm:p-8 text-center">
            <VoteIcon className="h-10 sm:h-12 w-10 sm:w-12 text-text-tertiary mx-auto mb-2 sm:mb-3 opacity-50" />
            <p className="text-sm sm:text-base text-text-secondary">No votes available. Run `backfill_2025_sample.py` to populate data.</p>
          </div>
        ) : filteredVotes.length === 0 ? (
          <div className="rounded-lg sm:rounded-2xl border border-glass bg-surface-secondary/40 p-6 sm:p-8 text-center">
            <VoteIcon className="h-10 sm:h-12 w-10 sm:w-12 text-text-tertiary mx-auto mb-2 sm:mb-3 opacity-50" />
            <p className="text-sm sm:text-base text-text-secondary">No votes match the selected filters.</p>
          </div>
        ) : (
          <>
            {/* Vote Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
              {filteredVotes.map((vote) => (
                <VoteCard
                  key={vote.natural_id}
                  naturalId={vote.natural_id}
                  date={vote.vote_date}
                  description={vote.vote_description_en || vote.vote_description_fr || 'No description'}
                  result={vote.result}
                  yeas={vote.yeas}
                  nays={vote.nays}
                  abstentions={vote.abstentions}
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
                {filteredVotes.length} of {total.toLocaleString()} votes
              </div>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-center gap-2 sm:gap-3 mt-6">
              <button
                onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
                disabled={page === 0 || isFetching}
                className="px-3 sm:px-4 py-2 sm:py-2.5 min-w-[44px] min-h-[44px] sm:min-w-auto rounded-lg border border-glass bg-surface-secondary hover:bg-surface-secondary/80 text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:border-accent-liberal/50 text-sm sm:text-base font-medium"
              >
                ← <span className="hidden sm:inline">Previous</span>
              </button>
              <span className="text-xs sm:text-sm text-text-secondary whitespace-nowrap">
                {page + 1} / {totalPages || 1}
              </span>
              <button
                onClick={() => setPage((prev) => prev + 1)}
                disabled={isFetching || page + 1 >= totalPages}
                className="px-3 sm:px-4 py-2 sm:py-2.5 min-w-[44px] min-h-[44px] sm:min-w-auto rounded-lg border border-glass bg-surface-secondary hover:bg-surface-secondary/80 text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:border-accent-liberal/50 text-sm sm:text-base font-medium"
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
