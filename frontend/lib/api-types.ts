/**
 * Shared API response types for the TrueCivic frontend.
 *
 * These interfaces mirror the FastAPI responses so the UI can rely on
 * predictable shapes without duplicating definitions across components.
 */

// MARK: Bills ---------------------------------------------------------------

export interface Bill {
  id: number;
  jurisdiction: string;
  parliament: number;
  session: number;
  number: string;
  title_en: string;
  title_fr: string | null;
  short_title_en: string | null;
  short_title_fr: string | null;
  sponsor_politician_id: number | null;
  sponsor_politician_name: string | null;
  introduced_date: string | null;
  law_status: string | null;
  royal_assent_date: string | null;
  royal_assent_chapter: string | null;
  legisinfo_id: number | null;
  legisinfo_status: string | null;
  legisinfo_summary_en: string | null;
  legisinfo_summary_fr: string | null;
  subject_tags: string[] | null;
  committee_studies: string[] | null;
  related_bill_numbers: string[] | null;
  source_openparliament: boolean;
  source_legisinfo: boolean;
  last_fetched_at: string;
  last_enriched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BillListResponse {
  bills: Bill[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// MARK: Politicians --------------------------------------------------------

export interface Politician {
  id: number;
  jurisdiction: string;
  politician_id: string;
  name: string;
  given_name: string | null;
  family_name: string | null;
  other_names: Record<string, unknown> | null;
  current_party: string | null;
  current_riding: string | null;
  gender: string | null;
  photo_url: string | null;
  memberships: Record<string, unknown>[] | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface PoliticianListResponse {
  politicians: Politician[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// MARK: Votes --------------------------------------------------------------

export interface VoteRecord {
  natural_id: string;
  jurisdiction: string;
  vote_id: string;
  politician_id: number;
  vote_position: string;
  created_at: string;
  updated_at: string;
}

export interface Vote {
  natural_id: string;
  jurisdiction: string;
  parliament: number;
  session: number;
  vote_number: number;
  chamber: string;
  vote_date: string | null;
  vote_description_en: string | null;
  vote_description_fr: string | null;
  bill_number: string | null;
  result: string;
  yeas: number;
  nays: number;
  abstentions: number;
  source_url: string | null;
  created_at: string;
  updated_at: string;
  vote_records?: VoteRecord[];
}

export interface VoteListResponse {
  votes: Vote[];
  total: number;
  skip: number;
  limit: number;
}

// MARK: Debates ------------------------------------------------------------

export interface Speech {
  natural_id: string;
  jurisdiction: string;
  debate_id: string;
  politician_id: number | null;
  content_en: string | null;
  content_fr: string | null;
  speech_time: string | null;
  speaker_name: string | null;
  speaker_display_name: string | null;
  speaker_role: string | null;
  sequence: number;
  created_at: string;
  updated_at: string;
}

export interface Debate {
  natural_id: string;
  jurisdiction: string;
  parliament: number;
  session: number;
  debate_number: string;
  chamber: string;
  debate_date: string | null;
  topic_en: string | null;
  topic_fr: string | null;
  debate_type: string;
  source_url: string | null;
  created_at: string;
  updated_at: string;
  speeches?: Speech[];
}

export interface DebateListResponse {
  debates: Debate[];
  total: number;
  skip: number;
  limit: number;
}

// MARK: Committees ---------------------------------------------------------

export interface Committee {
  natural_id: string;
  jurisdiction: string;
  parliament: number;
  session: number;
  committee_slug: string;
  acronym_en: string | null;
  acronym_fr: string | null;
  name_en: string | null;
  name_fr: string | null;
  short_name_en: string | null;
  short_name_fr: string | null;
  chamber: string;
  parent_committee: string | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommitteeList {
  committees: Committee[];
  total: number;
  skip: number;
  limit: number;
}

export interface CommitteeMeeting {
  id: number;
  committee_id: number;
  committee_slug: string;
  meeting_number: number;
  parliament: number;
  session: number;
  meeting_date: string;
  time_of_day: string | null;
  title_en: string | null;
  title_fr: string | null;
  meeting_type: string | null;
  room: string | null;
  witnesses: Record<string, unknown>[] | null;
  documents: Record<string, unknown>[] | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommitteeMeetingList {
  committee: Committee;
  meetings: CommitteeMeeting[];
  total: number;
  skip: number;
  limit: number;
}

// MARK: Overview -----------------------------------------------------------

export interface OverviewStats {
  bills: number;
  politicians: number;
  votes: number;
  debates: number;
  committees: number;
  generated_at: string;
}
