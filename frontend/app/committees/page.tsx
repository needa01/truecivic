'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Loader2, Gavel, AlertCircle } from 'lucide-react';
import { CommitteeCard } from '@/components/committee-card';

export default function CommitteesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['committees', { limit: 50 }],
    queryFn: () => apiClient.getCommittees({ limit: 50 }),
  });

  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-primary via-surface-primary to-surface-secondary transition-colors duration-300">
      {/* Header */}
      <div className="border-b border-glass bg-surface-primary/40 backdrop-filter backdrop-blur sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="rounded-lg sm:rounded-xl bg-gradient-to-br from-accent-conservative/20 to-accent-conservative/10 p-2 sm:p-2.5 text-accent-conservative flex-shrink-0">
              <Gavel className="h-5 w-5 sm:h-6 sm:w-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg sm:text-2xl font-bold text-text-primary truncate">Parliamentary Committees</h1>
              <p className="text-xs sm:text-sm text-text-secondary mt-0.5 sm:mt-1 line-clamp-1">
                {data?.committees?.length ?? 0} committees • All parliamentary committees
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 sm:py-16 gap-3 text-text-secondary">
            <Loader2 className="h-8 w-8 animate-spin text-accent-conservative" />
            <p className="text-sm sm:text-base">Loading committees…</p>
          </div>
        ) : isError ? (
          <div className="rounded-lg sm:rounded-2xl border border-status-failed/30 bg-status-failed/10 p-4 sm:p-6">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-status-failed flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-status-failed text-sm sm:text-base">Unable to load committees</p>
                <p className="mt-2 text-xs sm:text-sm text-status-failed/80">Please verify the API is running and try again.</p>
              </div>
            </div>
          </div>
        ) : !data?.committees?.length ? (
          <div className="rounded-lg sm:rounded-2xl border border-glass bg-surface-secondary/40 p-6 sm:p-8 text-center">
            <Gavel className="h-10 sm:h-12 w-10 sm:w-12 text-text-tertiary mx-auto mb-2 sm:mb-3 opacity-50" />
            <p className="text-sm sm:text-base text-text-secondary">No committees found. Run the committee ingestion flow to populate this view.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {data.committees.map((committee) => (
              <CommitteeCard
                key={committee.natural_id || committee.committee_slug}
                naturalId={committee.natural_id || committee.committee_slug}
                slug={committee.committee_slug}
                nameEn={committee.name_en || null}
                nameFr={committee.name_fr || null}
                chamber={committee.chamber}
                parliament={committee.parliament}
                session={committee.session}
                acronymEn={committee.acronym_en || null}
                acronymFr={committee.acronym_fr || null}
                sourceUrl={committee.source_url}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}




