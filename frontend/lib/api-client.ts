/**
 * API Client for TrueCivic.
 *
 * Resolves the base URL using NEXT_PUBLIC_API_URL, cloud/local fallbacks,
 * and provides strongly typed helpers for interacting with the backend.
 * All helpers return the exact response shape produced by the API so the
 * frontend can consume metadata like `has_more`, `limit`, and `offset`.
 */

import type {
  Bill,
  BillListResponse,
  Committee,
  CommitteeList,
  CommitteeMeeting,
  CommitteeMeetingList,
  Debate,
  DebateListResponse,
  OverviewStats,
  Politician,
  PoliticianListResponse,
  Speech,
  Vote,
  VoteListResponse,
  VoteRecord,
} from './api-types';

export type {
  Bill,
  BillListResponse,
  Committee,
  CommitteeList,
  CommitteeMeeting,
  CommitteeMeetingList,
  Debate,
  DebateListResponse,
  OverviewStats,
  Politician,
  PoliticianListResponse,
  Speech,
  Vote,
  VoteListResponse,
  VoteRecord,
};

// MARK: Client configuration -------------------------------------------------

const preferCloud = process.env.NEXT_PUBLIC_USE_CLOUD_API === 'true';
const localBaseUrl = (process.env.NEXT_PUBLIC_LOCAL_API_URL || 'http://localhost:8000/api/v1/ca').trim();
const cloudBaseUrl = (process.env.NEXT_PUBLIC_CLOUD_API_URL || '').trim();
const useCloudBase = preferCloud && Boolean(cloudBaseUrl);

const rawBaseUrl =
  (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim()) ||
  (useCloudBase ? cloudBaseUrl : localBaseUrl);

const API_BASE_URL = rawBaseUrl.replace(/\/$/, '');
const resolvedMode = useCloudBase ? 'cloud' : 'local';

const DEFAULT_API_KEY =
  (useCloudBase && process.env.NEXT_PUBLIC_CLOUD_API_KEY?.trim()) ||
  process.env.NEXT_PUBLIC_API_KEY?.trim() ||
  null;

// MARK: Error handling -------------------------------------------------------

export interface ApiClientErrorParams {
  status: number;
  statusText: string;
  detail?: string;
  body: unknown;
  headers: Headers;
}

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly statusText: string;
  public readonly detail?: string;
  public readonly body: unknown;
  public readonly headers: Record<string, string>;

  constructor(message: string, params: ApiClientErrorParams) {
    super(message);
    this.name = 'ApiClientError';
    this.status = params.status;
    this.statusText = params.statusText;
    this.detail = params.detail;
    this.body = params.body;
    this.headers = {};

    params.headers.forEach((value, key) => {
      this.headers[key.toLowerCase()] = value;
    });
  }

  get rateLimitLimit(): string | undefined {
    return this.headers['x-ratelimit-limit'];
  }
}

type RequestOptions = RequestInit & { signal?: AbortSignal };

class ApiClient {
  private baseUrl: string;
  private apiKey: string | null;

  constructor(baseUrl: string = API_BASE_URL, apiKey: string | null = DEFAULT_API_KEY) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey?.trim() || null;
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.info('🔗 API Client base URL:', this.baseUrl);
      // eslint-disable-next-line no-console
      console.info('☁️  API mode:', resolvedMode);
      if (!this.apiKey) {
        // eslint-disable-next-line no-console
        console.warn(
          '⚠️  API client is running without an API key. Set NEXT_PUBLIC_API_KEY or NEXT_PUBLIC_CLOUD_API_KEY to avoid 401 responses.'
        );
      }
    }
  }

  setApiKey(apiKey: string | null | undefined) {
    this.apiKey = apiKey?.trim() || null;
  }

  getApiKey(): string | null {
    return this.apiKey;
  }

  private buildHeaders(existing?: HeadersInit): Headers {
    const headers = new Headers();
    headers.set('Content-Type', 'application/json');

    if (existing) {
      const incoming = new Headers(existing);
      incoming.forEach((value, key) => {
        headers.set(key, value);
      });
    }

    if (this.apiKey) {
      headers.set('X-API-Key', this.apiKey);
    }

    return headers;
  }

  private async request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...(options ?? {}),
      headers: this.buildHeaders(options?.headers),
    });

    const contentType = response.headers.get('content-type') ?? '';
    const isJson = contentType.includes('application/json');
    const payload = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      let detail: string | undefined;

      if (typeof payload === 'object' && payload !== null) {
        const payloadDetail = (payload as Record<string, unknown>).detail;
        if (typeof payloadDetail === 'string') {
          detail = payloadDetail;
        }
      } else if (typeof payload === 'string' && payload.trim()) {
        detail = payload.trim();
      }

      let message = detail || `API Error: ${response.status} ${response.statusText}`;
      if (response.status === 401) {
        if (this.apiKey) {
          message = detail || 'Authentication failed. Verify the configured API key.';
        } else {
          message =
            'Authentication required. Set NEXT_PUBLIC_API_KEY in your frontend environment before retrying.';
        }
      } else if (response.status === 429) {
        const retryAfter = response.headers.get('retry-after');
        const retryMessage = retryAfter ? ` Retry after ${retryAfter} seconds.` : '';
        message = detail || `Rate limit exceeded.${retryMessage}`;
      }

      throw new ApiClientError(message, {
        status: response.status,
        statusText: response.statusText,
        detail,
        body: payload,
        headers: response.headers,
      });
    }

    return payload as T;
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

  // Overview ---------------------------------------------------------------
  async getOverviewStats(): Promise<OverviewStats> {
    return this.request<OverviewStats>('/overview/stats');
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
