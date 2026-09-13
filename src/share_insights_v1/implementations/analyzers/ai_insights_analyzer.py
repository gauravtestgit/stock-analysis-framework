from typing import Dict, Any, Optional, List
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
import json
import os
from datetime import datetime, timedelta
from ...implementations.llm_providers.llm_manager import LLMManager
from ...utils.prompt_formatter import PromptFormatter, create_company_insights_prompt, create_revenue_trends_prompt, create_etf_insights_prompt

class AIInsightsAnalyzer(IAnalyzer):
    """AI-powered analyzer for market insights and revenue trends"""
    
    def __init__(self, data_provider: IDataProvider, llm_manager=None):
        self.data_provider = data_provider
        self.llm_manager = llm_manager or LLMManager()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using AI insights for market analysis and revenue trends"""
        try:
            # Store ticker for use in helper methods
            self._current_ticker = ticker
            financial_metrics = data.get('financial_metrics', {})
            current_price = financial_metrics.get('current_price', 0)
            
            # Get current price from price data if not available in financial metrics
            if not current_price:
                price_data = data.get('price_data', {})
                price_history = price_data.get('price_history')
                if price_history is not None and not price_history.empty:
                    current_price = price_history['Close'].iloc[-1]
            
            # Get AI insights
            ai_insights = self._get_ai_insights(ticker, financial_metrics)
            
            # Focus on AI-powered market insights and revenue analysis
            # News sentiment is now handled by dedicated NewsSentimentAnalyzer
            
            # Analyze revenue trends
            revenue_trends = self._analyze_revenue_trends(financial_metrics)
            
            # Calculate target price first
            target_price = self._calculate_ai_target_price(current_price, ai_insights)
            
            # Generate AI recommendation based on target price and insights
            ai_recommendation = self._generate_ai_recommendation(
                ai_insights, revenue_trends, current_price, target_price
            )
            
            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(ai_insights, revenue_trends)

            return {
                'method': 'AI Insights Analysis',
                'applicable': True,
                'current_price': current_price,
                'predicted_price': target_price,
                'recommendation': ai_recommendation,
                'confidence': confidence,
                'ai_insights': ai_insights,
                'revenue_trends': revenue_trends,
                'market_analysis': self._get_market_analysis(ticker, financial_metrics),
                'ai_methods_used': {
                    'insights': ai_insights.get('ai_method', 'Unknown'),
                    'revenue_trends': revenue_trends.get('ai_method', 'Unknown')
                },
                'risk_factors': self._identify_ai_risk_factors(ai_insights),
                'analysis_type': 'ai_insights'
            }
            
        except Exception as e:
            return {'error': f"AI insights analysis failed: {str(e)}"}
    
    def _get_ai_insights(self, ticker: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI-powered insights about the company or ETF"""
        
        try:
            company_name = financial_metrics.get('long_name', ticker)
            quote_type = financial_metrics.get('quote_type', 'EQUITY')
            
            # Check if this is an ETF
            is_etf = ('ETF' in company_name.upper() or 
                     quote_type == 'ETF' or 
                     ticker.lower().endswith('.nz') and any(x in company_name.upper() for x in ['SMART', 'INDEX', 'FUND']))
            
            if is_etf:
                return self._get_etf_insights(ticker, company_name, financial_metrics)
            else:
                return self._get_company_insights(ticker, company_name, financial_metrics)
                
        except Exception as e:
            print(f"AI insights API error: {e}")
            fallback_insights = self._get_fallback_insights(ticker, financial_metrics)
            fallback_insights['ai_method'] = 'Fallback'
            return fallback_insights
    
    def _get_etf_insights(self, ticker: str, fund_name: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get ETF-specific insights"""
        
        # Get provider name for formatting
        provider_name = PromptFormatter.get_provider_name_from_llm_manager(self.llm_manager)
        
        # Determine market context
        market_context = self._get_market_context(ticker)
        
        # Prepare ETF info
        etf_info = {
            'name': f"{fund_name} ({ticker}) ETF",
            'fund_name': fund_name,
            'assets_under_management': f"${financial_metrics.get('market_cap', 0):,.0f}",
            'current_price': f"${financial_metrics.get('current_price', 0):.2f}",
            'pe_ratio': f"{financial_metrics.get('pe_ratio', 0):.2f}",
            'pb_ratio': financial_metrics.get('pb_ratio', 'N/A'),
            'market_context': market_context['market_name'],
            'analysis_notes': market_context['analysis_notes']
        }
        
        # Create universal prompt with ETF-specific context
        base_prompt = create_etf_insights_prompt(etf_info, provider_name)
        
        # Add ETF-specific considerations
        etf_considerations = f"""

IMPORTANT: {market_context['analysis_notes']}

Consider ETF-specific factors like:
- Fund size and liquidity relative to {market_context['market_name']} standards
- Expense ratios competitive within {market_context['market_name']}
- Tracking performance vs benchmark
- Geographic/sector concentration
- Provider reputation in {market_context['market_name']}"""
        
        prompt = base_prompt + etf_considerations
        
        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")
        
        json_str = self._extract_json_from_response(response)
        try:
            insights = json.loads(json_str)
            insights = self._ensure_required_insight_fields(insights)
            insights['ai_method'] = 'LLM'
            return insights
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")

    def _get_company_insights(self, ticker: str, company_name: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get company-specific insights"""

        # Get provider name for formatting
        provider_name = PromptFormatter.get_provider_name_from_llm_manager(self.llm_manager)

        # Prepare company info - includes business_summary (what the company actually
        # does, from yfinance's longBusinessSummary) and valuation/margin context that
        # was previously fetched elsewhere in the pipeline but never passed into this
        # prompt, leaving the LLM to guess from 6 bare numbers alone.
        business_summary = (financial_metrics.get('business_summary') or '').strip()
        if len(business_summary) > 600:
            business_summary = business_summary[:600].rsplit(' ', 1)[0] + '...'

        company_info = {
            'name': f"{company_name} ({ticker})",
            'sector': financial_metrics.get('sector', 'Unknown'),
            'industry': financial_metrics.get('industry', 'Unknown'),
            'business_summary': business_summary or 'Not available',
            'market_cap': f"${financial_metrics.get('market_cap', 0):,.0f}",
            'revenue_growth': f"{financial_metrics.get('yearly_revenue_growth', 0):.1%}",
            'roe': f"{financial_metrics.get('roe', 0) or 0:.1%}",
            'pe_ratio': financial_metrics.get('pe_ratio') or 'N/A',
            'pb_ratio': financial_metrics.get('pb_ratio') or 'N/A',
            'profit_margin': f"{financial_metrics.get('profit_margin', 0) or 0:.1f}%",
            'debt_to_equity': financial_metrics.get('debt_to_equity') or 'N/A',
        }
        
        # Create universal prompt
        prompt = create_company_insights_prompt(company_info, provider_name)
        
        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")
        
        json_str = self._extract_json_from_response(response)
        try:
            insights = json.loads(json_str)
            insights = self._ensure_required_insight_fields(insights)
            insights['ai_method'] = 'LLM'
            return insights
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")

    def _ensure_required_insight_fields(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Backfill any schema fields the LLM's JSON response omitted.

        Confirmed via direct testing that the same model/provider can include
        investment_thesis on one call and drop it on another (ordinary LLM sampling
        variance, not a bug in the prompt/parsing) - since it's the main content of
        this analyzer's output, silently rendering nothing for it isn't acceptable, so
        a missing thesis gets synthesized from whatever strengths/risks did come back
        (still real, specific content) rather than a fully generic placeholder.
        """
        if not insights.get('investment_thesis'):
            strengths = insights.get('key_strengths') or []
            risks = insights.get('key_risks') or []
            if strengths or risks:
                parts = []
                if strengths:
                    parts.append(strengths[0])
                if risks:
                    parts.append(f"Key risk: {risks[0]}")
                insights['investment_thesis'] = '. '.join(parts) + '.'
            else:
                insights['investment_thesis'] = 'No detailed thesis available for this analysis.'

        insights.setdefault('qualitative_stance', 'Neutral')
        insights.setdefault('conviction', 'Low')
        insights.setdefault('key_strengths', [])
        insights.setdefault('key_risks', [])

        # target_price_multiplier: prefer the LLM's own number, but fall back to a
        # stance-aware default - not a flat 1.0 - whenever it's missing, unparseable,
        # contradicts the stated stance, or is an out-of-range hallucination (e.g. 5.0
        # or -0.2). A flat 1.0 ignored the one thing we still know (the stance) even for
        # a clearly Bearish call. target_price_multiplier_source records which happened,
        # since a fallback value should never be indistinguishable from a genuine
        # reasoned LLM estimate to anything consuming this downstream.
        stance = insights.get('qualitative_stance')
        fallback_multiplier = {'Bullish': 1.05, 'Bearish': 0.95}.get(stance, 1.0)
        used_fallback = False

        if 'target_price_multiplier' not in insights:
            multiplier = fallback_multiplier
            used_fallback = True
        else:
            try:
                multiplier = float(insights['target_price_multiplier'])
            except (TypeError, ValueError):
                multiplier = fallback_multiplier
                used_fallback = True

        # Guard against the stance and the numeric multiplier disagreeing - confirmed
        # via live testing that a response can say "Bullish" while its
        # target_price_multiplier is still below 1.0 (implying downside), which then
        # mechanically produces a Sell recommendation despite a bullish thesis. This is
        # LLM sampling variance on the numeric field specifically (more pronounced on
        # smaller/faster models), not something the prompt wording can fully prevent.
        if stance == 'Bullish' and multiplier < 1.0:
            multiplier = fallback_multiplier
            used_fallback = True
        elif stance == 'Bearish' and multiplier > 1.0:
            multiplier = fallback_multiplier
            used_fallback = True
        elif not (0.5 <= multiplier <= 2.0):
            multiplier = fallback_multiplier
            used_fallback = True

        insights['target_price_multiplier'] = multiplier
        insights['target_price_multiplier_source'] = 'fallback' if used_fallback else 'llm'

        return insights

    def _analyze_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze revenue trends using AI (or performance trends for ETFs)"""
        
        try:
            company_name = financial_metrics.get('long_name', '')
            quote_type = financial_metrics.get('quote_type', 'EQUITY')
            
            # Check if this is an ETF
            is_etf = ('ETF' in company_name.upper() or 
                     quote_type == 'ETF' or 
                     any(x in company_name.upper() for x in ['SMART', 'INDEX', 'FUND']))
            
            if is_etf:
                return self._analyze_etf_performance_trends(financial_metrics)
            else:
                return self._analyze_company_revenue_trends(financial_metrics)
                
        except Exception as e:
            print(f"Revenue trends API error: {e}")
            fallback_trends = self._get_fallback_revenue_trends(financial_metrics)
            fallback_trends['ai_method'] = 'Fallback'
            return fallback_trends
    
    def _analyze_etf_performance_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ETF performance trends"""
        
        current_price = financial_metrics.get('current_price', 0)
        high_52w = financial_metrics.get('fifty_two_week_high', 0)
        low_52w = financial_metrics.get('fifty_two_week_low', 0)
        market_cap = financial_metrics.get('market_cap', 0)
        
        # Calculate performance metrics
        if high_52w and low_52w and current_price:
            ytd_range_position = (current_price - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5
        else:
            ytd_range_position = 0.5
        
        # Get market context - need ticker from somewhere
        ticker = getattr(self, '_current_ticker', '')
        market_context = self._get_market_context(ticker)
        
        prompt = f"""Analyze ETF performance trends for {market_context['market_name']} market:
- Current Price: ${current_price:.2f}
- 52-week High: ${high_52w:.2f}
- 52-week Low: ${low_52w:.2f}
- Position in Range: {ytd_range_position:.1%}
- Assets Under Management: ${market_cap:,.0f}
- Market Context: {market_context['market_name']}

Provide ETF performance analysis in JSON format:
{{
    "trend_assessment": "Strong Performance/Moderate Performance/Stable/Declining",
    "growth_consistency": "Consistent/Variable/Volatile",
    "future_outlook": "Very Positive/Positive/Neutral/Cautious/Negative",
    "trend_commentary": "1-2 sentences on what's specifically driving this position in its range"
}}

IMPORTANT: {market_context['analysis_notes']}

Consider factors like:
- Price performance vs 52-week range
- Fund size stability relative to {market_context['market_name']} market
- Market conditions for underlying assets in {market_context['region']}"""

        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")

        json_str = self._extract_json_from_response(response)
        try:
            trends = json.loads(json_str)
            # growth_rate comes from the already-computed input value, not the LLM -
            # same reasoning as _analyze_company_revenue_trends.
            trends['growth_rate'] = ytd_range_position
            trends['ai_method'] = 'LLM'
            return trends
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")
    
    def _analyze_company_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze company revenue trends"""

        # Get provider name for formatting
        provider_name = PromptFormatter.get_provider_name_from_llm_manager(self.llm_manager)

        # Prepare company info
        company_info = {
            'current_revenue_growth': f"{financial_metrics.get('revenue_growth', 0) or 0:.1%}",
            'yearly_revenue_growth': f"{financial_metrics.get('yearly_revenue_growth', 0) or 0:.1%}",
            'total_revenue': f"${financial_metrics.get('total_revenue', 0) or 0:,.0f}"
        }

        # Create universal prompt
        prompt = create_revenue_trends_prompt(company_info, provider_name)

        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")

        json_str = self._extract_json_from_response(response)
        try:
            trends = json.loads(json_str)
            # growth_rate comes from the known input, not the LLM - the schema no
            # longer asks for it (see create_revenue_trends_prompt's docstring for why).
            trends['growth_rate'] = financial_metrics.get('yearly_revenue_growth', 0) or 0
            trends['ai_method'] = 'LLM'
            return trends
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")
    
    def _generate_ai_recommendation(self, ai_insights: Dict, revenue_trends: Dict, current_price: float, target_price: float) -> str:
        """Generate recommendation based on target price and AI insights"""

        # Primary logic: base recommendation on price target vs current price
        if current_price > 0 and target_price > 0:
            upside_pct = ((target_price - current_price) / current_price) * 100

            # Base recommendation on upside/downside
            if upside_pct > 15:
                base_recommendation = 'Strong Buy'
            elif upside_pct > 5:
                base_recommendation = 'Buy'
            elif upside_pct < -15:
                base_recommendation = 'Strong Sell'
            elif upside_pct < -5:
                base_recommendation = 'Sell'
            else:
                base_recommendation = 'Hold'

            # Adjust based on qualitative factors (but don't contradict price logic).
            # Uses the LLM's own stated stance/conviction and revenue outlook, rather
            # than the old market_position/competitive_advantage/industry_outlook
            # categorical fields (removed - see create_company_insights_prompt).
            risk_factors = 0
            if ai_insights.get('qualitative_stance') == 'Bearish':
                risk_factors += 1
            if revenue_trends.get('future_outlook') in ('Negative', 'Cautious'):
                risk_factors += 1
            if ai_insights.get('conviction') == 'Low' and ai_insights.get('qualitative_stance') != 'Bullish':
                risk_factors += 1

            # Only downgrade recommendation if significant risks and marginal upside
            if risk_factors >= 2 and upside_pct < 10:
                if base_recommendation == 'Strong Buy':
                    return 'Buy'
                elif base_recommendation == 'Buy':
                    return 'Hold'

            return base_recommendation

        # Fallback to qualitative assessment if no price data
        return self._get_fallback_recommendation(ai_insights, revenue_trends)

    def _calculate_ai_target_price(self, current_price: float, ai_insights: Dict) -> float:
        """Calculate AI-based target price from the LLM's own stated
        target_price_multiplier, instead of a fixed formula bolted onto categorical
        labels that ignored key_strengths/key_risks entirely. Clamped to a sane range
        since this now trusts a number the LLM produced directly, not a hand-picked
        step function - guards against an occasional wild/malformed value."""

        if not current_price:
            return 0

        try:
            multiplier = float(ai_insights.get('target_price_multiplier', 1.0))
        except (TypeError, ValueError):
            multiplier = 1.0

        multiplier = max(0.5, min(multiplier, 2.0))

        return current_price * multiplier
    
    def _calculate_confidence(self, ai_insights: Dict, revenue_trends: Dict) -> str:
        """Calculate confidence level, using the LLM's own stated conviction when a
        real LLM call produced it - a fallback (hardcoded, generic guess) should never
        be reported as anything but Low confidence regardless of what it contains."""

        if ai_insights.get('ai_method') != 'LLM' or revenue_trends.get('ai_method') != 'LLM':
            return 'Low'

        conviction = ai_insights.get('conviction', 'Medium')
        consistency = revenue_trends.get('growth_consistency')

        if conviction == 'High' and consistency == 'Consistent':
            return 'High'
        if conviction == 'Low' or consistency == 'Volatile':
            return 'Low'
        return 'Medium'
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response that may contain markdown code blocks"""
        import re
        
        # First try to find JSON in markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find JSON in regular code blocks
        json_match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            potential_json = json_match.group(1).strip()
            if potential_json.startswith('{') and potential_json.endswith('}'):
                return potential_json
        
        # Try to find JSON object in the text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # If no JSON found, return original response
        return response
    
    def _assess_market_position(self, financial_metrics: Dict) -> str:
        """Assess market position based on financial metrics"""
        
        market_cap = financial_metrics.get('market_cap', 0)
        roe = financial_metrics.get('roe', 0)
        
        if market_cap > 100_000_000_000 and roe > 0.15:  # Large cap with good ROE
            return 'Strong'
        elif market_cap > 10_000_000_000 and roe > 0.10:  # Mid cap with decent ROE
            return 'Moderate'
        else:
            return 'Weak'
    
    def _assess_growth_prospects(self, financial_metrics: Dict) -> str:
        """Assess growth prospects based on financial metrics"""
        
        revenue_growth = financial_metrics.get('yearly_revenue_growth', 0)
        earnings_growth = financial_metrics.get('earnings_growth', 0)
        
        if revenue_growth > 0.20 and earnings_growth > 0.15:
            return 'High'
        elif revenue_growth > 0.10 and earnings_growth > 0.05:
            return 'Moderate'
        else:
            return 'Low'
    
    def _get_fallback_insights(self, ticker: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback insights when AI is not available - purely rule-based from
        financial metrics, matching the LLM schema's shape (see
        create_company_insights_prompt) so downstream code never needs to
        special-case the fallback path. conviction is always Low here since this
        is a mechanical guess, never a reasoned assessment."""
        market_position = self._assess_market_position(financial_metrics)
        growth_prospects = self._assess_growth_prospects(financial_metrics)

        if market_position == 'Strong' and growth_prospects == 'High':
            stance, multiplier = 'Bullish', 1.10
        elif market_position == 'Weak' and growth_prospects == 'Low':
            stance, multiplier = 'Bearish', 0.95
        else:
            stance, multiplier = 'Neutral', 1.0

        return {
            'investment_thesis': (
                f"Rule-based fallback: {market_position.lower()} market position with "
                f"{growth_prospects.lower()} growth prospects based on available financial "
                f"metrics (LLM analysis unavailable)."
            ),
            'qualitative_stance': stance,
            'target_price_multiplier': multiplier,
            'target_price_multiplier_source': 'fallback',
            'conviction': 'Low',
            'key_strengths': ['Financial stability'],
            'key_risks': ['Market volatility']
        }

    def _get_fallback_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback revenue trends when AI is not available"""
        yearly_growth = financial_metrics.get('yearly_revenue_growth', 0) or 0

        if yearly_growth > 0.15:
            trend_assessment = 'Strong Growth'
        elif yearly_growth > 0.05:
            trend_assessment = 'Moderate Growth'
        elif yearly_growth > -0.05:
            trend_assessment = 'Stable'
        else:
            trend_assessment = 'Declining'

        return {
            'trend_assessment': trend_assessment,
            'growth_rate': yearly_growth,
            'growth_consistency': 'Consistent',
            'future_outlook': 'Positive' if yearly_growth > 0 else 'Cautious',
            'trend_commentary': 'Derived from historical revenue growth only (LLM analysis unavailable).'
        }

    def _get_fallback_recommendation(self, ai_insights: Dict, revenue_trends: Dict) -> str:
        """Fallback recommendation when price-based logic can't be used"""
        stance = ai_insights.get('qualitative_stance')
        trend = revenue_trends.get('trend_assessment')

        positive_factors = 0
        negative_factors = 0

        if stance == 'Bullish':
            positive_factors += 2
        elif stance == 'Bearish':
            negative_factors += 1

        if trend in ('Strong Growth', 'Moderate Growth'):
            positive_factors += 1
        elif trend == 'Declining':
            negative_factors += 2

        net_score = positive_factors - negative_factors

        if net_score >= 3:
            return 'Strong Buy'
        elif net_score >= 1:
            return 'Buy'
        elif net_score <= -3:
            return 'Strong Sell'
        elif net_score <= -1:
            return 'Sell'
        else:
            return 'Hold'
    

    
    def _identify_ai_risk_factors(self, ai_insights: Dict) -> list:
        """Identify risk factors from AI insights.

        Previously checked 4 categorical fields (market_position=='Weak', etc.) that
        have since been removed from the schema - that logic silently returned an
        empty list whenever none of those specific values came back (which was most of
        the time), even when key_risks already contained several real, specific risks
        one level up in the same result. Just surface those directly instead.
        """
        return list(ai_insights.get('key_risks', []) or [])
    
    def _get_market_analysis(self, ticker: str, financial_metrics: Dict) -> Dict[str, Any]:
        """Get market analysis summary"""
        return {
            'market_cap_category': self._get_market_cap_category(financial_metrics.get('market_cap', 0)),
            'sector': financial_metrics.get('sector', 'Unknown'),
            'industry': financial_metrics.get('industry', 'Unknown'),
            'beta': financial_metrics.get('beta', 1.0)
        }
    
    def _get_market_cap_category(self, market_cap: float) -> str:
        """Categorize market cap"""
        if market_cap > 200_000_000_000:
            return 'Mega Cap'
        elif market_cap > 10_000_000_000:
            return 'Large Cap'
        elif market_cap > 2_000_000_000:
            return 'Mid Cap'
        elif market_cap > 300_000_000:
            return 'Small Cap'
        else:
            return 'Micro Cap'
    
    def _get_market_context(self, ticker: str) -> Dict[str, str]:
        """Get market-specific context for analysis"""
        ticker_lower = ticker.lower()
        
        if ticker_lower.endswith('.nz'):
            return {
                'market_name': 'New Zealand (NZX)',
                'region': 'New Zealand/Australia',
                'analysis_notes': 'Analyze relative to NZ market standards. Lower trading volumes and smaller fund sizes are normal for NZ ETFs. Focus on NZ-specific factors like currency exposure and local market dynamics.'
            }
        elif ticker_lower.endswith('.ax') or ticker_lower.endswith('.asx'):
            return {
                'market_name': 'Australian (ASX)',
                'region': 'Australia',
                'analysis_notes': 'Analyze relative to Australian market standards. Consider ASX-specific factors and regional market dynamics.'
            }
        elif ticker_lower.endswith('.l') or ticker_lower.endswith('.lon'):
            return {
                'market_name': 'London (LSE)',
                'region': 'United Kingdom/Europe',
                'analysis_notes': 'Analyze relative to UK/European market standards. Consider Brexit impacts and European market dynamics.'
            }
        else:
            return {
                'market_name': 'US Market',
                'region': 'United States',
                'analysis_notes': 'Analyze relative to US market standards with typical US ETF benchmarks for volume and fund size.'
            }
    
    def is_applicable(self, company_type: str) -> bool:
        """AI insights applicable to all company types"""
        return True