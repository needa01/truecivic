'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Loader2, MessageSquare } from 'lucide-react';
import { apiClient, DebateListResponse } from '@/lib/api-client';

const PAGE_SIZE = 20;
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

export default function DebatesPage() {
  const [page, setPage] = useState(0);

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

  const debates = data?.debates ?? [];
  const total = data?.total ?? 0;
  const totalPages = total ? Math.ceil(total / PAGE_SIZE) : 1;

  return (
    <div className="min-h-screen bg-slate-950/40 text-slate-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-2xl bg-orange-500/10 p-2 text-orange-300">
            <MessageSquare className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold">Debates (Hansard)</h1>
            <p className="text-sm text-slate-400">
              Explore debates and speeches from the House of Commons.
            </p>
          </div>
        </div>

        {isLoading && !data ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading debates…
          </div>
        ) : isError ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Unable to load debates. Ensure debate ingestion has been executed.
          </div>
        ) : !debates.length ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 text-slate-400">
            No debates available. Run the debate ingestion flow to populate data.
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {debates.map((debate) => (
                <Link
                  key={debate.natural_id}
                  href={`/debates/${encodeURIComponent(debate.natural_id)}`}
                  className="block rounded-3xl border border-slate-800 bg-slate-900/40 p-6 hover:border-slate-700 transition-colors"
                >
                  <div className="flex flex-wrap justify-between gap-3">
                    <div>
                      <p className="text-sm text-orange-300 font-semibold">{debate.natural_id}</p>
                      <h2 className="text-lg font-semibold text-slate-100">
                        {debate.topic_en || debate.debate_type || 'Unnamed Debate'}
                      </h2>
                      {debate.topic_fr && (
                        <p className="text-sm text-slate-400 italic">{debate.topic_fr}</p>
                      )}
                    </div>
                    <div className="text-sm text-slate-300">
                      <div>{formatDate(debate.debate_date)}</div>
                      <div className="text-slate-400">
                        Parliament {debate.parliament} · Session {debate.session}
                      </div>
                      <div className="text-slate-400">Chamber: {debate.chamber}</div>
                    </div>
                  </div>
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
