'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { FileText, Loader2 } from 'lucide-react';
import { apiClient, BillListResponse } from '@/lib/api-client';

const PAGE_SIZE = 25;
const DEFAULT_PARLIAMENT = 44;
const DEFAULT_SESSION = 2;

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

export default function BillsPage() {
  const [page, setPage] = useState(0);

  const { data, isLoading, isError, isFetching } = useQuery<BillListResponse>({
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
    keepPreviousData: true,
  });

  const hasMore = data?.has_more ?? false;
  const total = data?.total ?? 0;
  const totalPages = useMemo(() => {
    if (!total) return 1;
    return Math.ceil(total / PAGE_SIZE);
  }, [total]);

  return (
    <div className="min-h-screen bg-slate-950/40 text-slate-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-2xl bg-blue-500/10 p-2 text-blue-300">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold">Bills (Parliament {DEFAULT_PARLIAMENT}, Session {DEFAULT_SESSION})</h1>
            <p className="text-sm text-slate-400">
              Data is live from the TrueCivic API. Run the 2025 backfill to see recent legislation.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4 text-sm text-slate-400">
          <p>
            Showing page <span className="text-slate-200">{page + 1}</span> of{' '}
            <span className="text-slate-200">{totalPages || 1}</span>
          </p>
          <p>
            Total bills indexed: <span className="text-slate-200">{total.toLocaleString()}</span>
          </p>
        </div>

        {isLoading && !data ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading bills…
          </div>
        ) : isError ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Unable to load bills. Verify the API is running and data ingestion has been executed.
          </div>
        ) : !data?.bills?.length ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 text-slate-400">
            No bills found for the selected parliament/session. Trigger the ingestion pipeline to populate data.
          </div>
        ) : (
          <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/40 backdrop-blur">
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-900/60">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Number
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Title
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Introduced
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Sponsor
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {data.bills.map((bill) => (
                  <tr key={bill.id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-blue-200">
                      <Link href={`/bills/${bill.id}`} className="hover:underline">
                        {bill.number}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-200">
                      <Link href={`/bills/${bill.id}`} className="hover:text-slate-100 transition-colors">
                        {bill.title_en || bill.short_title_en || 'Untitled'}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300">{formatDate(bill.introduced_date)}</td>
                    <td className="px-4 py-3 text-sm text-slate-300">{bill.law_status || bill.legisinfo_status || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-300">
                      {bill.sponsor_politician_name ? (
                        <Link
                          href={`/politicians/${bill.sponsor_politician_id}`}
                          className="text-indigo-300 hover:underline"
                        >
                          {bill.sponsor_politician_name}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-6 flex items-center justify-between">
          <button
            className="rounded-full border border-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
            onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
            disabled={page === 0 || isFetching}
          >
            Previous
          </button>
          <div className="text-xs text-slate-400">
            Page {page + 1} of {totalPages || 1}
          </div>
          <button
            className="rounded-full border border-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
            onClick={() => setPage((prev) => prev + 1)}
            disabled={!hasMore || isFetching}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
