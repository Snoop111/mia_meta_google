"""
Simple ADK + MCP Integration
Focuses on integrating our working MCP client with Google ADK concepts
Without complex LangChain dependencies
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .mcp_client_fixed import get_mcp_client_fixed
from .claude_agent import get_claude_intent_agent

# Database imports for account mapping
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user_profile import AccountMapping


class ADKMarketingAgent:
    """
    Simplified Google ADK-inspired agent that uses our MCP tools
    Demonstrates the architecture without complex dependencies
    """
    
    def __init__(self):
        self.mcp_client = None
        self.tools = {
            "get_platform_examples": {
                "description": "Get examples of data structure formats for different marketing platforms",
                "parameters": {},
                "requires_auth": False
            },
            "get_comprehensive_insights": {
                "description": "Get comprehensive marketing insights from multiple data sources",
                "parameters": {
                    "user_id": "string (required)",
                    "data_selections": "array of data source selections",
                    "start_date": "string (YYYY-MM-DD)",
                    "end_date": "string (YYYY-MM-DD)"
                },
                "requires_auth": True
            },
            "query_google_ads_data": {
                "description": "Query Google Ads data for campaigns, demographics, keywords, locations, devices",
                "parameters": {
                    "user_id": "string (required)", 
                    "query_type": "string (campaigns, demographics, keywords, etc.)",
                    "metrics": "array of metrics to retrieve"
                },
                "requires_auth": True
            },
            "query_ga4_data": {
                "description": "Query Google Analytics 4 data for website traffic, user behavior, content performance",
                "parameters": {
                    "user_id": "string (required)",
                    "property_id": "string (optional, will use first available if not provided)",
                    "query_type": "string (overview, demographics, pages, sources, events, conversions, realtime)",
                    "start_date": "string (YYYY-MM-DD format, optional)",
                    "end_date": "string (YYYY-MM-DD format, optional)",
                    "dimensions": "array of GA4 dimensions (e.g., ['userGender', 'userAgeBracket'])",
                    "metrics": "array of GA4 metrics (e.g., ['sessions', 'screenPageViews'])",
                    "filters": "optional filters to apply to the data"
                },
                "requires_auth": True
            },
            "query_google_ads_data": {
                "description": "Query Google Ads data directly for specific insights like demographics, campaign performance, etc",
                "parameters": {
                    "user_id": "string (required)",
                    "customer_id": "string (optional, will use first available if not provided)",
                    "query_type": "string (campaigns, demographics, keywords, locations, devices, custom)",
                    "start_date": "string (YYYY-MM-DD format, optional)",
                    "end_date": "string (YYYY-MM-DD format, optional)",
                    "dimensions": "array of dimensions (e.g., ['gender', 'age_range'])",
                    "metrics": "array of metrics (e.g., ['impressions', 'clicks', 'cost_micros'])",
                    "custom_query": "string (custom Google Ads query string for advanced queries)"
                },
                "requires_auth": True
            },
            "get_google_ads_accounts": {
                "description": "List all accessible Google Ads accounts for a user",
                "parameters": {
                    "user_id": "string (required)"
                },
                "requires_auth": True
            },
            "get_ga4_properties": {
                "description": "List all accessible Google Analytics 4 properties for a user",
                "parameters": {
                    "user_id": "string (required)"
                },
                "requires_auth": True
            },
            "get_meta_ads_accounts": {
                "description": "List all accessible Meta (Facebook) Ads accounts for a user",
                "parameters": {
                    "user_id": "string (required)"
                },
                "requires_auth": True
            }
        }
        
    async def initialize(self):
        """Initialize the agent with MCP client"""
        self.mcp_client = await get_mcp_client_fixed()
        print("ADK Marketing Agent initialized with MCP tools")
    
    async def close(self):
        """Close MCP client and cleanup resources"""
        if self.mcp_client:
            await self.mcp_client.close()
            self.mcp_client = None
        
    def _classify_question_intent(self, query: str) -> Dict[str, Any]:
        """
        Phase 2: Smart MIA Brain - Classify question intent for contextual responses
        Returns question type, confidence, and contextual hints for formatting
        """
        query_lower = query.lower()
        
        # Question type patterns
        question_types = {
            'audience': {
                'keywords': ['audience', 'demographic', 'who', 'gender', 'age', 'location', 'targeting', 'users', 'customers', 'visitors', 'people'],
                'phrases': ['who is my', 'what demographics', 'audience breakdown', 'user demographics', 'customer profile'],
                'confidence_base': 0.8
            },
            'funnel': {
                'keywords': ['funnel', 'conversion', 'journey', 'path', 'flow', 'stage', 'awareness', 'consideration', 'decision', 'retention'],
                'phrases': ['user journey', 'conversion funnel', 'customer journey', 'purchase path', 'sales funnel'],
                'confidence_base': 0.8
            },
            'budget': {
                'keywords': ['budget', 'spend', 'cost', 'waste', 'wasting', 'expensive', 'money', 'allocation', 'optimization', 'efficient'],
                'phrases': ['wasting budget', 'budget allocation', 'cost optimization', 'spend efficiency', 'where am i wasting'],
                'confidence_base': 0.9
            },
            'performance': {
                'keywords': ['performance', 'performing', 'best', 'worst', 'top', 'bottom', 'campaign', 'results', 'metrics'],
                'phrases': ['best performing', 'top campaigns', 'campaign performance', 'which campaigns'],
                'confidence_base': 0.7
            },
            'scaling': {
                'keywords': ['scale', 'scaling', 'increase', 'grow', 'expand', 'more', 'boost'],
                'phrases': ['scale up', 'which campaigns to scale', 'what should i scale', 'grow campaigns'],
                'confidence_base': 0.8
            }
        }
        
        # Calculate scores for each type
        type_scores = {}
        for qtype, patterns in question_types.items():
            score = 0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in patterns['keywords'] if keyword in query_lower)
            score += keyword_matches * 0.3
            
            # Phrase matching (higher weight)
            phrase_matches = sum(1 for phrase in patterns['phrases'] if phrase in query_lower)
            score += phrase_matches * 0.7
            
            # Apply confidence base
            if score > 0:
                score *= patterns['confidence_base']
            
            type_scores[qtype] = score
        
        # Find the best match
        if not type_scores or max(type_scores.values()) == 0:
            return {
                'type': 'general',
                'confidence': 0.5,
                'context': 'No specific intent detected - using general analysis'
            }
        
        best_type = max(type_scores, key=type_scores.get)
        confidence = min(type_scores[best_type], 1.0)  # Cap at 1.0
        
        return {
            'type': best_type,
            'confidence': confidence,
            'context': f"Detected {best_type} question with {confidence:.1f} confidence",
            'all_scores': type_scores
        }
    
    def _generate_contextual_response(self, query: str, intent: Dict[str, Any], tool_results: List[Dict[str, Any]], user_context: Dict[str, Any] = None) -> str:
        """
        Phase 2: Generate contextual response based on question intent
        """
        print(f"[DEBUG] _generate_contextual_response called with {len(tool_results)} tool results")
        
        # Extract data from comprehensive_insights
        insights_data = None
        for result in tool_results:
            print(f"[DEBUG] Checking tool result: {result.get('tool')} - success: {result.get('success')}")
            if result['tool'] == 'get_comprehensive_insights' and result['success']:
                insights_data = result['data']
                print(f"[DEBUG] Found comprehensive insights data")
                break
        
        if not insights_data:
            print(f"[DEBUG] No insights data found - returning error message")
            return "I couldn't retrieve marketing data to answer your question. Please check your account connection."
        
        question_type = intent['type']
        confidence = intent['confidence']
        
        # Get account context
        account_id = user_context.get('focus_account', 'Unknown') if user_context else 'Unknown'
        start_date = user_context.get('start_date', 'Unknown') if user_context else 'Unknown'
        end_date = user_context.get('end_date', 'Unknown') if user_context else 'Unknown'
        
        # Header with context
        response = f"📊 **Marketing Analysis** - {question_type.title()} Focus\n"
        response += f"Account: {account_id} | Period: {start_date} to {end_date}\n"
        response += f"Intent Confidence: {confidence:.1f}\n\n"
        
        # Contextual response based on question type
        if question_type == 'audience':
            response += self._format_audience_response(insights_data, query)
        elif question_type == 'funnel':
            response += self._format_funnel_response(insights_data, query)
        elif question_type == 'budget':
            response += self._format_budget_response(insights_data, query)
        elif question_type == 'performance':
            response += self._format_performance_response(insights_data, query)
        elif question_type == 'scaling':
            response += self._format_scaling_response(insights_data, query)
        else:
            response += self._format_general_response(insights_data, query)
        
        return response
    
    def _format_audience_response(self, data: Dict[str, Any], query: str) -> str:
        """Format response for audience/demographic questions"""
        response = "## 👥 **AUDIENCE INSIGHTS**\n\n"
        
        # Look for demographic data in comprehensive insights
        if 'individual_insights' in data:
            insights = data['individual_insights']
            
            # Check for GA4 audience data
            if 'google_analytics' in insights:
                ga_data = insights['google_analytics']
                response += "### Website Audience (GA4)\n"
                if 'data' in ga_data and ga_data['data']:
                    # Look for demographic breakdowns
                    response += "• Demographics and user behavior data available\n"
                    response += "• Website traffic patterns identified\n"
                else:
                    response += "• No GA4 audience data available (authentication needed)\n"
            
            # Check for Google Ads audience data
            if 'google_ads' in insights:
                ads_data = insights['google_ads']
                response += "\n### Campaign Targeting (Google Ads)\n"
                if 'data' in ads_data and ads_data['data']:
                    campaigns = ads_data['data']
                    active_campaigns = [c for c in campaigns if c.get('campaign_status') == 'ENABLED']
                    response += f"• {len(active_campaigns)} active campaigns with targeting data\n"
                    response += f"• {len(campaigns)} total campaigns analyzed\n"
                    
                    # Show campaign names that might indicate audience targeting
                    for campaign in active_campaigns[:3]:
                        name = campaign.get('campaign_name', 'Unknown')
                        response += f"• **{name}**: Active targeting\n"
                else:
                    response += "• No Google Ads campaign data available\n"
        
        response += "\n## 💡 **AUDIENCE RECOMMENDATIONS**\n"
        response += "• **Analyze Demographics**: Use GA4 to understand your visitor profiles\n"
        response += "• **Refine Targeting**: Adjust Google Ads audience settings based on performance\n"
        response += "• **Cross-Platform Insights**: Compare GA4 visitors vs Google Ads converters\n"
        
        return response
    
    def _format_funnel_response(self, data: Dict[str, Any], query: str) -> str:
        """Format response for funnel/conversion questions"""
        response = "## 🔄 **CONVERSION FUNNEL ANALYSIS**\n\n"
        
        if 'individual_insights' in data:
            insights = data['individual_insights']
            
            # Google Ads conversion data
            if 'google_ads' in insights:
                ads_data = insights['google_ads']
                if 'data' in ads_data and ads_data['data']:
                    campaigns = ads_data['data']
                    
                    # Calculate funnel metrics
                    total_impressions = sum(int(c.get('impressions', 0)) for c in campaigns)
                    total_clicks = sum(int(c.get('clicks', 0)) for c in campaigns)
                    total_conversions = sum(float(c.get('conversions', 0)) for c in campaigns)
                    
                    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                    cvr = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
                    
                    response += "### Campaign Funnel Performance\n"
                    response += f"• **Impressions**: {total_impressions:,}\n"
                    response += f"• **Clicks**: {total_clicks:,} (CTR: {ctr:.2f}%)\n"
                    response += f"• **Conversions**: {total_conversions:.0f} (CVR: {cvr:.2f}%)\n\n"
                    
                    # Find best and worst performing campaigns for funnel
                    campaigns_with_cvr = []
                    for campaign in campaigns:
                        clicks = int(campaign.get('clicks', 0))
                        conversions = float(campaign.get('conversions', 0))
                        if clicks > 10:  # Only campaigns with meaningful traffic
                            cvr = (conversions / clicks * 100) if clicks > 0 else 0
                            campaigns_with_cvr.append({
                                'name': campaign.get('campaign_name', 'Unknown'),
                                'cvr': cvr,
                                'conversions': conversions,
                                'clicks': clicks
                            })
                    
                    if campaigns_with_cvr:
                        # Sort by conversion rate
                        campaigns_with_cvr.sort(key=lambda x: x['cvr'], reverse=True)
                        
                        response += "### 🏆 **FUNNEL WINNERS** (Best Conversion Rates)\n"
                        for i, campaign in enumerate(campaigns_with_cvr[:3]):
                            response += f"{i+1}. **{campaign['name']}**: {campaign['cvr']:.1f}% CVR ({campaign['conversions']:.0f} conversions)\n"
                        
                        response += "\n### ⚠️ **FUNNEL LEAKS** (Low Conversion Rates)\n"
                        for i, campaign in enumerate(campaigns_with_cvr[-3:]):
                            response += f"{i+1}. **{campaign['name']}**: {campaign['cvr']:.1f}% CVR ({campaign['clicks']} clicks)\n"
            
            # GA4 funnel data
            if 'google_analytics' in insights:
                response += "\n### Website Funnel (GA4)\n"
                response += "• Page-level conversion tracking available\n"
                response += "• User journey analysis can be performed\n"
        
        response += "\n## 💡 **FUNNEL OPTIMIZATION RECOMMENDATIONS**\n"
        response += "• **Fix Leaks**: Improve landing pages for low-CVR campaigns\n"
        response += "• **Scale Winners**: Increase budget for high-CVR campaigns\n"
        response += "• **Test Paths**: A/B test different conversion flows\n"
        
        return response
    
    def _format_budget_response(self, data: Dict[str, Any], query: str) -> str:
        """Format response for budget/waste questions"""
        response = "## 💰 **BUDGET ANALYSIS**\n\n"
        
        if 'individual_insights' in data:
            insights = data['individual_insights']
            
            if 'google_ads' in insights:
                ads_data = insights['google_ads']
                if 'data' in ads_data and ads_data['data']:
                    campaigns = ads_data['data']
                    
                    # Calculate budget efficiency metrics
                    total_spend = 0
                    total_conversions = 0
                    campaign_efficiency = []
                    
                    for campaign in campaigns:
                        cost = float(campaign.get('cost_micros', 0)) / 1_000_000
                        conversions = float(campaign.get('conversions', 0))
                        clicks = int(campaign.get('clicks', 0))
                        
                        total_spend += cost
                        total_conversions += conversions
                        
                        if cost > 50:  # Only analyze campaigns with meaningful spend
                            cost_per_conversion = cost / conversions if conversions > 0 else float('inf')
                            efficiency_score = min(100, (conversions / cost * 50)) if cost > 0 else 0
                            
                            campaign_efficiency.append({
                                'name': campaign.get('campaign_name', 'Unknown'),
                                'cost': cost,
                                'conversions': conversions,
                                'cost_per_conversion': cost_per_conversion,
                                'efficiency_score': efficiency_score,
                                'clicks': clicks
                            })
                    
                    avg_cost_per_conversion = total_spend / total_conversions if total_conversions > 0 else 0
                    
                    response += "### Overall Budget Performance\n"
                    response += f"• **Total Spend**: R{total_spend:,.2f}\n"
                    response += f"• **Total Conversions**: {total_conversions:.0f}\n"
                    response += f"• **Average Cost/Conversion**: R{avg_cost_per_conversion:.2f}\n\n"
                    
                    if campaign_efficiency:
                        # Sort by efficiency (lowest cost per conversion first)
                        campaign_efficiency.sort(key=lambda x: x['cost_per_conversion'])
                        
                        response += "### 💸 **BUDGET WASTE ALERTS**\n"
                        high_cost_campaigns = [c for c in campaign_efficiency if c['cost_per_conversion'] > avg_cost_per_conversion * 2 or c['cost_per_conversion'] == float('inf')]
                        
                        if high_cost_campaigns:
                            for i, campaign in enumerate(high_cost_campaigns[:3]):
                                if campaign['conversions'] == 0:
                                    response += f"{i+1}. **{campaign['name']}**: R{campaign['cost']:.2f} spend, 0 conversions ❌\n"
                                else:
                                    response += f"{i+1}. **{campaign['name']}**: R{campaign['cost_per_conversion']:.2f}/conversion (R{campaign['cost']:.2f} total)\n"
                        else:
                            response += "• No major budget waste detected - good efficiency across campaigns!\n"
                        
                        response += "\n### 🎯 **BUDGET EFFICIENCY WINNERS**\n"
                        efficient_campaigns = [c for c in campaign_efficiency if c['cost_per_conversion'] < avg_cost_per_conversion and c['conversions'] >= 5]
                        
                        if efficient_campaigns:
                            for i, campaign in enumerate(efficient_campaigns[:3]):
                                response += f"{i+1}. **{campaign['name']}**: ${campaign['cost_per_conversion']:.2f}/conversion ({campaign['conversions']:.0f} conversions)\n"
                        else:
                            response += "• Consider optimizing campaigns to improve cost per conversion\n"
        
        response += "\n## 💡 **BUDGET OPTIMIZATION RECOMMENDATIONS**\n"
        response += "• **Pause Waste**: Stop campaigns with zero conversions after 30 days\n"
        response += "• **Reallocate Budget**: Move spend from high-cost to efficient campaigns\n"
        response += "• **Set Limits**: Implement daily budget caps for testing campaigns\n"
        
        return response
    
    def _format_performance_response(self, data: Dict[str, Any], query: str) -> str:
        """Format response for general performance questions"""
        return self._format_general_response(data, query)  # Use existing GROW/RISK/OPTIMIZE
    
    def _format_scaling_response(self, data: Dict[str, Any], query: str) -> str:
        """Format response for scaling questions"""
        response = "## 📈 **SCALING OPPORTUNITIES**\n\n"
        
        if 'individual_insights' in data:
            insights = data['individual_insights']
            
            if 'google_ads' in insights:
                ads_data = insights['google_ads']
                if 'data' in ads_data and ads_data['data']:
                    campaigns = ads_data['data']
                    
                    # Find campaigns worth scaling
                    scalable_campaigns = []
                    for campaign in campaigns:
                        conversions = float(campaign.get('conversions', 0))
                        cost = float(campaign.get('cost_micros', 0)) / 1_000_000
                        clicks = int(campaign.get('clicks', 0))
                        impressions = int(campaign.get('impressions', 0))
                        
                        if conversions >= 10 and cost > 100:  # Meaningful volume and spend
                            cost_per_conversion = cost / conversions if conversions > 0 else float('inf')
                            ctr = (clicks / impressions * 100) if impressions > 0 else 0
                            
                            # Calculate scaling potential
                            scaling_score = 0
                            if cost_per_conversion < 50:  # Efficient conversion cost
                                scaling_score += 30
                            if ctr > 2:  # Good engagement
                                scaling_score += 25
                            if conversions >= 20:  # High volume
                                scaling_score += 25
                            if campaign.get('campaign_status') == 'ENABLED':  # Active
                                scaling_score += 20
                            
                            scalable_campaigns.append({
                                'name': campaign.get('campaign_name', 'Unknown'),
                                'conversions': conversions,
                                'cost': cost,
                                'cost_per_conversion': cost_per_conversion,
                                'ctr': ctr,
                                'scaling_score': scaling_score,
                                'status': campaign.get('campaign_status', 'Unknown')
                            })
                    
                    if scalable_campaigns:
                        # Sort by scaling score
                        scalable_campaigns.sort(key=lambda x: x['scaling_score'], reverse=True)
                        
                        response += "### 🚀 **TOP SCALING CANDIDATES**\n"
                        for i, campaign in enumerate(scalable_campaigns[:3]):
                            response += f"{i+1}. **{campaign['name']}**\n"
                            response += f"   • {campaign['conversions']:.0f} conversions at ${campaign['cost_per_conversion']:.2f}/conversion\n"
                            response += f"   • {campaign['ctr']:.1f}% CTR | Scaling Score: {campaign['scaling_score']}/100\n"
                            response += f"   • **Recommendation**: Increase budget by 25-50%\n\n"
                        
                        response += "### ⚠️ **SCALING CAUTIONS**\n"
                        caution_campaigns = [c for c in campaigns if float(c.get('conversions', 0)) < 5 and float(c.get('cost_micros', 0)) / 1_000_000 > 200]
                        
                        if caution_campaigns:
                            for campaign in caution_campaigns[:2]:
                                name = campaign.get('campaign_name', 'Unknown')
                                cost = float(campaign.get('cost_micros', 0)) / 1_000_000
                                conversions = float(campaign.get('conversions', 0))
                                response += f"• **{name}**: High spend (R{cost:.2f}) but low conversions ({conversions:.0f}) - optimize before scaling\n"
                        else:
                            response += "• No high-risk campaigns detected for scaling\n"
                    else:
                        response += "• No campaigns currently meet scaling criteria\n"
                        response += "• Focus on optimizing existing campaigns first\n"
        
        response += "\n## 💡 **SCALING STRATEGY RECOMMENDATIONS**\n"
        response += "• **Start Small**: Increase budgets by 25% initially, monitor for 1 week\n"
        response += "• **Monitor CPA**: Watch for cost per conversion increases during scaling\n"
        response += "• **Expand Gradually**: Scale proven winners systematically\n"
        
        return response
    
    def _format_general_response(self, data: Dict[str, Any], query: str) -> str:
        """Fallback to existing GROW/RISK/OPTIMIZE format for general questions"""
        response = "## 📊 **GENERAL PERFORMANCE OVERVIEW**\n\n"
        response += "I've analyzed your marketing data. For detailed GROW/RISK/OPTIMIZE insights, please ask more specific questions about:\n"
        response += "• **Audience**: 'Who is my audience?' or 'What demographics perform best?'\n"
        response += "• **Budget**: 'Where am I wasting budget?' or 'How can I optimize spend?'\n"
        response += "• **Funnel**: 'How is my conversion funnel performing?'\n"
        response += "• **Scaling**: 'Which campaigns should I scale?'\n"
        return response

    async def analyze_marketing_query(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Phase 2: Smart MIA - Analyze marketing query with contextual intelligence
        1. Classify question intent
        2. Use comprehensive_insights tool for raw data
        3. Apply contextual formatting based on question type
        4. Return relevant, focused response
        """
        print(f"[SMART MIA] analyze_marketing_query called with query: {query}")
        if not self.mcp_client:
            print("[SMART MIA] Initializing MCP client...")
            await self.initialize()
        print(f"[SMART MIA] MCP client ready: {self.mcp_client is not None}")
            
        try:
            # Step 1: Try Claude intent analysis (with fallback to existing)
            claude_agent = await get_claude_intent_agent()
            claude_result = await claude_agent.analyze_intent(query, user_context)
            
            if claude_result.get('success'):
                print(f"[CLAUDE AGENT] Intent analysis successful")
                intent_data = claude_result.get('intent', {})
                print(f"[CLAUDE AGENT] Detected intent: {intent_data.get('intent_type', 'unknown')}")
                print(f"[CLAUDE AGENT] Confidence: {intent_data.get('confidence', 0)}")
                print(f"[CLAUDE AGENT] Key focus: {intent_data.get('key_focus', 'N/A')}")
            else:
                print(f"[CLAUDE AGENT] Intent analysis failed: {claude_result.get('error', 'Unknown error')}")
                print(f"[CLAUDE AGENT] Falling back to existing system")
            
            # Step 2: Select tools with intelligent context awareness
            query_lower = query.lower()
            focus_account = user_context.get('focus_account')
            selected_tools = self._select_tools_for_query(query_lower, focus_account)
            
            print(f"Query: {query}")
            print(f"Selected tools: {[tool['name'] for tool in selected_tools]}")
            
            # Step 2: Execute selected tools
            tool_results = []
            for tool in selected_tools:
                print(f"[ADK DEBUG] Executing tool: {tool['name']}")
                result = await self._execute_tool(tool, user_context)
                print(f"[ADK DEBUG] Tool {tool['name']} result type: {type(result)}")
                if result:
                    print(f"[ADK DEBUG] Tool {tool['name']} success: {not result.get('error')}")
                    if result.get('error'):
                        print(f"[ADK DEBUG] Tool {tool['name']} error: {result.get('error')}")
                tool_results.append({
                    "tool": tool['name'],
                    "success": not result.get('error'),
                    "data": result
                })
                
            # Step 4: Synthesize insights (simplified)
            insights = self._synthesize_insights(query, tool_results)
            
            # Include Claude intent analysis in response if available
            response_data = {
                "success": True,
                "agent": "ADK Marketing Agent with Claude Intent",
                "query": query,
                "tools_executed": len(tool_results),
                "insights": insights,
                "raw_results": tool_results,
                "timestamp": datetime.now().isoformat()
            }
            
            # Let Claude analyze the marketing data from individual tools
            print(f"[CLAUDE] Processing marketing data with Claude intelligence...")
            
            # Collect all successful tool data
            google_ads_data = None
            ga4_data = None
            comprehensive_data = None
            
            for result in tool_results:
                if result.get('success'):
                    if result.get('tool') == 'query_google_ads_data':
                        google_ads_data = result.get('data', {})
                    elif result.get('tool') == 'query_ga4_data':
                        ga4_data = result.get('data', {})
                    elif result.get('tool') == 'get_comprehensive_insights':
                        comprehensive_data = result.get('data', {})
            
            if google_ads_data or ga4_data or comprehensive_data:
                # Use Claude agent for proper analysis
                claude_agent = await get_claude_intent_agent()
                
                # Use Claude's enhanced response formatting with proper data parsing
                mcp_results_data = {
                    'raw_results': [
                        {
                            'tool': 'get_comprehensive_insights' if comprehensive_data else ('query_google_ads_data' if google_ads_data else 'query_ga4_data'),
                            'success': True,
                            'data': comprehensive_data or google_ads_data or ga4_data
                        }
                    ],
                    'user_context': user_context
                }
                
                formatted_data = await claude_agent.enhance_response_formatting(mcp_results_data, claude_result.get('intent', {}), query)
                if not formatted_data:
                    # Fallback to simple formatting if Claude formatting fails
                    formatted_data = self._format_cross_platform_data(google_ads_data, ga4_data, query)
                
                # DEBUG: Show what data is being sent to Claude
                print(f"[CLAUDE DEBUG] Formatted data ready for Claude (length: {len(formatted_data)} chars)")
                
                # Format comprehensive insights data for Claude analysis
                card_type = (user_context or {}).get('card_type', 'general')
                card_type_upper = card_type.upper() if card_type else 'GENERAL'
                
                claude_prompt = f"""You are Mia, a conversational marketing intelligence agent. Your response will be spoken aloud by Dorothy AI, so write in a natural, conversational tone.

CRITICAL RULES:
- NEVER generate mock/fake marketing data or campaign names
- If you don't have real data, say "I don't have access to your marketing data right now"
- DO NOT start with "Here is my analysis" or similar analytical prefixes
- DO NOT include stage directions like "*in a friendly, conversational tone*"
- Speak directly to the user as if you're having a conversation
- Be factual but conversational
- Focus ONLY on {card_type_upper} framework - do not mention other frameworks

User Question: "{query}"
Card Type: {card_type}

Your Marketing Data:
{formatted_data}

Respond conversationally and directly. Focus on actionable insights. Include specific numbers in South African Rand (R) when mentioning costs (convert USD to ZAR at R17.65 to $1). Keep it concise but comprehensive - this will be spoken aloud."""

                # Call Claude API directly for comprehensive insights
                import os
                import httpx
                
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(
                                "https://api.anthropic.com/v1/messages",
                                headers={
                                    "Content-Type": "application/json",
                                    "x-api-key": api_key,
                                    "anthropic-version": "2023-06-01"
                                },
                                json={
                                    "model": "claude-3-5-sonnet-20241022",
                                    "max_tokens": 1000,
                                    "temperature": 0.1,
                                    "messages": [{"role": "user", "content": claude_prompt}]
                                }
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                if 'content' in result and len(result['content']) > 0:
                                    claude_response = result['content'][0]['text'].strip()
                                else:
                                    claude_response = "Unable to analyze your marketing data at the moment."
                            else:
                                claude_response = "Unable to analyze your marketing data at the moment."
                    except Exception as e:
                        print(f"[CLAUDE] ERROR: {e}")
                        claude_response = "Unable to analyze your marketing data at the moment."
                else:
                    claude_response = "Marketing data analysis is unavailable."
                
                print(f"[CLAUDE] SUCCESS: Response ready")
                response_data["success"] = True
                response_data["response"] = claude_response
            else:
                print(f"[CLAUDE] ERROR: No marketing data found")
                response_data["success"] = False
                response_data["response"] = "Unable to retrieve marketing data. Please check your account authentication."
            
            return response_data
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": "ADK Marketing Agent",
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def _select_tools_for_query(self, query_lower: str, focus_account: str = None) -> List[Dict[str, Any]]:
        """HYBRID MCP STRATEGY: Smart tool selection based on account capabilities"""
        selected = []
        
        # Platform examples only for specific requests
        if any(word in query_lower for word in ["platform", "example", "format", "structure", "what tools", "available tools"]):
            selected.append({
                "name": "get_platform_examples",
                "priority": 1
            })
        
        # Get account listings when asked about accounts or properties
        elif any(word in query_lower for word in ["what accounts", "list accounts", "google ads account", "available accounts", "connected accounts", "ga4 properties", "properties", "what ga4", "analytics properties"]) and "campaign" not in query_lower:
            # Use individual tools for account listing only
            selected.append({
                "name": "get_google_ads_accounts",
                "priority": 1
            })
            selected.append({
                "name": "get_ga4_properties", 
                "priority": 2
            })
        
        # UNIFIED STRATEGY: ALWAYS use comprehensive_insights
        # Let MCP backend decide single vs multi-platform based on available data
        else:
            print(f"[UNIFIED] Using comprehensive insights for account {focus_account} - MCP will determine single vs multi-platform")
            selected.append({
                "name": "get_comprehensive_insights",
                "priority": 1
            })
        
        # Sort by priority
        selected.sort(key=lambda x: x['priority'])
        return selected
    
    def _get_account_capabilities(self, focus_account: str = None) -> Dict[str, bool]:
        """Determine account capabilities for hybrid strategy"""
        if not focus_account:
            return {"has_google_ads": True, "has_ga4": False, "supports_comprehensive_insights": False}
        
        # Resolve account to platform-specific IDs
        resolved_ids = self._resolve_account_ids(focus_account)
        has_google_ads = bool(resolved_ids.get('google_ads_id'))
        has_ga4 = bool(resolved_ids.get('ga4_property_id'))
        
        # Comprehensive insights available when both platforms are available
        supports_comprehensive_insights = has_google_ads and has_ga4
        
        print(f"[CAPABILITIES] Account {focus_account}: Google Ads={has_google_ads}, GA4={has_ga4}, Comprehensive={supports_comprehensive_insights}")
        
        return {
            "has_google_ads": has_google_ads,
            "has_ga4": has_ga4,
            "supports_comprehensive_insights": supports_comprehensive_insights
        }
    
    def _format_cross_platform_data(self, google_ads_data: Dict[str, Any] = None, ga4_data: Dict[str, Any] = None, query: str = "") -> str:
        """Format cross-platform marketing data for Claude analysis"""
        formatted = []
        
        # Header
        if google_ads_data and ga4_data:
            formatted.append("## **Cross-Platform Marketing Data Available**")
            formatted.append("**Claude can now provide comprehensive user journey analysis**")
        elif google_ads_data:
            formatted.append("## **Google Ads Data Available**")
        elif ga4_data:
            formatted.append("## **Google Analytics Data Available**")
        
        # Google Ads Data
        if google_ads_data and google_ads_data.get('success') and google_ads_data.get('data'):
            formatted.append("\n### Google Ads Performance Data:")
            
            # Extract campaigns data directly from data key
            campaigns = google_ads_data['data']
            formatted.append(f"**Campaign Data**: {len(campaigns)} campaigns found")
            
            # Calculate totals (MCP data uses 'cost' field directly, not 'cost_micros')
            total_spend = sum(float(c.get('cost', 0)) for c in campaigns)
            total_conversions = sum(float(c.get('conversions', 0)) for c in campaigns)
            total_clicks = sum(int(c.get('clicks', 0)) for c in campaigns)
            total_impressions = sum(int(c.get('impressions', 0)) for c in campaigns)
            
            formatted.append(f"**Total Spend**: R{total_spend:,.2f}")
            formatted.append(f"**Total Conversions**: {total_conversions:,.0f}")
            formatted.append(f"**Total Clicks**: {total_clicks:,}")
            formatted.append(f"**Total Impressions**: {total_impressions:,}")
            
            if total_clicks > 0:
                avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                formatted.append(f"**Average CTR**: {avg_ctr:.2f}%")
            
            if total_conversions > 0 and total_spend > 0:
                cost_per_conversion = total_spend / total_conversions
                formatted.append(f"**Cost per Conversion**: ${cost_per_conversion:.2f}")
            
            # Show top campaigns
            formatted.append(f"\n**Top Campaigns by Spend**:")
            sorted_campaigns = sorted(campaigns, key=lambda x: float(x.get('cost', 0)), reverse=True)
            for i, campaign in enumerate(sorted_campaigns[:3]):
                name = campaign.get('campaign_name', 'Unknown')
                spend = float(campaign.get('cost', 0))
                conversions = float(campaign.get('conversions', 0))
                formatted.append(f"{i+1}. **{name}**: ${spend:.2f} spend, {conversions:.0f} conversions")
        
        # GA4 Data
        if ga4_data and ga4_data.get('success'):
            formatted.append("\n### Google Analytics Performance Data:")
            
            # Check for structured content (analytics data)
            if 'structuredContent' in ga4_data and ga4_data['structuredContent'].get('rows'):
                rows = ga4_data['structuredContent']['rows']
                formatted.append(f"**Analytics Data**: {len(rows)} data points found")
                
                # Look for key metrics in the first row (summary data)
                if rows and len(rows) > 0:
                    first_row = rows[0]
                    if 'metric_values' in first_row:
                        metrics = first_row['metric_values']
                        formatted.append(f"👥 **Sessions**: {metrics.get('sessions', 'N/A')}")
                        formatted.append(f"🆕 **New Users**: {metrics.get('newUsers', 'N/A')}")
                        formatted.append(f"📄 **Page Views**: {metrics.get('screenPageViews', 'N/A')}")
                        formatted.append(f"⏱️ **Engagement Time**: {metrics.get('userEngagementDuration', 'N/A')} seconds")
                        if 'bounceRate' in metrics:
                            bounce_rate = float(metrics['bounceRate']) * 100
                            formatted.append(f"🏃 **Bounce Rate**: {bounce_rate:.1f}%")
        
        # Cross-platform insights opportunity
        if google_ads_data and ga4_data:
            formatted.append("\n### ✨ **Cross-Platform Analysis Opportunity**:")
            formatted.append("🔄 **User Journey**: Can analyze from ad click to website behavior")
            formatted.append("📍 **Drop-off Points**: Can identify where users leave the funnel")
            formatted.append("🎯 **Attribution**: Can connect ad performance to website outcomes")
            formatted.append("💡 **Optimization**: Can recommend improvements across both platforms")
        
        return "\n".join(formatted)
    
    def _determine_account_type(self, focus_account: str) -> str:
        """Determine if focus_account is GA4-only, Google Ads, or unified"""
        if not focus_account:
            return "unknown"
            
        # Check if it's a known GA4-only property
        ga4_only_properties = ["428491753", "475337837", "485466226", "493853437", "493882843", "494813186"]
        if focus_account in ga4_only_properties:
            return "ga4_only"
            
        # Check if it's a known Google Ads account
        resolved_ids = self._resolve_account_ids(focus_account)
        if resolved_ids.get('google_ads_id') and not resolved_ids.get('ga4_property_id'):
            return "google_ads"
        elif resolved_ids.get('google_ads_id') and resolved_ids.get('ga4_property_id'):
            return "unified"
        elif resolved_ids.get('ga4_property_id'):
            return "ga4_only"
            
        return "unknown"
    
    def _account_has_ga4(self, focus_account: str) -> bool:
        """Check if an account has GA4 properties available"""
        resolved_ids = self._resolve_account_ids(focus_account)
        return bool(resolved_ids.get('ga4_property_id'))
    
    def _resolve_account_ids(self, focus_account: str) -> Dict[str, str]:
        """Resolve unified account ID to platform-specific IDs using database"""
        db = SessionLocal()
        try:
            # First try direct lookup by account_id (unified account key like "dfsa")
            account = db.query(AccountMapping).filter(AccountMapping.account_id == focus_account).first()

            if account:
                return {
                    'google_ads_id': account.google_ads_id,
                    'ga4_property_id': account.ga4_property_id
                }

            # If not found, try reverse lookup by Google Ads ID
            account = db.query(AccountMapping).filter(AccountMapping.google_ads_id == focus_account).first()

            if account:
                return {
                    'google_ads_id': account.google_ads_id,
                    'ga4_property_id': account.ga4_property_id
                }

            # If not found, try reverse lookup by GA4 property ID
            account = db.query(AccountMapping).filter(AccountMapping.ga4_property_id == focus_account).first()

            if account:
                return {
                    'google_ads_id': account.google_ads_id,
                    'ga4_property_id': account.ga4_property_id
                }

            # If it's a numeric ID and not found in database, return as-is for backward compatibility
            if focus_account and focus_account.isdigit():
                # Assume it's a Google Ads ID if not found in GA4 mappings
                return {
                    'google_ads_id': focus_account,
                    'ga4_property_id': None
                }

            # Complete fallback - return empty
            print(f"[ADK-AGENT] WARNING: Unknown account '{focus_account}', no mapping found")
            return {'google_ads_id': None, 'ga4_property_id': None}

        finally:
            db.close()

    async def _execute_tool(self, tool_config: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific MCP tool with appropriate parameters"""
        tool_name = tool_config['name']

        try:
            if tool_name == "get_platform_examples":
                # No parameters needed
                return await self.mcp_client.get_platform_examples()
                
            elif tool_name == "get_comprehensive_insights":
                # Get date ranges from user context
                start_date = user_context.get('start_date') if user_context else None
                end_date = user_context.get('end_date') if user_context else None
                
                # If no dates provided, use last 30 days
                if not start_date or not end_date:
                    from datetime import datetime, timedelta
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                # Build date_range object for both platforms
                date_range = {
                    "start": start_date,
                    "end": end_date
                }
                
                # DYNAMIC ACCOUNT SELECTION - Uses focus_account from user_context
                focus_account = user_context.get('focus_account', 'dfsa')  # Default to DFSA
                
                # Get account configuration from database
                db = SessionLocal()
                try:
                    account = db.query(AccountMapping).filter(AccountMapping.account_id == focus_account).first()

                    if not account:
                        print(f"[ERROR] Unknown focus_account: {focus_account}, defaulting to dfsa")
                        account = db.query(AccountMapping).filter(AccountMapping.account_id == "dfsa").first()
                        focus_account = "dfsa"

                    if not account:
                        raise ValueError("No accounts found in database - please initialize AccountMapping table")

                    account_config = {
                        "google_ads_id": account.google_ads_id,
                        "ga4_property_id": account.ga4_property_id,
                        "meta_ads_id": account.meta_ads_id
                    }
                finally:
                    db.close()
                meta_info = f", Meta Ads {account_config['meta_ads_id']}" if account_config['meta_ads_id'] else " (no Meta Ads configured)"
                print(f"[DEBUG] Using dynamic account: {focus_account} -> Google Ads {account_config['google_ads_id']}, GA4 {account_config['ga4_property_id']}{meta_info}")

                data_selections = [
                    {
                        "platform": "google_ads",
                        "account_id": account_config["google_ads_id"],
                        "date_range": date_range
                    },
                    {
                        "platform": "google_analytics",
                        "property_id": account_config["ga4_property_id"],
                        "date_range": date_range
                    }
                ]

                # Add Meta ads if configured
                if account_config["meta_ads_id"]:
                    data_selections.append({
                        "platform": "facebook",  # FIXED: MCP expects 'facebook', not 'meta_ads'
                        "account_id": account_config["meta_ads_id"],
                        "date_range": date_range
                    })
                
                # SMART USER ID SELECTION: Use Meta user ID when Meta data is requested
                has_meta_data = any(ds.get('platform') == 'facebook' for ds in data_selections)

                if has_meta_data:
                    # If Meta data is requested, use Meta user ID (122146502042672568)
                    user_id = "122146502042672568"
                    print(f"[DEBUG] Meta data requested - using Meta user ID: {user_id}")
                else:
                    # Use Google user ID from context for Google-only queries
                    user_id = user_context.get('user_id')
                    if not user_id:
                        # Fallback to MCP client discovery
                        user_id = await self.mcp_client._get_authenticated_user_id()
                        if not user_id:
                            print("[ERROR] No authenticated user ID available for comprehensive insights")
                            return {"error": "No authenticated user", "success": False}
                    print(f"[DEBUG] Using Google user ID from context: {user_id}")
                
                # Build arguments exactly as shown in Postman format
                arguments = {
                    "user_id": user_id,
                    "data_selections": data_selections,
                    "start_date": start_date,
                    "end_date": end_date,
                    "min_spend_threshold": 50,
                    "budget_increase_limit": 25
                }
                
                return await self.mcp_client.call_tool("get_comprehensive_insights", arguments)
            
            elif tool_name == "get_google_ads_accounts":
                # Get Google Ads accounts for the dynamically authenticated user
                return await self.mcp_client.get_google_ads_accounts()
                
            elif tool_name == "get_ga4_properties":
                # Get GA4 properties for the dynamically authenticated user  
                return await self.mcp_client.get_ga4_properties()
                
            elif tool_name == "get_meta_ads_accounts":
                # Get Meta Ads accounts for the dynamically authenticated user
                return await self.mcp_client.get_meta_ads_accounts()
                
            elif tool_name == "query_google_ads_data":
                # Query specific Google Ads data with focus_account support
                user_id = await self.mcp_client._get_authenticated_user_id()
                if not user_id:
                    return {"error": "No authenticated user", "success": False}
                
                # Resolve unified account ID to platform-specific IDs
                focus_account = user_context.get('focus_account') if user_context else None
                resolved_ids = self._resolve_account_ids(focus_account) if focus_account != 'all' else {'google_ads_id': None}
                customer_id = resolved_ids.get('google_ads_id')
                
                query_type = user_context.get('query_type', 'campaigns')  # Default to campaigns for marketing questions
                start_date = user_context.get('start_date')
                end_date = user_context.get('end_date')
                
                # Build arguments exactly as shown in Postman format
                arguments = {
                    "user_id": user_id,
                    "customer_id": customer_id,
                    "query_type": query_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "dimensions": None,
                    "metrics": None,
                    "custom_query": None
                }
                
                return await self.mcp_client.call_tool("query_google_ads_data", arguments)
                
            elif tool_name == "query_ga4_data":
                # Query specific GA4 data
                user_id = await self.mcp_client._get_authenticated_user_id()
                if not user_id:
                    return {"error": "No authenticated user", "success": False}
                
                # Resolve unified account ID to platform-specific IDs
                focus_account = user_context.get('focus_account') if user_context else None
                resolved_ids = self._resolve_account_ids(focus_account) if focus_account != 'all' else {'ga4_property_id': None}
                property_id = resolved_ids.get('ga4_property_id')
                
                query_type = user_context.get('query_type', 'overview')  # Default to overview
                start_date = user_context.get('start_date')
                end_date = user_context.get('end_date')
                
                # Build arguments exactly as shown in Postman format
                arguments = {
                    "user_id": user_id,
                    "property_id": property_id,
                    "query_type": query_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "dimensions": None,
                    "metrics": None,
                    "filters": None
                }
                
                return await self.mcp_client.call_tool("query_ga4_data", arguments)
                
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def _synthesize_insights(self, query: str, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize insights from tool results (simplified version)"""
        successful_tools = [r for r in tool_results if r['success']]
        failed_tools = [r for r in tool_results if not r['success']]
        
        insights = {
            "query_analysis": {
                "original_query": query,
                "tools_attempted": len(tool_results),
                "tools_successful": len(successful_tools),
                "tools_failed": len(failed_tools)
            },
            "data_availability": {},
            "key_findings": [],
            "recommendations": []
        }
        
        # Process successful results
        for result in successful_tools:
            tool_name = result['tool']
            data = result['data']
            
            if tool_name == "get_platform_examples" and data:
                if 'examples' in data:
                    insights['data_availability']['platforms'] = list(data['examples'].keys())
                if 'new_mcp_tools' in data:
                    insights['data_availability']['available_tools'] = list(data['new_mcp_tools'].keys())
                    
            elif tool_name == "get_comprehensive_insights" and data:
                if 'data_availability' in data:
                    insights['data_availability'].update(data['data_availability'])
                if 'analysis_period' in data:
                    insights['query_analysis']['analysis_period'] = data['analysis_period']
                    
            # Add tool-specific findings
            insights['key_findings'].append({
                "tool": tool_name,
                "status": "success",
                "summary": f"{tool_name} executed successfully",
                "data_points": len(str(data)) if data else 0
            })
        
        # Process failed results
        for result in failed_tools:
            insights['key_findings'].append({
                "tool": result['tool'],
                "status": "failed", 
                "error": result['data'].get('error', 'Unknown error')
            })
        
        # Generate recommendations
        if successful_tools:
            insights['recommendations'].append("✅ MCP tools are responding - integration is working")
        
        if failed_tools:
            insights['recommendations'].append("⚠️  Some MCP tools failed - may need authentication or parameter adjustment")
            
        if not successful_tools:
            insights['recommendations'].append("❌ All MCP tools failed - check authentication and server status")
        
        return insights
    
    async def get_tool_status(self) -> Dict[str, Any]:
        """Get status of all available MCP tools"""
        if not self.mcp_client:
            await self.initialize()
            
        status = {
            "mcp_client_ready": bool(self.mcp_client),
            "available_tools": list(self.tools.keys()),
            "tool_details": self.tools,
            "timestamp": datetime.now().isoformat()
        }
        
        return status


# Singleton instance
_adk_agent = None

async def get_adk_marketing_agent() -> ADKMarketingAgent:
    """Get singleton ADK marketing agent"""
    global _adk_agent
    if _adk_agent is None:
        _adk_agent = ADKMarketingAgent()
        await _adk_agent.initialize()
    return _adk_agent

async def reset_adk_marketing_agent() -> None:
    """Force reset the singleton ADK marketing agent to clear cached MCP session"""
    global _adk_agent
    if _adk_agent is not None:
        await _adk_agent.close()
        _adk_agent = None
    print("[MCP-RESET] ADK marketing agent singleton cleared")