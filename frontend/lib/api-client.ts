/**
 * API Client for TrueCivic.
 *
 * Uses NEXT_PUBLIC_API_URL to build requests against the FastAPI backend.
 * All helpers return the exact response shape produced by the API so the
 * frontend can consume metadata like `has_more`, `limit`, and `offset`.
 */

const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/ca';
const API_BASE_URL = rawBaseUrl.replace(/\/$/, '');

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

export interface Speech {
  natural_id: string;
  jurisdiction: string;
  debate_id: string;
  politician_id: number | null;
  content_en: string | null;
  content_fr: string | null;
  speech_time: string | null;
  speaker_name: string | null;
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

type RequestOptions = RequestInit & { signal?: AbortSignal };

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.info('🔗 API Client base URL:', this.baseUrl);
    }
  }

  private async request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return (await response.json()) as T;
  }

  // Bills --------------------------------------------------------------------
  async getBills(params?: {
    parliament?: number;
    session?: number;
    limit?: number;
    offset?: number;
    sort?: string;
    order?: 'asc' | 'desc';
  }): Promise<BillListResponse> {
    const query = new URLSearchParams();
    query.set('limit', String(params?.limit ?? 50));
    query.set('offset', String(params?.offset ?? 0));
    if (params?.parliament) query.set('parliament', String(params.parliament));
    if (params?.session) query.set('session', String(params.session));
    if (params?.sort) query.set('sort', params.sort);
    if (params?.order) query.set('order', params.order);

    const qs = query.toString();
    return this.request<BillListResponse>(`/bills${qs ? `?${qs}` : ''}`);
  }

  async getBillById(id: number): Promise<Bill> {
    return this.request<Bill>(`/bills/${id}`);
  }

  async searchBills(queryText: string, limit = 20, offset = 0): Promise<BillListResponse> {
    const query = new URLSearchParams({
      q: queryText,
      limit: String(limit),
      offset: String(offset),
    });
    return this.request<BillListResponse>(`/bills/search?${query.toString()}`);
  }

  // Politicians --------------------------------------------------------------
  async getPoliticians(params?: {
    party?: string;
    riding?: string;
    currentOnly?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<PoliticianListResponse> {
    const query = new URLSearchParams();
    query.set('limit', String(params?.limit ?? 50));
    query.set('offset', String(params?.offset ?? 0));
    if (params?.party) query.set('party', params.party);
    if (params?.riding) query.set('riding', params.riding);
    if (params?.currentOnly ?? true) query.set('current_only', 'true');
    const qs = query.toString();
    return this.request<PoliticianListResponse>(`/politicians${qs ? `?${qs}` : ''}`);
  }

  async getPoliticianById(id: number): Promise<Politician> {
    return this.request<Politician>(`/politicians/${id}`);
  }

  // Votes --------------------------------------------------------------------
  async getVotes(params?: {
    parliament?: number;
    session?: number;
    limit?: number;
    skip?: number;
  }): Promise<VoteListResponse> {
    const query = new URLSearchParams();
    query.set('limit', String(params?.limit ?? 100));
    query.set('skip', String(params?.skip ?? 0));
    if (params?.parliament) query.set('parliament', String(params.parliament));
    if (params?.session) query.set('session', String(params.session));
    const qs = query.toString();
    return this.request<VoteListResponse>(`/votes${qs ? `?${qs}` : ''}`);
  }

  async getVoteById(naturalId: string, options?: { includeRecords?: boolean }): Promise<Vote> {
    const query = new URLSearchParams();
    if (options?.includeRecords) query.set('include_records', 'true');
    const qs = query.toString();
    return this.request<Vote>(`/votes/${encodeURIComponent(naturalId)}${qs ? `?${qs}` : ''}`);
  }

  async getVoteRecords(naturalId: string, params?: { position?: string; skip?: number; limit?: number }) {
    const query = new URLSearchParams();
    if (params?.position) query.set('position', params.position);
    if (typeof params?.skip === 'number') query.set('skip', String(params.skip));
    if (typeof params?.limit === 'number') query.set('limit', String(params.limit));
    const qs = query.toString();
    return this.request<VoteRecord[]>(
      `/votes/${encodeURIComponent(naturalId)}/records${qs ? `?${qs}` : ''}`
    );
  }

  // Debates ------------------------------------------------------------------
  async getDebates(params?: {
    parliament?: number;
    session?: number;
    limit?: number;
    skip?: number;
  }): Promise<DebateListResponse> {
    const query = new URLSearchParams();
    query.set('limit', String(params?.limit ?? 100));
    query.set('skip', String(params?.skip ?? 0));
    if (params?.parliament) query.set('parliament', String(params.parliament));
    if (params?.session) query.set('session', String(params.session));
    const qs = query.toString();
    return this.request<DebateListResponse>(`/debates${qs ? `?${qs}` : ''}`);
  }

  async getDebateById(naturalId: string, options?: { includeSpeeches?: boolean }): Promise<Debate> {
    const query = new URLSearchParams();
    if (options?.includeSpeeches) query.set('include_speeches', 'true');
    const qs = query.toString();
    return this.request<Debate>(`/debates/${encodeURIComponent(naturalId)}${qs ? `?${qs}` : ''}`);
  }

  async getDebateSpeeches(naturalId: string, params?: { skip?: number; limit?: number; politicianId?: number }) {
    const query = new URLSearchParams();
    if (typeof params?.skip === 'number') query.set('skip', String(params.skip));
    if (typeof params?.limit === 'number') query.set('limit', String(params.limit));
    if (typeof params?.politicianId === 'number') query.set('politician_id', String(params.politicianId));
    const qs = query.toString();
    return this.request<Speech[]>(
      `/debates/${encodeURIComponent(naturalId)}/speeches${qs ? `?${qs}` : ''}`
    );
  }

  // Committees ---------------------------------------------------------------
  async getCommittees(params?: {
    parliament?: number;
    session?: number;
    chamber?: string;
    slug?: string;
    skip?: number;
    limit?: number;
  }): Promise<CommitteeList> {
    const query = new URLSearchParams();
    query.set('limit', String(params?.limit ?? 50));
    query.set('skip', String(params?.skip ?? 0));
    if (params?.parliament) query.set('parliament', String(params.parliament));
    if (params?.session) query.set('session', String(params.session));
    if (params?.chamber) query.set('chamber', params.chamber);
    if (params?.slug) query.set('slug', params.slug);
    const qs = query.toString();
    return this.request<CommitteeList>(`/committees${qs ? `?${qs}` : ''}`);
  }

  async getCommittee(naturalId: string): Promise<Committee> {
    return this.request<Committee>(`/committees/${encodeURIComponent(naturalId)}`);
  }

  async getCommitteeMeetings(
    naturalId: string,
    params?: { skip?: number; limit?: number }
  ): Promise<CommitteeMeetingList> {
    const query = new URLSearchParams();
    if (typeof params?.skip === 'number') query.set('skip', String(params.skip));
    if (typeof params?.limit === 'number') query.set('limit', String(params.limit));
    const qs = query.toString();
    return this.request<CommitteeMeetingList>(
      `/committees/${encodeURIComponent(naturalId)}/meetings${qs ? `?${qs}` : ''}`
    );
  }
}

export const apiClient = new ApiClient();
export default apiClient;
