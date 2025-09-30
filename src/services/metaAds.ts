const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'

interface MetaAdsAccount {
  id: string
  name: string
  account_id: string
  currency: string
  timezone_name: string
  account_status: number
}

interface CampaignMetrics {
  impressions: number
  clicks: number
  spend: number
  reach: number
  frequency: number
  ctr: number
  cpc: number
  cpm: number
  cpp: number
  actions?: Array<{ action_type: string; value: string }>
}

interface MetaCampaign {
  id: string
  name: string
  status: string
  objective: string
  daily_budget?: number
  lifetime_budget?: number
  metrics?: CampaignMetrics
}

class MetaAdsService {
  async getAccounts(): Promise<MetaAdsAccount[]> {
    return this.getAdAccounts()
  }

  async getAdAccounts(): Promise<MetaAdsAccount[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/oauth/meta/accounts`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionStorage.getItem('session_id') || ''
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch Meta ad accounts: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching Meta ad accounts:', error)
      throw new Error('Failed to fetch Meta Ads accounts')
    }
  }

  async getCampaigns(accountId: string, includeMetrics: boolean = true): Promise<MetaCampaign[]> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/oauth/meta/accounts/${accountId}/campaigns`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionStorage.getItem('session_id') || ''
          }
        }
      )

      const searchParams = new URLSearchParams()
      if (includeMetrics) {
        searchParams.append('include_metrics', 'true')
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch Meta campaigns: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching Meta campaigns:', error)
      throw new Error('Failed to fetch campaigns')
    }
  }

  async getAccountPerformanceMetrics(
    accountId: string,
    startDate: string,
    endDate: string
  ): Promise<CampaignMetrics> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/oauth/meta/accounts/${accountId}/performance?start_date=${startDate}&end_date=${endDate}`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionStorage.getItem('session_id') || ''
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch Meta account performance metrics: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching Meta account performance metrics:', error)
      throw new Error('Failed to fetch performance metrics')
    }
  }

  async getAdSets(accountId: string, campaignId?: string): Promise<Array<{ id: string; name: string; status: string }>> {
    try {
      const searchParams = new URLSearchParams()
      if (campaignId) {
        searchParams.append('campaign_id', campaignId)
      }

      const response = await fetch(
        `${API_BASE_URL}/api/oauth/meta/accounts/${accountId}/adsets?${searchParams}`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionStorage.getItem('session_id') || ''
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch Meta ad sets: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching Meta ad sets:', error)
      throw new Error('Failed to fetch ad sets')
    }
  }

  async getAds(accountId: string, adSetId?: string): Promise<Array<{ id: string; name: string; status: string }>> {
    try {
      const searchParams = new URLSearchParams()
      if (adSetId) {
        searchParams.append('adset_id', adSetId)
      }

      const response = await fetch(
        `${API_BASE_URL}/api/oauth/meta/accounts/${accountId}/ads?${searchParams}`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionStorage.getItem('session_id') || ''
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch Meta ads: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching Meta ads:', error)
      throw new Error('Failed to fetch ads')
    }
  }
}

export const metaAdsService = new MetaAdsService()
export const metaAds = metaAdsService
export type { MetaAdsAccount, MetaCampaign, CampaignMetrics }