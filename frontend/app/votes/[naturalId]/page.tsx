'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { apiClient, Vote, VoteRecord } from '@/lib/api-client';

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

export default function VoteDetailPage() {
  const params = useParams<{ naturalId: string }>();
  const router = useRouter();
  const naturalId = Array.isArray(params?.naturalId) ? params.naturalId[0] : params?.naturalId;

  const { data, isLoading, isError } = useQuery<Vote>({
    queryKey: ['vote', naturalId],
    queryFn: () => apiClient.getVoteById(naturalId!, { includeRecords: true }),
    enabled: Boolean(naturalId),
  });

  return (
    <div className="min-h-screen bg-slate-950/40 text-slate-100">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-6">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-slate-100 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        {!naturalId ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Invalid vote identifier.
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading vote…
          </div>
        ) : isError || !data ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Unable to load this vote. Confirm votes have been ingested.
          </div>
        ) : (
          <div className="space-y-8">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 backdrop-blur">
              <p className="text-sm text-emerald-300 font-semibold mb-2">{data.natural_id}</p>
              <h1 className="text-3xl font-bold text-slate-100">
                Vote #{data.vote_number} — {data.vote_description_en || data.vote_description_fr || 'No description'}
              </h1>
              <dl className="mt-6 grid md:grid-cols-2 gap-3 text-sm text-slate-300">
                <div>
                  <dt className="text-slate-400">Parliament</dt>
                  <dd>{data.parliament}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Session</dt>
                  <dd>{data.session}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Chamber</dt>
                  <dd>{data.chamber}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Date</dt>
                  <dd>{formatDate(data.vote_date)}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Result</dt>
                  <dd>{data.result}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Bill</dt>
                  <dd>
                    {data.bill_number ? (
                      <span className="text-slate-200">{data.bill_number}</span>
                    ) : (
                      '—'
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">Yeas</dt>
                  <dd>{data.yeas}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Nays</dt>
                  <dd>{data.nays}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Abstentions</dt>
                  <dd>{data.abstentions}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Source</dt>
                  <dd>
                    {data.source_url ? (
                      <Link href={data.source_url} target="_blank" className="text-emerald-300 hover:underline">
                        OpenParliament
                      </Link>
                    ) : (
                      '—'
                    )}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-900/30">
              <div className="border-b border-slate-800 px-6 py-4">
                <h2 className="text-xl font-semibold text-slate-100">
                  MP Vote Records ({data.vote_records?.length ?? 0})
                </h2>
              </div>
              {data.vote_records?.length ? (
                <div className="max-h-[480px] overflow-y-auto">
                  <table className="min-w-full divide-y divide-slate-800">
                    <thead className="bg-slate-900/60 sticky top-0">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Politician ID
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Position
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Recorded At
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80">
                      {data.vote_records.map((record: VoteRecord) => (
                        <tr key={record.natural_id} className="hover:bg-slate-900/60 transition-colors">
                          <td className="px-4 py-2 text-sm text-slate-200">
                            <Link href={`/politicians/${record.politician_id}`} className="text-indigo-300 hover:underline">
                              {record.politician_id}
                            </Link>
                          </td>
                          <td className="px-4 py-2 text-sm text-slate-300">{record.vote_position}</td>
                          <td className="px-4 py-2 text-sm text-slate-400">{formatDate(record.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="px-6 py-8 text-sm text-slate-400">
                  Individual vote records are not available for this ballot yet.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
