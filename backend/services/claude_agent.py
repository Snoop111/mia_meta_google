"""
Claude Intent Analysis Agent
Simple agent that uses Claude API to analyze user intent for marketing queries
"""
import os
import json
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

class ClaudeIntentAgent:
    """
    Simple Claude agent for marketing query intent analysis
    """
    
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-haiku-20240307"  # Fast, cheap model for intent analysis
        
    async def analyze_intent(self, user_question: str, account_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze user intent for marketing queries using Claude API
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "ANTHROPIC_API_KEY not found",
                "fallback_to_existing": True
            }
        
        try:
            # Build context prompt
            context_info = ""
            if account_context:
                account_id = account_context.get('focus_account', 'Unknown')
                date_range = f"{account_context.get('start_date', 'N/A')} to {account_context.get('end_date', 'N/A')}"
                context_info = f"""
Context:
- Account: {account_id}
- Date Range: {date_range}
"""

            prompt = f"""You are a marketing intelligence agent analyzing user queries about Google Ads campaigns and marketing performance.

{context_info}
User Question: "{user_question}"

Analyze this question and return a JSON response with:

1. "intent_type" - one of: audience, budget, funnel, performance, scaling, general
2. "confidence" - score 0.0-1.0 for how confident you are
3. "key_focus" - what specifically the user wants to know
4. "data_needed" - what marketing data would best answer this
5. "response_style" - how the response should be formatted

Intent Types:
- audience: Demographics, targeting, who is converting
- budget: Waste, efficiency, cost optimization  
- funnel: Conversions, user journey, CTR/CVR analysis
- performance: Overall metrics, campaign comparison
- scaling: Which campaigns to increase budget on
- general: Broad questions or unclear intent

Return only valid JSON, no other text."""

            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": 300,  # Keep it short for intent analysis
                "temperature": 0.1,  # Low temperature for consistent analysis
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                # Extract content from Claude response
                if 'content' in result and len(result['content']) > 0:
                    content = result['content'][0]['text'].strip()
                    
                    # Try to parse as JSON
                    try:
                        intent_data = json.loads(content)
                        
                        return {
                            "success": True,
                            "agent": "Claude Intent Agent",
                            "intent": intent_data,
                            "raw_response": content,
                            "model_used": self.model,
                            "timestamp": datetime.now().isoformat()
                        }
                    except json.JSONDecodeError as e:
                        return {
                            "success": False,
                            "error": f"Failed to parse Claude response as JSON: {str(e)}",
                            "raw_response": content,
                            "fallback_to_existing": True
                        }
                else:
                    return {
                        "success": False,
                        "error": "No content in Claude response",
                        "fallback_to_existing": True
                    }
                    
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"Claude API HTTP error: {e.response.status_code} - {e.response.text}",
                "fallback_to_existing": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Claude API error: {str(e)}",
                "fallback_to_existing": True
            }
    
    async def enhance_response_formatting(self, mcp_data: Dict[str, Any], intent_analysis: Dict[str, Any], user_question: str) -> Optional[str]:
        """
        Use Claude to format response based on intent and MCP data
        """
        if not self.api_key:
            return None
            
        try:
            intent_type = intent_analysis.get('intent_type', 'general')
            key_focus = intent_analysis.get('key_focus', 'general analysis')
            confidence = intent_analysis.get('confidence', 0.0)
            
            # Extract comprehensive insights data from MCP results
            comprehensive_data = None
            for result in mcp_data.get('raw_results', []):
                if result.get('tool') == 'get_comprehensive_insights' and result.get('success'):
                    data = result.get('data', {})
                    if 'structuredContent' in data:
                        comprehensive_data = data['structuredContent']
                        break
                    else:
                        # Handle direct data structure
                        comprehensive_data = data
                        break
            
            if not comprehensive_data:
                print(f"[CLAUDE DEBUG] No comprehensive insights data found. Available results: {len(mcp_data.get('raw_results', []))}")
                for i, result in enumerate(mcp_data.get('raw_results', [])):
                    print(f"[CLAUDE DEBUG] Result {i}: tool={result.get('tool')}, success={result.get('success')}")
                    if 'data' in result:
                        print(f"[CLAUDE DEBUG] Result {i} data keys: {list(result['data'].keys()) if isinstance(result['data'], dict) else type(result['data'])}")
                return None
            
            # Extract campaign data from comprehensive insights structure
            google_ads_insights = comprehensive_data.get('individual_insights', {}).get('google_ads', {})
            if not google_ads_insights:
                print(f"[CLAUDE DEBUG] No Google Ads insights in comprehensive data")
                return None
                
            # Get campaign summary from comprehensive insights
            campaign_summary = google_ads_insights.get('campaign_comparison', {}).get('campaign_comparison', {})
            if not campaign_summary:
                print(f"[CLAUDE DEBUG] No campaign summary in Google Ads insights")
                return None
            
            campaigns = list(campaign_summary.values())
            customer_id = comprehensive_data.get('user_id', 'Unknown')
            date_range = {
                'start': comprehensive_data.get('analysis_period', '').split(' to ')[0] if ' to ' in comprehensive_data.get('analysis_period', '') else 'N/A',
                'end': comprehensive_data.get('analysis_period', '').split(' to ')[1] if ' to ' in comprehensive_data.get('analysis_period', '') else 'N/A'
            }
            
            # Build campaign summary for Claude
            campaigns_summary = []
            total_spend = 0
            total_conversions = 0
            total_clicks = 0
            total_impressions = 0
            
            for campaign_name, campaign_data in campaign_summary.items():
                spend = float(campaign_data.get('spend', 0))
                conversions = float(campaign_data.get('conversions', 0))
                clicks = int(campaign_data.get('clicks', 0))
                impressions = int(campaign_data.get('impressions', 0))
                ctr = float(campaign_data.get('ctr', 0))
                cost_per_conversion = float(campaign_data.get('cost_per_conversion', 0))
                
                total_spend += spend
                total_conversions += conversions
                total_clicks += clicks
                total_impressions += impressions
                
                campaigns_summary.append({
                    'name': campaign_name,
                    'spend': spend,
                    'conversions': conversions,
                    'clicks': clicks,
                    'impressions': impressions,
                    'ctr': ctr * 100,  # Convert to percentage if needed
                    'cost_per_conversion': cost_per_conversion
                })
            
            # Create Claude prompt based on intent
            if intent_type == 'budget':
                analysis_focus = f"""BUDGET WASTE ANALYSIS - Focus specifically on:
1. Which campaigns are wasting budget (high spend, low conversions)
2. Cost efficiency comparison between campaigns  
3. Specific budget reallocation recommendations
4. Immediate actions to stop waste

Do NOT provide generic GROW/RISK/OPTIMIZE format. Focus ONLY on budget waste and efficiency."""
                
            elif intent_type == 'audience':
                analysis_focus = f"""AUDIENCE ANALYSIS - Focus specifically on:
1. Campaign targeting and audience insights
2. Which campaigns reach the best audiences (based on conversion rates)
3. Audience optimization recommendations
4. Demographics and targeting insights

Do NOT provide generic GROW/RISK/OPTIMIZE format. Focus ONLY on audience and targeting."""
                
            elif intent_type == 'scaling':
                analysis_focus = f"""SCALING ANALYSIS - Focus specifically on:
1. Which campaigns are ready to scale (efficient + volume)
2. Scaling recommendations with specific budget increases
3. Risk assessment for scaling each campaign
4. Expected results from scaling

Do NOT provide generic GROW/RISK/OPTIMIZE format. Focus ONLY on scaling opportunities."""
                
            else:
                # Check if we have card_type context from frontend
                card_type = mcp_data.get('user_context', {}).get('card_type')
                if card_type == 'grow':
                    analysis_focus = f"""GROW FRAMEWORK ANALYSIS - Focus on growth opportunities:
1. Identify scaling opportunities and untapped potential
2. Find audiences, channels, or campaigns ready for expansion  
3. Highlight where to double down for faster growth
4. Recommend specific growth actions with expected impact

Answer the question: "{user_question}" within this growth context."""
                    
                elif card_type == 'optimize':
                    analysis_focus = f"""OPTIMIZE FRAMEWORK ANALYSIS - Focus on optimization improvements:
1. Identify inefficiencies and areas for refinement
2. Suggest targeting improvements and data-driven adjustments
3. Recommend ways to boost ROI and performance
4. Highlight specific optimization actions with expected results

Answer the question: "{user_question}" within this optimization context."""
                    
                elif card_type == 'risk':
                    analysis_focus = f"""RISK FRAMEWORK ANALYSIS - Focus on risk identification:
1. Flag underperforming elements that could hurt performance
2. Identify budget waste and protection opportunities  
3. Highlight campaigns/audiences to pause or cut
4. Recommend risk mitigation actions with specific impacts

Answer the question: "{user_question}" within this risk management context."""
                    
                else:
                    analysis_focus = f"""PERFORMANCE ANALYSIS - Focus on the specific question: "{user_question}"
Provide relevant insights based on what the user is asking about."""
            
            # Data from MCP is already in ZAR - no conversion needed
            total_spend_zar = total_spend
            
            prompt = f"""You are Mia, a conversational marketing intelligence agent. Your response will be spoken aloud by Dorothy AI, so write in a natural, conversational tone.

CRITICAL RULES:
- NEVER generate mock/fake marketing data or campaign names
- If you don't have real data, say "I don't have access to your marketing data right now" 
- DO NOT start with "Here is my analysis" or similar analytical prefixes
- DO NOT include stage directions like "*in a friendly, conversational tone*"
- Speak directly to the user as if you're having a conversation
- Be factual but conversational
- Focus ONLY on the {card_type.upper() if card_type else 'GENERAL'} framework - do not mention other frameworks
- ALWAYS use South African Rand (R) currency symbol - NEVER use dollar ($) symbols
- DISTINGUISH CAREFULLY between CPC (cost per click) and cost per conversion - these are different metrics
- When mentioning costs, be precise about whether it's CPC, cost per conversion, or total spend

User Question: "{user_question}"
Intent: {intent_type}

{analysis_focus}

Your Campaign Data:
- Account: {customer_id}
- Period: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}
- Total Spend: R{total_spend_zar:,.2f}
- Total Conversions: {total_conversions:,.0f}
- Total Clicks: {total_clicks:,}
- Total Impressions: {total_impressions:,}

Campaign Performance:
{self._format_campaigns_for_claude(campaigns_summary)}

Respond conversationally and directly. Focus on actionable insights. Include specific numbers in South African Rand (R) when mentioning costs. Keep it concise but comprehensive - this will be spoken aloud."""

            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,  # Longer response for detailed analysis
                "temperature": 0.2,  # Low temperature for factual analysis
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if 'content' in result and len(result['content']) > 0:
                    formatted_response = result['content'][0]['text'].strip()
                    return formatted_response
                else:
                    return None
                    
        except Exception as e:
            print(f"[CLAUDE FORMATTER] Error: {str(e)}")
            return None
    
    def _format_campaigns_for_claude(self, campaigns: List[Dict[str, Any]]) -> str:
        """Format campaign data for Claude analysis - data already in ZAR"""
        formatted = []
        for i, campaign in enumerate(campaigns, 1):
            spend = campaign['spend']  # Already in ZAR
            cost_per_conv = campaign['cost_per_conversion']  # Already in ZAR
            cost_per_conv_str = f"R{cost_per_conv:.2f}" if cost_per_conv > 0 else "No conversions"
            cpc = campaign.get('cpc', 0)  # Already in ZAR
            
            formatted.append(f"""{i}. {campaign['name']}:
   • Spend: R{spend:.2f}
   • Conversions: {campaign['conversions']:.0f}
   • Cost/Conversion: {cost_per_conv_str}
   • CPC (cost per click): R{cpc:.2f}
   • CTR: {campaign['ctr']:.2f}%
   • Clicks: {campaign['clicks']:,}
   • Impressions: {campaign['impressions']:,}""")
        
        return "\n\n".join(formatted)

# Singleton instance
_claude_agent = None

async def get_claude_intent_agent() -> ClaudeIntentAgent:
    """Get singleton Claude intent agent"""
    global _claude_agent
    if _claude_agent is None:
        _claude_agent = ClaudeIntentAgent()
    return _claude_agent