'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Loader2, AlertCircle } from 'lucide-react';
import { apiClient, BillListResponse, ApiClientError } from '@/lib/api-client';
import { BillCard } from '@/components/bill-card';
import { BillFilters } from '@/components/bill-filters';

const PAGE_SIZE = 25;
const DEFAULT_PARLIAMENT = 44;
const DEFAULT_SESSION = 2;

export default function BillsPage() {
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState('all');

  const { data, isLoading, isError, isFetching, error } = useQuery<BillListResponse, ApiClientError>({
    queryKey: ['bills', { page }],
    queryFn: () =>
      apiClient.getBills({
        parliament: DEFAULT_PARLIAMENT,
        session: DEFAULT_SESSION,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        sort: 'introduced_date',
        order: 'desc',
      }),
  });

  const hasMore = data?.has_more ?? false;
  const total = data?.total ?? 0;
  const totalPages = useMemo(() => {
    if (!total) return 1;
    return Math.ceil(total / PAGE_SIZE);
  }, [total]);

  const errorMessage = error?.message ?? 'Verify the API is running and data ingestion has been executed.';

  // Filter bills based on status
  const filteredBills = useMemo(() => {
    if (!data?.bills || statusFilter === 'all') return data?.bills || [];

    return data.bills.filter((bill) => {
      const status = (bill.law_status || bill.legisinfo_status || '').toLowerCase();

      switch (statusFilter) {
        case 'active':
          return status.includes('active');
        case 'first-reading':
          return status.includes('first reading') || status.includes('1st reading');
        case 'second-reading':
          return status.includes('second reading') || status.includes('2nd reading');
        case 'third-reading':
          return status.includes('third reading') || status.includes('3rd reading');
        case 'royal-assent':
          return status.includes('royal assent') || status.includes('assented');
        case 'failed':
          return status.includes('withdrawn') || status.includes('died');
        default:
          return true;
      }
    });
  }, [data?.bills, statusFilter]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-primary via-surface-primary to-surface-secondary transition-colors duration-300">
      {/* Header */}
      <div className="border-b border-glass bg-surface-primary/40 backdrop-filter backdrop-blur sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="rounded-lg sm:rounded-xl bg-gradient-to-br from-accent-conservative/20 to-accent-conservative/10 p-2 sm:p-2.5 text-accent-conservative flex-shrink-0">
              <FileText className="h-5 w-5 sm:h-6 sm:w-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg sm:text-2xl font-bold text-text-primary truncate">
                Bills
              </h1>
              <p className="text-xs sm:text-sm text-text-secondary mt-0.5 sm:mt-1 line-clamp-1">
                {total.toLocaleString()} bills • Live from TrueCivic API
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <BillFilters status={statusFilter} onStatusChange={setStatusFilter} />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {isLoading && !data ? (
          <div className="flex flex-col items-center justify-center py-12 sm:py-16 gap-3 text-text-secondary">
            <Loader2 className="h-8 w-8 animate-spin text-accent-conservative" />
            <p className="text-sm sm:text-base">Loading bills…</p>
          </div>
        ) : isError ? (
          <div className="rounded-lg sm:rounded-2xl border border-status-failed/30 bg-status-failed/10 p-4 sm:p-6">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-status-failed flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-status-failed text-sm sm:text-base">Unable to load bills</p>
                <p className="mt-2 text-xs sm:text-sm text-status-failed/80">{errorMessage}</p>
              </div>
            </div>
          </div>
        ) : !data?.bills?.length ? (
          <div className="rounded-lg sm:rounded-2xl border border-glass bg-surface-secondary/40 p-6 sm:p-8 text-center">
            <FileText className="h-10 sm:h-12 w-10 sm:w-12 text-text-tertiary mx-auto mb-2 sm:mb-3 opacity-50" />
            <p className="text-sm sm:text-base text-text-secondary">No bills found for the selected parliament/session.</p>
          </div>
        ) : filteredBills.length === 0 ? (
          <div className="rounded-lg sm:rounded-2xl border border-glass bg-surface-secondary/40 p-6 sm:p-8 text-center">
            <FileText className="h-10 sm:h-12 w-10 sm:w-12 text-text-tertiary mx-auto mb-2 sm:mb-3 opacity-50" />
            <p className="text-sm sm:text-base text-text-secondary">No bills match the selected filters.</p>
          </div>
        ) : (
          <>
            {/* Bill Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
              {filteredBills.map((bill) => (
                <BillCard
                  key={bill.id}
                  id={bill.id}
                  number={bill.number}
                  title={bill.title_en || bill.short_title_en || 'Untitled'}
                  status={bill.law_status || bill.legisinfo_status || ''}
                  introducedDate={bill.introduced_date}
                  sponsorName={bill.sponsor_politician_name || null}
                  sponsorId={bill.sponsor_politician_id || null}
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
                {filteredBills.length} of {total.toLocaleString()} bills
              </div>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-center gap-2 sm:gap-3 mt-6">
              <button
                onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
                disabled={page === 0 || isFetching}
                className="px-3 sm:px-4 py-2 sm:py-2.5 min-w-[44px] min-h-[44px] sm:min-w-auto rounded-lg border border-glass bg-surface-secondary hover:bg-surface-secondary/80 text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:border-accent-conservative/50 text-sm sm:text-base font-medium"
              >
                ← <span className="hidden sm:inline">Previous</span>
              </button>
              <span className="text-xs sm:text-sm text-text-secondary whitespace-nowrap">
                {page + 1} / {totalPages || 1}
              </span>
              <button
                onClick={() => setPage((prev) => prev + 1)}
                disabled={!hasMore || isFetching}
                className="px-3 sm:px-4 py-2 sm:py-2.5 min-w-[44px] min-h-[44px] sm:min-w-auto rounded-lg border border-glass bg-surface-secondary hover:bg-surface-secondary/80 text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:border-accent-conservative/50 text-sm sm:text-base font-medium"
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
