'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeft, ExternalLink, Loader2 } from 'lucide-react';
import { apiClient, Politician, ApiClientError } from '@/lib/api-client';

function formatDate(value: string | null | undefined) {
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

export default function PoliticianDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const idParam = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const politicianId = Number(idParam);

  const { data, isLoading, isError, error } = useQuery<Politician, ApiClientError>({
    queryKey: ['politician', politicianId],
    queryFn: () => apiClient.getPoliticianById(politicianId),
    enabled: Number.isFinite(politicianId),
  });
  const errorMessage = error?.message ?? 'Ensure politicians have been ingested.';

  if (!Number.isFinite(politicianId)) {
    return (
      <div className="min-h-screen bg-slate-950/40 text-slate-100">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Invalid politician identifier provided.
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
            Loading politician…
          </div>
        ) : isError || !data ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            <p className="font-semibold">Unable to load this profile.</p>
            <p className="mt-2 text-sm text-red-100/80">{errorMessage}</p>
          </div>
        ) : (
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 backdrop-blur space-y-6">
            <div>
              <p className="text-sm text-purple-300 font-semibold mb-2">{data.politician_id}</p>
              <h1 className="text-3xl font-bold text-slate-100">{data.name}</h1>
              {data.given_name && data.family_name ? (
                <p className="text-sm text-slate-400">
                  {data.given_name} {data.family_name}
                </p>
              ) : null}
            </div>

            <dl className="grid sm:grid-cols-2 gap-3 text-sm text-slate-300">
              <div>
                <dt className="text-slate-400">Current Party</dt>
                <dd>{data.current_party || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Current Riding</dt>
                <dd>{data.current_riding || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Gender</dt>
                <dd>{data.gender || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Created</dt>
                <dd>{formatDate(data.created_at)}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Updated</dt>
                <dd>{formatDate(data.updated_at)}</dd>
              </div>
            </dl>

            <div className="flex flex-wrap gap-3 text-sm text-indigo-300">
              {data.source_url ? (
                <Link
                  href={data.source_url}
                  target="_blank"
                  className="inline-flex items-center gap-1 hover:underline"
                >
                  Source profile
                  <ExternalLink className="h-4 w-4" />
                </Link>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
