'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Loader2, Users } from 'lucide-react';
import { apiClient, PoliticianListResponse, ApiClientError } from '@/lib/api-client';

const PAGE_SIZE = 30;

export default function PoliticiansPage() {
  const [page, setPage] = useState(0);

  const { data, isLoading, isError, isFetching, error } = useQuery<PoliticianListResponse, ApiClientError>({
    queryKey: ['politicians', { page }],
    queryFn: () =>
      apiClient.getPoliticians({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        currentOnly: true,
      }),
  });

  const hasMore = data?.has_more ?? false;
  const total = data?.total ?? 0;
  const totalPages = total ? Math.ceil(total / PAGE_SIZE) : 1;
  const errorMessage = error?.message ?? 'Run the ingestion pipeline or check the API connection.';

  return (
    <div className="min-h-screen bg-slate-950/40 text-slate-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-2xl bg-purple-500/10 p-2 text-purple-300">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold">Members of Parliament</h1>
            <p className="text-sm text-slate-400">
              Listing active MPs using data returned by the TrueCivic API.
            </p>
          </div>
        </div>

        {isLoading && !data ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading politicians…
          </div>
        ) : isError ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            <p className="font-semibold">Unable to load politicians.</p>
            <p className="mt-2 text-sm text-red-100/80">{errorMessage}</p>
          </div>
        ) : !data?.politicians?.length ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 text-slate-400">
            No politicians found. Populate the database and refresh this page.
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {data.politicians.map((politician) => (
                <Link
                  key={politician.id}
                  href={`/politicians/${politician.id}`}
                  className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 hover:border-slate-700 transition-colors"
                >
                  <p className="text-sm text-purple-300 font-semibold">{politician.politician_id}</p>
                  <h2 className="text-lg font-semibold text-slate-100">{politician.name}</h2>
                  <dl className="mt-3 space-y-1 text-sm text-slate-300">
                    <div>
                      <dt className="inline text-slate-400">Party:</dt>{' '}
                      <dd className="inline">{politician.current_party || '—'}</dd>
                    </div>
                    <div>
                      <dt className="inline text-slate-400">Riding:</dt>{' '}
                      <dd className="inline">{politician.current_riding || '—'}</dd>
                    </div>
                  </dl>
                </Link>
              ))}
            </div>

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
          </>
        )}
      </div>
    </div>
  );
}
