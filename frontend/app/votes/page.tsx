'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Loader2, Vote as VoteIcon } from 'lucide-react';
import { apiClient, VoteListResponse } from '@/lib/api-client';

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

export default function VotesPage() {
  const [page, setPage] = useState(0);

  const { data, isLoading, isError, isFetching } = useQuery<VoteListResponse>({
    queryKey: ['votes', { page }],
    queryFn: () =>
      apiClient.getVotes({
        parliament: DEFAULT_PARLIAMENT,
        session: DEFAULT_SESSION,
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
      }),
    keepPreviousData: true,
  });

  const votes = data?.votes ?? [];
  const total = data?.total ?? 0;
  const totalPages = total ? Math.ceil(total / PAGE_SIZE) : 1;

  return (
    <div className="min-h-screen bg-slate-950/40 text-slate-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-2xl bg-emerald-500/10 p-2 text-emerald-300">
            <VoteIcon className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold">Votes</h1>
            <p className="text-sm text-slate-400">
              Parliamentary votes with counts and descriptions. Click a vote to see individual ballots.
            </p>
          </div>
        </div>

        {isLoading && !data ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading votes…
          </div>
        ) : isError ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Unable to load votes. Populate data via the ingestion scripts first.
          </div>
        ) : !votes.length ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 text-slate-400">
            No votes available. Run `backfill_2025_sample.py` or the vote ingestion flow.
          </div>
        ) : (
          <>
            <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/40 backdrop-blur">
              <table className="min-w-full divide-y divide-slate-800">
                <thead className="bg-slate-900/60">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Vote ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Date
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Description
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Result
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Yeas / Nays / Abstentions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {votes.map((vote) => (
                    <tr key={vote.natural_id} className="hover:bg-slate-900/60 transition-colors">
                      <td className="px-4 py-3 text-sm font-medium text-emerald-200">
                        <Link href={`/votes/${encodeURIComponent(vote.natural_id)}`} className="hover:underline">
                          {vote.natural_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-300">{formatDate(vote.vote_date)}</td>
                      <td className="px-4 py-3 text-sm text-slate-200">
                        {vote.vote_description_en || vote.vote_description_fr || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-300">{vote.result}</td>
                      <td className="px-4 py-3 text-sm text-slate-300">
                        {vote.yeas} / {vote.nays} / {vote.abstentions}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
                disabled={isFetching || page + 1 >= totalPages}
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
