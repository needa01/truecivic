/**
 * API Client for TrueCivic - automatically detects environment
 * Uses NEXT_PUBLIC_API_URL from .env.local (localhost) or production
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/ca';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

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
  sponsor_politician_id: string | null;
  sponsor_politician_name: string | null;
  introduced_date: string | null;
  law_status: string | null;
  legisinfo_id: string | null;
  legisinfo_status: string | null;
  legisinfo_summary_en: string | null;
  legisinfo_summary_fr: string | null;
  subject_tags: string[] | null;
  committee_studies: string[] | null;
  royal_assent_date: string | null;
  royal_assent_chapter: string | null;
  related_bill_numbers: string[] | null;
  source_openparliament: boolean;
  source_legisinfo: boolean;
  last_fetched_at: string;
  last_enriched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Politician {
  id: number;
  openparliament_url: string;
  name: string;
  party: string | null;
  riding: string | null;
  province: string | null;
  current_member: boolean;
  start_date: string | null;
  end_date: string | null;
  image_url: string | null;
  email: string | null;
  phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface Vote {
  id: number;
  vote_number: number;
  parliament: number;
  session: number;
  date: string;
  result: string;
  yea_count: number;
  nay_count: number;
  paired_count: number;
  bill_id: number | null;
  description_en: string | null;
  description_fr: string | null;
  created_at: string;
  updated_at: string;
}

export interface Debate {
  id: number;
  date: string;
  house: string;
  number: number;
  parliament: number;
  session: number;
  created_at: string;
  updated_at: string;
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

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    console.log('🔗 API Client initialized:', this.baseUrl);
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${url}`, error);
      throw error;
    }
  }

  // Bills
  async getBills(params?: {
    parliament?: number;
    session?: number;
    page?: number;
    size?: number;
    sort?: string;
  }): Promise<PaginatedResponse<Bill>> {
    const query = new URLSearchParams();
    if (params?.parliament) query.set('parliament', params.parliament.toString());
    if (params?.session) query.set('session', params.session.toString());
    if (params?.page) query.set('page', params.page.toString());
    if (params?.size) query.set('size', params.size.toString());
    if (params?.sort) query.set('sort', params.sort);
    
    return this.request<PaginatedResponse<Bill>>(`/bills?${query.toString()}`);
  }

  async getBillById(id: number): Promise<Bill> {
    return this.request<Bill>(`/bills/${id}`);
  }

  async searchBills(query: string, page: number = 1, size: number = 20): Promise<PaginatedResponse<Bill>> {
    const params = new URLSearchParams({ q: query, page: page.toString(), size: size.toString() });
    return this.request<PaginatedResponse<Bill>>(`/bills/search?${params.toString()}`);
  }

  // Politicians
  async getPoliticians(params?: {
    riding?: string;
    party?: string;
    current_only?: boolean;
    page?: number;
    size?: number;
  }): Promise<PaginatedResponse<Politician>> {
    const query = new URLSearchParams();
    if (params?.riding) query.set('riding', params.riding);
    if (params?.party) query.set('party', params.party);
    if (params?.current_only) query.set('current_only', 'true');
    if (params?.page) query.set('page', params.page.toString());
    if (params?.size) query.set('size', params.size.toString());
    
    return this.request<PaginatedResponse<Politician>>(`/politicians?${query.toString()}`);
  }

  async getPoliticianById(id: number): Promise<Politician> {
    return this.request<Politician>(`/politicians/${id}`);
  }

  // Votes
  async getVotes(params?: {
    parliament?: number;
    session?: number;
    page?: number;
    size?: number;
  }): Promise<PaginatedResponse<Vote>> {
    const query = new URLSearchParams();
    if (params?.parliament) query.set('parliament', params.parliament.toString());
    if (params?.session) query.set('session', params.session.toString());
    if (params?.page) query.set('page', params.page.toString());
    if (params?.size) query.set('size', params.size.toString());
    
    return this.request<PaginatedResponse<Vote>>(`/votes?${query.toString()}`);
  }

  async getVoteById(id: number): Promise<Vote> {
    return this.request<Vote>(`/votes/${id}`);
  }

  // Debates
  async getDebates(params?: {
    parliament?: number;
    session?: number;
    page?: number;
    size?: number;
  }): Promise<PaginatedResponse<Debate>> {
    const query = new URLSearchParams();
    if (params?.parliament) query.set('parliament', params.parliament.toString());
    if (params?.session) query.set('session', params.session.toString());
    if (params?.page) query.set('page', params.page.toString());
    if (params?.size) query.set('size', params.size.toString());
    
    return this.request<PaginatedResponse<Debate>>(`/debates?${query.toString()}`);
  }

  async getDebateById(id: number): Promise<Debate> {
    return this.request<Debate>(`/debates/${id}`);
  }

  // Committees
  async getCommittees(params?: {
    parliament?: number;
    session?: number;
    chamber?: string;
    slug?: string;
    skip?: number;
    limit?: number;
  }): Promise<CommitteeList> {
    const query = new URLSearchParams();
    if (params?.parliament) query.set('parliament', params.parliament.toString());
    if (params?.session) query.set('session', params.session.toString());
    if (params?.chamber) query.set('chamber', params.chamber);
    if (params?.slug) query.set('slug', params.slug);
    if (typeof params?.skip === 'number') query.set('skip', params.skip.toString());
    if (typeof params?.limit === 'number') query.set('limit', params.limit.toString());

    const queryString = query.toString();
    const endpoint = queryString ? `/committees?${queryString}` : `/committees`;
    return this.request<CommitteeList>(endpoint);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
