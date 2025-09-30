/**
 * Dynamic Account Discovery Service
 * Fetches real-time account data from MCP tools instead of hardcoded mappings
 */
import { apiFetch } from '../utils/api'

export interface RawGoogleAdsAccount {
  customer_id: string
  resource_name: string
  descriptive_name: string
  error?: string
}

export interface RawGA4Property {
  property_id: string
  display_name: string
  name: string
  currency_code: string
  time_zone: string
  account_id: string
  account_display_name: string
}

export interface GoogleAdsAccount {
  id: string
  name: string
  customer_id: string
  display_name: string
  raw_data: RawGoogleAdsAccount
  hasMatchingGA4?: boolean // Indicates if user has GA4 for same business
}

export interface GA4Account {
  id: string
  name: string
  property_id: string
  display_name: string
  raw_data: RawGA4Property
  hasMatchingAds?: boolean // Indicates if user has Google Ads for same business
}

export interface CombinedAccount {
  id: string
  name: string
  google_ads_id: string
  ga4_property_id: string
  display_name: string
  ads_data: RawGoogleAdsAccount
  ga4_data: RawGA4Property
}

export interface AccountMappingRecord {
  id: number
  account_id: string
  account_name: string
  google_ads_id: string
  ga4_property_id: string
  business_type: string
  is_active: boolean
  sort_order: number
}

export interface AccountCollections {
  googleAds: GoogleAdsAccount[]
  ga4: GA4Account[]
  combined: CombinedAccount[]
}

class AccountService {
  private cachedCollections: AccountCollections | null = null
  private lastFetchTime: number = 0
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  /**
   * Get all account collections for the authenticated user
   * Returns separate Google Ads, GA4, and Combined collections
   */
  async getAccountCollections(): Promise<AccountCollections> {
    // Return cached data if still valid
    if (this.cachedCollections && (Date.now() - this.lastFetchTime) < this.CACHE_DURATION) {
      return this.cachedCollections
    }

    try {
      
      // Get authenticated user's accounts via MCP tools
      const [googleAdsResponse, ga4Response] = await Promise.all([
        this.fetchGoogleAdsAccounts(),
        this.fetchGA4Properties()
      ])

      const googleAdsAccounts: RawGoogleAdsAccount[] = googleAdsResponse.accounts || []
      const ga4Properties: RawGA4Property[] = ga4Response.properties || []


      // Build separate collections
      const collections = await this.buildAccountCollections(googleAdsAccounts, ga4Properties)
      
      // Cache results
      this.cachedCollections = collections
      this.lastFetchTime = Date.now()
      
      return collections
    } catch (error) {
      console.error('❌ Failed to fetch account collections:', error)
      // Return empty collections instead of fallback
      return {
        googleAds: [],
        ga4: [],
        combined: []
      }
    }
  }

