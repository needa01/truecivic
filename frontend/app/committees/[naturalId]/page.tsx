'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeft, ExternalLink, Loader2 } from 'lucide-react';

import { apiClient, Committee, CommitteeMeeting, CommitteeMeetingList } from '@/lib/api-client';

const MEETINGS_PAGE_SIZE = 25;

function formatDate(value: string | null | undefined) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function display(value: string | null | undefined) {
  return value && value.trim() ? value : 'N/A';
}

export default function CommitteeDetailPage() {
  const params = useParams<{ naturalId: string }>();
  const router = useRouter();
  const naturalId = Array.isArray(params?.naturalId) ? params.naturalId[0] : params?.naturalId;

  const {
    data: committee,
    isLoading: committeeLoading,
    isError: committeeError,
  } = useQuery<Committee>({
    queryKey: ['committee', naturalId],
    queryFn: () => apiClient.getCommittee(naturalId!),
    enabled: Boolean(naturalId),
  });

  const {
    data: meetingsData,
    isLoading: meetingsLoading,
    isError: meetingsError,
  } = useQuery<CommitteeMeetingList>({
    queryKey: ['committee-meetings', naturalId, MEETINGS_PAGE_SIZE],
    queryFn: () =>
      apiClient.getCommitteeMeetings(naturalId!, {
        skip: 0,
        limit: MEETINGS_PAGE_SIZE,
      }),
    enabled: Boolean(naturalId),
  });

  const meetings = meetingsData?.meetings ?? [];
  const totalMeetings = meetingsData?.total ?? 0;
  const isLoading = committeeLoading || meetingsLoading;
  const hasError = committeeError || meetingsError;

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
            Invalid committee identifier.
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading committee...
          </div>
        ) : hasError || !committee ? (
          <div className="rounded-2xl border border-red-900/40 bg-red-900/10 p-6 text-red-200">
            Unable to load this committee. Verify committee data has been ingested.
          </div>
        ) : (
          <div className="space-y-8">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 backdrop-blur space-y-5">
              <p className="text-sm text-indigo-300 font-semibold">{committee.committee_slug}</p>
              <h1 className="text-3xl font-bold text-slate-100">
                {committee.name_en || committee.acronym_en || 'Parliamentary Committee'}
              </h1>
              {committee.name_fr && (
                <p className="text-sm text-slate-400 italic">{committee.name_fr}</p>
              )}

              <dl className="grid md:grid-cols-2 gap-4 text-sm text-slate-300">
                <div>
                  <dt className="text-slate-400">Parliament</dt>
                  <dd>{committee.parliament}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Session</dt>
                  <dd>{committee.session}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Chamber</dt>
                  <dd>{display(committee.chamber)}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Acronym</dt>
                  <dd>{display(committee.acronym_en || committee.acronym_fr)}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Parent Committee</dt>
                  <dd>{display(committee.parent_committee)}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Source</dt>
                  <dd>
                    {committee.source_url ? (
                      <Link
                        href={committee.source_url}
                        target="_blank"
                        className="inline-flex items-center gap-1 text-indigo-300 hover:underline"
                      >
                        OpenParliament
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    ) : (
                      'N/A'
                    )}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-900/30">
              <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
                <div>
                  <h2 className="text-xl font-semibold text-slate-100">Meetings</h2>
                  <p className="text-xs text-slate-400">
                    Showing {meetings.length} of {totalMeetings} stored meetings.
                  </p>
                </div>
              </div>

              {meetings.length ? (
                <div className="divide-y divide-slate-800/70">
                  {meetings.map((meeting: CommitteeMeeting) => (
                    <div key={meeting.id} className="px-6 py-5 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
                        <span>
                          Meeting {meeting.meeting_number} &middot; Parliament {meeting.parliament} / Session{' '}
                          {meeting.session}
                        </span>
                        <span>{formatDate(meeting.meeting_date)}</span>
                      </div>
                      <div>
                        <p className="text-base font-semibold text-slate-100">
                          {meeting.title_en || meeting.title_fr || `Committee Meeting ${meeting.meeting_number}`}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-400">
                          {meeting.meeting_type && <span>Type: {meeting.meeting_type}</span>}
                          {meeting.time_of_day && <span>Time: {meeting.time_of_day}</span>}
                          {meeting.room && <span>Room: {meeting.room}</span>}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                        <span>
                          Witnesses: {meeting.witnesses?.length ? meeting.witnesses.length : 0}
                        </span>
                        <span>
                          Documents: {meeting.documents?.length ? meeting.documents.length : 0}
                        </span>
                        {meeting.source_url && (
                          <Link
                            href={meeting.source_url}
                            target="_blank"
                            className="inline-flex items-center gap-1 text-indigo-300 hover:underline"
                          >
                            Source
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-6 py-10 text-sm text-slate-400">
                  No meetings stored for this committee yet.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
