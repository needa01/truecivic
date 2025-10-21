'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Loader2, Gavel } from 'lucide-react';
import Link from 'next/link';

export default function CommitteesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['committees', { limit: 50 }],
    queryFn: () => apiClient.getCommittees({ limit: 50 }),
  });

  return (
    <div className="min-h-screen bg-slate-950/40 text-slate-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="mb-10">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-indigo-500/10 p-2 text-indigo-300">
              <Gavel className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-semibold">Parliamentary Committees</h1>
              <p className="text-sm text-slate-400">
                Committee slugs now include jurisdiction prefixes for clarity across data products.
              </p>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading committees…
          </div>
        ) : isError ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Unable to load committees. Please verify the API is running and try again.
          </div>
        ) : !data?.committees?.length ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 text-slate-400">
            No committees found. Run the committee ingestion flow to populate this view.
          </div>
        ) : (
          <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/40 backdrop-blur">
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-900/60">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Slug
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Chamber
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Acronym
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {data.committees.map((committee) => (
                  <tr
                    key={committee.natural_id || committee.committee_slug}
                    className="hover:bg-slate-900/60 transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-indigo-200">
                      <Link
                        href={`/committees/${encodeURIComponent(
                          committee.natural_id || committee.committee_slug
                        )}`}
                        className="hover:underline"
                      >
                        {committee.committee_slug}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-200">
                      {committee.name_en || committee.acronym_en || 'Unknown'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300">{committee.chamber}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">
                      {committee.acronym_en || committee.acronym_fr || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-indigo-300">
                      {committee.source_url ? (
                        <Link href={committee.source_url} target="_blank" className="hover:underline">
                          OpenParliament
                        </Link>
                      ) : (
                        'OpenParliament'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
