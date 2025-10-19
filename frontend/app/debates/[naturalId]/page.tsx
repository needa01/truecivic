'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { apiClient, Debate, Speech } from '@/lib/api-client';

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function DebateDetailPage() {
  const params = useParams<{ naturalId: string }>();
  const router = useRouter();
  const naturalId = Array.isArray(params?.naturalId) ? params.naturalId[0] : params?.naturalId;

  const { data, isLoading, isError } = useQuery<Debate>({
    queryKey: ['debate', naturalId],
    queryFn: () => apiClient.getDebateById(naturalId!, { includeSpeeches: true }),
    enabled: Boolean(naturalId),
  });

  const speeches = data?.speeches ?? [];

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
            Invalid debate identifier.
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading debate…
          </div>
        ) : isError || !data ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Unable to load this debate. Verify debates have been ingested.
          </div>
        ) : (
          <div className="space-y-8">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 backdrop-blur space-y-4">
              <p className="text-sm text-orange-300 font-semibold">{data.natural_id}</p>
              <h1 className="text-3xl font-bold text-slate-100">
                {data.topic_en || data.debate_type || 'Parliamentary Debate'}
              </h1>
              {data.topic_fr && (
                <p className="text-sm text-slate-400 italic">{data.topic_fr}</p>
              )}
              <dl className="grid md:grid-cols-2 gap-3 text-sm text-slate-300">
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
                  <dt className="text-slate-400">Debate Date</dt>
                  <dd>{formatDate(data.debate_date)}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Debate Type</dt>
                  <dd>{data.debate_type}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Source</dt>
                  <dd>
                    {data.source_url ? (
                      <Link href={data.source_url} target="_blank" className="text-orange-300 hover:underline">
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
                  Speeches ({speeches.length})
                </h2>
              </div>
              {speeches.length ? (
                <div className="divide-y divide-slate-800/60">
                  {speeches.map((speech: Speech) => (
                    <div key={speech.natural_id} className="px-6 py-5 space-y-3">
                      <div className="flex items-center justify-between text-sm text-slate-400">
                        <div>
                          Speaker:{' '}
                          {speech.politician_id ? (
                            <Link
                              href={`/politicians/${speech.politician_id}`}
                              className="text-indigo-300 hover:underline"
                            >
                              {speech.speaker_name || speech.politician_id}
                            </Link>
                          ) : (
                            speech.speaker_name || 'Unknown'
                          )}
                        </div>
                        <div>{formatDate(speech.speech_time)}</div>
                      </div>
                      <p className="text-sm leading-relaxed text-slate-200 whitespace-pre-wrap">
                        {speech.content_en || speech.content_fr || 'No transcript available.'}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-6 py-8 text-sm text-slate-400">
                  No speeches stored for this debate yet.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
