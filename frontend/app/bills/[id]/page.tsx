'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeft, ExternalLink, Loader2 } from 'lucide-react';
import { apiClient, Bill, ApiClientError } from '@/lib/api-client';

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

export default function BillDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const idParam = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const billId = Number(idParam);

  const { data, isLoading, isError, error } = useQuery<Bill, ApiClientError>({
    queryKey: ['bill', billId],
    queryFn: () => apiClient.getBillById(billId),
    enabled: Number.isFinite(billId),
  });
  const errorMessage = error?.message ?? 'It may not exist yet—try re-running the ingestion pipeline.';

  if (!Number.isFinite(billId)) {
    return (
      <div className="min-h-screen bg-slate-950/40 text-slate-100">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Invalid bill identifier provided.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950/40 text-slate-100">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-6">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-slate-100 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading bill details…
          </div>
        ) : isError || !data ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            <p className="font-semibold">Unable to load this bill.</p>
            <p className="mt-2 text-sm text-red-100/80">{errorMessage}</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 backdrop-blur">
              <p className="text-sm text-blue-300 font-semibold mb-2">{data.number}</p>
              <h1 className="text-3xl font-bold text-slate-100 mb-3">
                {data.title_en || data.short_title_en || 'Untitled Bill'}
              </h1>
              {data.title_fr && (
                <p className="text-lg text-slate-300 italic mb-2">{data.title_fr}</p>
              )}
              <div className="grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
                <div>
                  <span className="text-slate-400">Parliament:</span> {data.parliament}
                </div>
                <div>
                  <span className="text-slate-400">Session:</span> {data.session}
                </div>
                <div>
                  <span className="text-slate-400">Introduced:</span> {formatDate(data.introduced_date)}
                </div>
                <div>
                  <span className="text-slate-400">Law Status:</span> {data.law_status || '—'}
                </div>
                <div>
                  <span className="text-slate-400">LegiStatus:</span> {data.legisinfo_status || '—'}
                </div>
                <div>
                  <span className="text-slate-400">Royal Assent:</span> {formatDate(data.royal_assent_date)}
                </div>
                <div>
                  <span className="text-slate-400">Sponsor:</span>{' '}
                  {data.sponsor_politician_name ? (
                    <Link
                      href={`/politicians/${data.sponsor_politician_id}`}
                      className="text-indigo-300 hover:underline"
                    >
                      {data.sponsor_politician_name}
                    </Link>
                  ) : (
                    '—'
                  )}
                </div>
                <div>
                  <span className="text-slate-400">Last Updated:</span> {formatDate(data.updated_at)}
                </div>
              </div>

              <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-indigo-300">
                {data.source_openparliament && data.legisinfo_id ? (
                  <Link
                    href={`https://www.parl.ca/legisinfo/en/bill/${data.parliament}-${data.session}/${data.number}`}
                    target="_blank"
                    className="inline-flex items-center gap-1 hover:underline"
                  >
                    View on LEGISinfo <ExternalLink className="h-4 w-4" />
                  </Link>
                ) : null}
                {data.source_openparliament && (
                  <Link
                    href={`https://api.openparliament.ca/bills/${data.number}/`}
                    target="_blank"
                    className="inline-flex items-center gap-1 hover:underline"
                  >
                    OpenParliament <ExternalLink className="h-4 w-4" />
                  </Link>
                )}
              </div>
            </div>

            {data.legisinfo_summary_en && (
              <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-6">
                <h2 className="text-xl font-semibold text-slate-100 mb-3">Summary</h2>
                <p className="text-sm leading-relaxed text-slate-300">{data.legisinfo_summary_en}</p>
              </div>
            )}

            {data.subject_tags?.length ? (
              <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-6">
                <h2 className="text-xl font-semibold text-slate-100 mb-3">Subject Tags</h2>
                <div className="flex flex-wrap gap-2 text-xs">
                  {data.subject_tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-blue-500/10 px-3 py-1 text-blue-200">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