  /**
   * Fetch Google Ads accounts using MCP tool
   */
  private async fetchGoogleAdsAccounts(): Promise<any> {
    
    const response = await apiFetch('/api/mcp/google-ads-accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool: 'get_google_ads_accounts',
        // user_id will be determined by backend session
      })
    })
    
    
    if (!response.ok) {
      console.error('❌ [AccountService] Google Ads fetch failed:', response.status, response.statusText)
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    
    return result
  }

  /**
   * Fetch GA4 properties using MCP tool
   */
  private async fetchGA4Properties(): Promise<any> {
    
    const response = await apiFetch('/api/mcp/ga4-properties', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool: 'get_ga4_properties',
        // user_id will be determined by backend session
      })
    })
    
    
    if (!response.ok) {
      console.error('❌ [AccountService] GA4 fetch failed:', response.status, response.statusText)
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    
    return result
  }

  /**
   * Build separate account collections with intelligent business matching
   */
  private async buildAccountCollections(
    googleAdsAccounts: RawGoogleAdsAccount[],
    ga4Properties: RawGA4Property[]
  ): Promise<AccountCollections> {
    // Create business mapping from GA4 (source of truth for business names)
    const businessMap = await this.createBusinessMap(googleAdsAccounts, ga4Properties)
    
    // Smart categorization based on business mapping
    const googleAdsOnly: GoogleAdsAccount[] = []
    const ga4Only: GA4Account[] = []
    const combined: CombinedAccount[] = []
    
    // Process each business from the mapping
    businessMap.forEach((businessData, businessName) => {
      const { adsAccount, ga4Properties: businessGA4Properties, websiteGA4Map, primaryWebsite } = businessData
      
      if (adsAccount && businessGA4Properties.length > 0) {
        // Special handling for agency accounts (11&1 Accounts)
        if (businessName === '11&1 Accounts') {
          // Agency account: Create individual combined accounts for each website that has clear URL
          businessGA4Properties.forEach(property => {
            const domain = this.extractDomain(property.display_name)
            if (domain) {
              // Create combined account for each website the agency manages
              combined.push({
                id: `combined_${adsAccount.customer_id}_${property.property_id}`,
                name: `${domain} (via 11&1 Ads)`,
                google_ads_id: adsAccount.customer_id,
                ga4_property_id: property.property_id,
                display_name: `${property.display_name} + 11&1 Google Ads`,
                ads_data: adsAccount,
                ga4_data: property
              })
            } else {
              // No clear domain - put in GA4-only
              ga4Only.push({
                id: `ga4_${property.property_id}`,
                name: property.display_name,
                property_id: property.property_id,
                display_name: property.display_name,
                raw_data: property,
                hasMatchingAds: true
              })
            }
          })
        } else {
          // Regular business: Use primary GA4 property + put rest in GA4-only
          let primaryGA4
          
          if (primaryWebsite && websiteGA4Map?.has(primaryWebsite)) {
            // Use the specified primary website
            primaryGA4 = websiteGA4Map.get(primaryWebsite)
          } else {
            // Fall back to best name match
            primaryGA4 = businessGA4Properties.find(p => 
              p.display_name.toLowerCase().includes(businessName.toLowerCase().split(' ')[0]) ||
              p.display_name.toLowerCase().includes('ga4')
            ) || businessGA4Properties[0]
          }
          
          // Create combined account with primary GA4
          combined.push({
            id: `combined_${adsAccount.customer_id}_${primaryGA4.property_id}`,
            name: businessName,
            google_ads_id: adsAccount.customer_id,
            ga4_property_id: primaryGA4.property_id,
            display_name: businessName,
            ads_data: adsAccount,
            ga4_data: primaryGA4
          })
          
          // Put remaining GA4 properties in GA4-only tab
          businessGA4Properties.forEach(property => {
            if (property.property_id !== primaryGA4.property_id) {
              ga4Only.push({
                id: `ga4_${property.property_id}`,
                name: property.display_name,
                property_id: property.property_id,
                display_name: property.display_name,
                raw_data: property,
                hasMatchingAds: true
              })
            }
          })
        }
      } else if (adsAccount && businessGA4Properties.length === 0) {
        // Business has only Google Ads → Ads-only tab
        googleAdsOnly.push({
          id: `ads_${adsAccount.customer_id}`,
          name: businessName,
          customer_id: adsAccount.customer_id,
          display_name: businessName,
          raw_data: adsAccount,
          hasMatchingGA4: false
        })
      } else if (!adsAccount && businessGA4Properties.length > 0) {
        // Business has only GA4 → GA4-only tab
        businessGA4Properties.forEach(property => {
          ga4Only.push({
            id: `ga4_${property.property_id}`,
            name: property.display_name,
            property_id: property.property_id,
            display_name: property.display_name,
            raw_data: property,
            hasMatchingAds: false
          })
        })
      }
    })
    
    // Handle unmatched Google Ads accounts (get mappings from API)
    const accountMappings = await this.getAccountMappingsFromAPI()
    const knownAdIds = new Set(accountMappings.map(mapping => mapping.google_ads_id))

    googleAdsAccounts.forEach(account => {
      if (!knownAdIds.has(account.customer_id)) {
        googleAdsOnly.push({
          id: `ads_${account.customer_id}`,
          name: this.cleanBusinessName(account.descriptive_name),
          customer_id: account.customer_id,
          display_name: this.cleanBusinessName(account.descriptive_name),
          raw_data: account,
          hasMatchingGA4: false
        })
      }
    })

    return { 
      googleAds: googleAdsOnly.sort((a, b) => a.name.localeCompare(b.name)), 
      ga4: ga4Only.sort((a, b) => a.name.localeCompare(b.name)), 
      combined: combined.sort((a, b) => a.name.localeCompare(b.name))
    }
  }

  /**
   * Extract domain from GA4 display name or return null
   */
  private extractDomain(displayName: string): string | null {
    // Match URLs like "https://petspreference.co.za/" or "goodbyeboring.co.za"
    const urlMatch = displayName.match(/https?:\/\/([^\/\s]+)|([a-zA-Z0-9-]+\.(?:co\.za|com|org|net|co\.uk))/i)
    if (urlMatch) {
      return urlMatch[1] || urlMatch[2]
    }
    return null
  }

  /**
   * Fetch account mappings from the API instead of using hardcoded values
   */
  private async getAccountMappingsFromAPI(): Promise<AccountMappingRecord[]> {
    try {
      const response = await apiFetch('/api/accounts/available')
      if (!response.ok) {
        console.warn('[ACCOUNT-SERVICE] Failed to fetch account mappings, using empty array')
        return []
      }
      const data = await response.json()
      return data.accounts || []
    } catch (error) {
      console.warn('[ACCOUNT-SERVICE] Error fetching account mappings:', error)
      return []
    }
  }

  /**
   * Create intelligent business mapping with URL-based matching
   */
  private async createBusinessMap(googleAdsAccounts: RawGoogleAdsAccount[], ga4Properties: RawGA4Property[]): Promise<Map<string, {adsAccount?: RawGoogleAdsAccount, ga4Properties: RawGA4Property[], websiteGA4Map?: Map<string, RawGA4Property>}>> {
    const businessMap = new Map()
    
    // Group GA4 properties by business AND create website mapping
    ga4Properties.forEach(property => {
      const businessName = property.account_display_name
      if (!businessMap.has(businessName)) {
        businessMap.set(businessName, { ga4Properties: [], websiteGA4Map: new Map() })
      }
      const business = businessMap.get(businessName)
      business.ga4Properties.push(property)
      
      // Map websites to GA4 properties for URL-based matching
      const domain = this.extractDomain(property.display_name)
      if (domain) {
        business.websiteGA4Map.set(domain, property)
      }
    })
    
    // Enhanced Google Ads mapping using API account mappings
    const accountMappings = await this.getAccountMappingsFromAPI()

    googleAdsAccounts.forEach(adsAccount => {
      const mapping = accountMappings.find(m => m.google_ads_id === adsAccount.customer_id)
      if (mapping) {
        const businessName = mapping.account_name
        if (businessMap.has(businessName)) {
          businessMap.get(businessName).adsAccount = adsAccount
          // TODO: Add primary website support if needed
        }
      }
    })
    
    return businessMap
  }

  /**
   * Check if Google Ads account has matching GA4 (for visual indicator)
   */
  private hasMatchingGA4(adsAccount: RawGoogleAdsAccount, ga4Properties: RawGA4Property[]): boolean {
    return ga4Properties.some(prop => 
      this.isBusinessMatch(adsAccount.descriptive_name, prop.account_display_name)
    )
  }

  /**
   * Check if GA4 property has matching Google Ads (for visual indicator)  
   */
  private hasMatchingAds(ga4Property: RawGA4Property, googleAdsAccounts: RawGoogleAdsAccount[]): boolean {
    return googleAdsAccounts.some(ads => 
      this.isBusinessMatch(ads.descriptive_name, ga4Property.account_display_name)
    )
  }

  /**
   * Check if business names match (fuzzy matching for indicators)
   */
  private isBusinessMatch(adsName: string, ga4AccountName: string): boolean {
    const normalize = (str: string) => str.toLowerCase()
      .replace(/[^a-z0-9]/g, '')
      .replace(/account|ltd|llc|inc|co\.|limited/g, '')

    const normalizedAds = normalize(adsName)
    const normalizedGA4 = normalize(ga4AccountName)

    // Check for exact match or contains
    return normalizedAds === normalizedGA4 || 
           normalizedAds.includes(normalizedGA4) ||
           normalizedGA4.includes(normalizedAds)
  }

  /**
   * Clean business name for display
   */
  private cleanBusinessName(name: string): string {
    const cleaned = name
      .replace(/^Account\s+/i, '')
      .replace(/\s+-\s+GA4?$/, '')
      .trim()
    
    // If we only have a customer ID (due to API errors), make it more friendly
    if (/^\d+$/.test(cleaned)) {
      return `Google Ads Account ${cleaned.slice(-4)}` // Show last 4 digits
    }
    
    return cleaned
  }

  /**
   * Clear cache (useful after re-authentication)
   */
  clearCache(): void {
    this.cachedCollections = null
    this.lastFetchTime = 0
  }
}

export const accountService = new AccountService()
export default accountService