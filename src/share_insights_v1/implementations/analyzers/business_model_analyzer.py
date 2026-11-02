from typing import Dict, Any, Optional, List, Tuple
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...interfaces.sec_data_provider import SECDataProvider
from ...models.business_model import (
    BusinessModelReport, RevenueStreamAnalysis, BusinessModelType,
    RevenueStreamType, RevenueQuality
)
from ...models.company import CompanyType
import numpy as np
import json
import os
import re
import yaml
from ...implementations.llm_providers.llm_manager import LLMManager
from ...utils.debug_printer import debug_print
from ...utils.json_extractor import extract_json_from_llm_response
from ...utils.filing_text_tools import select_keyword_context, scan_pass_through

class BusinessModelAnalyzer(IAnalyzer):
    """Analyzer for business model and revenue stream analysis"""

    # Bump whenever this analyzer's logic changes meaningfully (prompt
    # schema, slice selection, consistency checks, etc.) - a cached result
    # keyed by an old version is never read, so a logic change can't be
    # silently masked by a stale cache hit.
    _ANALYZER_VERSION = 'v2-structured-segments-and-drivers'
    _CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'cache', 'business_model_analyzer')

    def __init__(self, data_provider: IDataProvider, llm_manager: Optional['LLMManager'] = None, sec_provider: Optional[SECDataProvider] = None):
        self.data_provider = data_provider
        self.llm_manager = llm_manager
        # Default to SECEdgarProvider if no SEC provider is provided
        if sec_provider is None:
            from ...implementations.data_providers.sec_edgar_provider import SECEdgarProvider
            self.sec_provider = SECEdgarProvider()
        else:
            self.sec_provider = sec_provider
        
        # Industry to business model mappings
        self.industry_business_models = {
            'Software - Application': BusinessModelType.B2B_SAAS,
            'Software - Infrastructure': BusinessModelType.B2B_SAAS,
            'Internet Content & Information': BusinessModelType.ADVERTISING_BASED,
            'Consumer Electronics': BusinessModelType.MANUFACTURING,
            'Auto Manufacturers': BusinessModelType.MANUFACTURING,
            'Banks - Regional': BusinessModelType.FINANCIAL_SERVICES,
            'Banks - Diversified': BusinessModelType.FINANCIAL_SERVICES,
            'Insurance': BusinessModelType.FINANCIAL_SERVICES,
            'Real Estate': BusinessModelType.ASSET_HEAVY,
            'Restaurants': BusinessModelType.TRADITIONAL_RETAIL,
            'Specialty Retail': BusinessModelType.TRADITIONAL_RETAIL,
            'Internet Retail': BusinessModelType.MARKETPLACE,
            'Entertainment': BusinessModelType.B2C_SUBSCRIPTION,
            'Biotechnology': BusinessModelType.MANUFACTURING
        }
    
    def _cache_path(self, ticker: str, accession_number: str) -> str:
        safe_accession = re.sub(r'[^A-Za-z0-9_-]', '_', accession_number)
        return os.path.join(self._CACHE_DIR, f"{ticker}_{safe_accession}_{self._ANALYZER_VERSION}.json")

    def _read_cache(self, ticker: str, accession_number: Optional[str]) -> Optional[Dict[str, Any]]:
        """Cache keyed by (ticker, filing accession number, analyzer
        version) - a re-run against the SAME filing returns the same
        result rather than a fresh (and, at temperature=0.1 previously,
        non-identical) LLM call. No accession number (non-SEC-filing
        ticker) means nothing to key by, so caching is skipped entirely."""
        if not accession_number:
            return None
        path = self._cache_path(ticker, accession_number)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            debug_print(f"[BM_DEBUG] Could not read cache for {ticker}: {e}")
            return None

    def _write_cache(self, ticker: str, accession_number: Optional[str], result: Dict[str, Any]) -> None:
        if not accession_number:
            return
        try:
            os.makedirs(self._CACHE_DIR, exist_ok=True)
            with open(self._cache_path(ticker, accession_number), 'w', encoding='utf-8') as f:
                json.dump(result, f, default=str)
        except Exception as e:
            debug_print(f"[BM_DEBUG] Could not write cache for {ticker}: {e}")

    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze business model and revenue streams"""
        try:
            company_info = data.get('company_info', {})
            financial_metrics = data.get('financial_metrics', {})

            debug_print(f"[BM_DEBUG] Analyzing {ticker}: sector={company_info.get('sector')}, industry={company_info.get('industry')}")

            accession_number = None
            if self.sec_provider:
                try:
                    filing = self.sec_provider.get_latest_10k(ticker)
                    accession_number = filing.get('accession_number') if filing else None
                except Exception as e:
                    debug_print(f"[BM_DEBUG] Could not resolve filing accession for {ticker}: {e}")

            cached = self._read_cache(ticker, accession_number)
            if cached is not None:
                debug_print(f"[BM_DEBUG] Using cached result for {ticker} (accession {accession_number})")
                return cached

            # Get business model report
            report = self.analyze_business_model(ticker, company_info, financial_metrics)
            
            if not report:
                debug_print(f"[BM_DEBUG] No report generated for {ticker}")
                return {'error': 'Could not analyze business model'}
            
            debug_print(f"[BM_DEBUG] Generated report for {ticker}: type={report.business_model_type.value}")
            
            # Convert to standardized format
            result = {
                'method': 'Business Model Analysis',
                'applicable': True,
                'business_model_type': report.business_model_type.value,
                'primary_revenue_stream': report.revenue_stream_analysis.primary_stream.value,
                'revenue_quality': report.revenue_quality.value,
                'recurring_percentage': report.revenue_stream_analysis.recurring_percentage,
                'scalability_score': report.scalability_score,
                'growth_consistency': report.revenue_stream_analysis.growth_consistency,
                'strengths': report.strengths,
                'risks': report.risks,
                'competitive_moat': report.competitive_moat,
                'confidence': 'Medium',
                'recommendation': self._generate_recommendation(report)
            }
            
            # Add product portfolio, competitive differentiation, and segment revenue data
            if hasattr(report, 'product_portfolio') and report.product_portfolio:
                result['product_portfolio'] = report.product_portfolio
            
            if hasattr(report, 'competitive_differentiation') and report.competitive_differentiation:
                result['competitive_differentiation'] = report.competitive_differentiation
            
            if hasattr(report, 'segment_revenue_data') and report.segment_revenue_data:
                result['segment_revenue_data'] = report.segment_revenue_data
            
            # Add complete SEC Edgar data
            if hasattr(report, 'sec_edgar_data') and report.sec_edgar_data:
                result['sec_edgar_data'] = report.sec_edgar_data

            # Which text slice each prompt actually received - grounding
            # transparency for debugging, not shown in the normal UI.
            if hasattr(report, 'slice_log') and report.slice_log:
                result['slice_log'] = report.slice_log

            self._write_cache(ticker, accession_number, result)
            debug_print(f"[BM_DEBUG] Returning result for {ticker}: {result.get('business_model_type')}")
            return result
            
        except Exception as e:
            debug_print(f"[BM_DEBUG] Error analyzing {ticker}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def is_applicable(self, company_type: str) -> bool:
        """Business model analysis applies to most company types"""
        excluded_types = [CompanyType.ETF.value]
        return company_type not in excluded_types
    
    def analyze_business_model(self, ticker: str, company_info: Dict[str, Any], 
                             financial_metrics: Dict[str, Any]) -> Optional[BusinessModelReport]:
        """Perform detailed business model analysis"""
        
                   
        sector = company_info.get('sector', '')
        industry = company_info.get('industry', '')
        
        
        # Determine business model type
        business_model_type = self._classify_business_model(sector, industry, financial_metrics)
        
        # Analyze revenue streams (SEC Edgar first, then LLM fallback)
        try:
            revenue_stream_analysis = self._analyze_revenue_streams(
                ticker, business_model_type, financial_metrics
            )
        except Exception as e:
            debug_print(f"[BM_DEBUG] Revenue stream analysis failed for {ticker}: {e}")
            return None
        
        # Assess revenue quality
        revenue_quality = self._assess_revenue_quality(revenue_stream_analysis, financial_metrics)
        
        # Calculate key metrics
        key_metrics = self._calculate_key_metrics(financial_metrics, business_model_type)

        # Fetch the SEC 10-K Item 1 Business section once, up front - the full
        # section (tens of thousands of characters, uncapped - see
        # SECEdgarProvider.get_business_description), not a fixed first-N-chars
        # cut. Each prompt below selects its own ~5k-char slice out of this
        # full text, rather than every prompt getting the same arbitrary first
        # 5k chars regardless of relevance.
        sec_business_data = None
        if self.sec_provider:
            try:
                sec_business_data = self.sec_provider.get_business_description(ticker)
            except Exception as e:
                debug_print(f"[BM_DEBUG] SEC business data fetch failed for {ticker}: {e}")

        # Real, filing-sourced per-segment revenue/profit (10-K + 10-Q) when
        # parseable - see SECEdgarProvider.get_segment_financials. Used to
        # ground segment numbers in actual data instead of an LLM estimate,
        # and to drive the product-portfolio slice selector below (grab the
        # paragraphs that actually introduce each real segment by name).
        segment_financials = None
        if self.sec_provider:
            try:
                segment_financials = self.sec_provider.get_segment_financials(ticker)
            except Exception as e:
                debug_print(f"[BM_DEBUG] Segment financials fetch failed for {ticker}: {e}")

        # Per-prompt slice selection log (which method/slice each prompt got),
        # for grounding transparency/debugging - reset per analysis run.
        self._slice_log: Dict[str, Any] = {}

        # Enhanced: Analyze product portfolio, competitive differentiation, and segment revenue
        product_analysis = self._analyze_product_portfolio(ticker, company_info, financial_metrics, sec_business_data, segment_financials)
        competitive_differentiation = self._analyze_competitive_differentiation(ticker, company_info, product_analysis, financial_metrics, sec_business_data)
        segment_revenue_data = self._extract_segment_revenue_data(ticker, company_info, financial_metrics, product_analysis, sec_business_data, segment_financials)
        
        # Collect SEC Edgar data
        sec_edgar_data = self._collect_sec_edgar_data(ticker)
        
        # Generate insights (now includes product and competitive insights)
        strengths, risks = self._generate_insights(
            business_model_type, revenue_stream_analysis, key_metrics, product_analysis, competitive_differentiation
        )
        
        # Assess competitive moat (enhanced with product differentiation)
        competitive_moat = self._assess_competitive_moat(business_model_type, key_metrics, competitive_differentiation)
        
        # Calculate scalability score
        scalability_score = self._calculate_scalability_score(
            business_model_type, revenue_stream_analysis, key_metrics
        )
        
        # Store product and competitive analysis separately
        report = BusinessModelReport(
            ticker=ticker,
            business_model_type=business_model_type,
            revenue_stream_analysis=revenue_stream_analysis,
            revenue_quality=revenue_quality,
            key_metrics=key_metrics,
            strengths=strengths,
            risks=risks,
            competitive_moat=competitive_moat,
            scalability_score=scalability_score
        )
        
        # Add enhanced data as attributes
        report.product_portfolio = product_analysis
        report.competitive_differentiation = competitive_differentiation
        report.segment_revenue_data = segment_revenue_data
        report.sec_edgar_data = sec_edgar_data
        report.slice_log = self._slice_log

        return report
    
    def _classify_business_model(self, sector: str, industry: str, 
                               financial_metrics: Dict[str, Any]) -> BusinessModelType:
        """Classify business model using LLM analysis with hardcoded fallback"""
        
        # Try LLM-powered classification first
        try:
            llm_result = self._classify_with_llm(sector, industry, financial_metrics)
            if llm_result:
                return llm_result
        except Exception:
            pass  # Fall back to hardcoded logic
        
        # Fallback to hardcoded logic
        return self._classify_hardcoded(sector, industry, financial_metrics)
    
    def _classify_with_llm(self, sector: str, industry: str, 
                          financial_metrics: Dict[str, Any]) -> Optional[BusinessModelType]:
        """Use LLM to classify business model"""
        try:
            # Use injected LLM manager if available, otherwise create new one
            llm_manager = self.llm_manager or LLMManager()
            
            company_name = financial_metrics.get('long_name', 'Unknown')
            revenue = financial_metrics.get('total_revenue', 0)
            
            prompt = f"""
Analyze the business model for this company and classify it into one of these categories:

Business Model Types:
- B2B_SAAS: Software-as-a-Service for businesses
- B2C_SUBSCRIPTION: Consumer subscription services  
- MARKETPLACE: Platform connecting buyers/sellers
- TRADITIONAL_RETAIL: Physical/online retail sales
- MANUFACTURING: Product manufacturing and sales
- FINANCIAL_SERVICES: Banking, insurance, financial products
- ADVERTISING_BASED: Revenue from advertising
- ASSET_HEAVY: Real estate, infrastructure, rental income
- PLATFORM: Multi-sided platform with ecosystem effects

Company Information:
- Name: {company_name}
- Sector: {sector}
- Industry: {industry}
- Annual Revenue: ${revenue:,.0f}

Respond with ONLY the business model type (e.g., "PLATFORM", "B2B_SAAS", etc.)
"""
            
            response = llm_manager.generate_response(prompt, temperature=0)
            result = response.strip().upper()
            
            # Map response to enum
            model_mapping = {
                'B2B_SAAS': BusinessModelType.B2B_SAAS,
                'B2C_SUBSCRIPTION': BusinessModelType.B2C_SUBSCRIPTION,
                'MARKETPLACE': BusinessModelType.MARKETPLACE,
                'TRADITIONAL_RETAIL': BusinessModelType.TRADITIONAL_RETAIL,
                'MANUFACTURING': BusinessModelType.MANUFACTURING,
                'FINANCIAL_SERVICES': BusinessModelType.FINANCIAL_SERVICES,
                'ADVERTISING_BASED': BusinessModelType.ADVERTISING_BASED,
                'ASSET_HEAVY': BusinessModelType.ASSET_HEAVY,
                'PLATFORM': BusinessModelType.PLATFORM
            }
            
            return model_mapping.get(result)
            
        except Exception:
            return None
    
    def _classify_hardcoded(self, sector: str, industry: str, 
                           financial_metrics: Dict[str, Any]) -> BusinessModelType:
        """Hardcoded classification logic as fallback"""
        
        # Special cases for major platform companies
        company_name = financial_metrics.get('long_name', '').lower()
        
        # Platform/Ecosystem companies
        platform_indicators = ['apple', 'google', 'alphabet', 'microsoft', 'amazon', 'meta', 'facebook']
        if any(indicator in company_name for indicator in platform_indicators):
            return BusinessModelType.PLATFORM
        
        # Check for mixed business model indicators
        revenue = financial_metrics.get('total_revenue', 0)
        services_revenue_indicators = [
            financial_metrics.get('services_revenue', 0),
            financial_metrics.get('subscription_revenue', 0)
        ]
        
        # If services revenue is significant (>20% of total), likely mixed/platform
        total_services = sum(x for x in services_revenue_indicators if x)
        if revenue > 0 and total_services / revenue > 0.2:
            return BusinessModelType.PLATFORM
        
        # Try industry mapping
        if industry in self.industry_business_models:
            return self.industry_business_models[industry]
        
        # Enhanced sector-based classification
        if 'Technology' in sector:
            if 'Software' in industry:
                return BusinessModelType.B2B_SAAS
            elif 'Consumer Electronics' in industry:
                return BusinessModelType.PLATFORM  # Most tech hardware companies have services
            else:
                return BusinessModelType.B2B_SAAS
        elif 'Financial' in sector:
            return BusinessModelType.FINANCIAL_SERVICES
        elif 'Consumer Cyclical' in sector:
            if 'Internet Retail' in industry or 'E-Commerce' in industry:
                return BusinessModelType.MARKETPLACE
            else:
                return BusinessModelType.TRADITIONAL_RETAIL
        elif 'Communication' in sector:
            return BusinessModelType.B2C_SUBSCRIPTION
        elif 'Healthcare' in sector:
            if 'Biotechnology' in industry:
                return BusinessModelType.MANUFACTURING
            else:
                return BusinessModelType.B2B_SAAS  # Many health tech companies
        else:
            return BusinessModelType.MANUFACTURING
    
    def _analyze_revenue_streams(self, ticker: str, business_model_type: BusinessModelType,
                               financial_metrics: Dict[str, Any]) -> RevenueStreamAnalysis:
        """Analyze revenue stream characteristics using SEC Edgar data first, then LLM fallback"""
        
        debug_print(f"[BM_DEBUG] Analyzing revenue streams for {ticker}")
        
        # Try SEC Edgar data first
        sec_result = self._analyze_revenue_streams_from_sec(ticker)
        if sec_result:
            debug_print(f"[BM_DEBUG] Using SEC Edgar revenue stream data for {ticker}")
            return sec_result
        
        # Fallback to LLM analysis
        llm_result = self._analyze_revenue_streams_from_llm(ticker, business_model_type, financial_metrics)
        if llm_result:
            debug_print(f"[BM_DEBUG] Using LLM revenue stream data for {ticker}")
            return llm_result
        
        # Last resort: return default analysis for pre-revenue companies
        debug_print(f"[BM_DEBUG] Returning default analysis for pre-revenue company {ticker}")
        return RevenueStreamAnalysis(
            primary_stream=RevenueStreamType.MIXED,
            secondary_streams=[],
            recurring_percentage=0.0,
            growth_consistency=None
        )
    
    def _analyze_revenue_streams_from_sec(self, ticker: str) -> Optional[RevenueStreamAnalysis]:
        """Analyze revenue streams from SEC Edgar XBRL data"""
        try:
            if not self.sec_provider:
                return None
            
            facts = self.sec_provider.get_filing_facts(ticker)
            if not facts or 'facts' not in facts:
                debug_print(f"[BM_DEBUG] No SEC facts data for {ticker}")
                return None
            
            us_gaap = facts['facts'].get('us-gaap', {})
            debug_print(f"[BM_DEBUG] SEC XBRL fields available for {ticker}: {len(us_gaap)} total fields")
            
            # Generic revenue field detection
            revenue_keywords = {
                'revenue': RevenueStreamType.MIXED,
                'sales': RevenueStreamType.PRODUCT_SALES,
                'subscription': RevenueStreamType.SUBSCRIPTION,
                'service': RevenueStreamType.SUBSCRIPTION,
                'interest': RevenueStreamType.INTEREST_INCOME,
                'commission': RevenueStreamType.TRANSACTION_FEES,
                'fee': RevenueStreamType.TRANSACTION_FEES,
                'advertising': RevenueStreamType.ADVERTISING,
                'rental': RevenueStreamType.RENTAL_INCOME,
                'lease': RevenueStreamType.RENTAL_INCOME
            }
            
            # Find all potential revenue fields
            potential_revenue_fields = []
            for field_name in us_gaap.keys():
                field_lower = field_name.lower()
                # Check if field contains revenue-related keywords
                if any(keyword in field_lower for keyword in ['revenue', 'sales', 'income']) and \
                   not any(exclude in field_lower for exclude in ['expense', 'cost', 'loss', 'tax', 'deferred']):
                    potential_revenue_fields.append(field_name)
            
            debug_print(f"[BM_DEBUG] Potential revenue fields for {ticker}: {potential_revenue_fields[:10]}")
            
            # Find revenue components
            revenue_components = {}
            total_revenue = 0
            
            for field_name in potential_revenue_fields:
                units = us_gaap[field_name].get('units', {})
                if 'USD' in units:
                    # Get most recent data point
                    recent_data = sorted(units['USD'], key=lambda x: x.get('end', ''), reverse=True)[:1]
                    if recent_data and recent_data[0].get('val', 0) > 0:
                        value = recent_data[0]['val']
                        
                        # Classify revenue stream type based on field name
                        stream_type = RevenueStreamType.MIXED  # default
                        field_lower = field_name.lower()
                        for keyword, rev_type in revenue_keywords.items():
                            if keyword in field_lower:
                                stream_type = rev_type
                                break
                        
                        revenue_components[stream_type] = revenue_components.get(stream_type, 0) + value
                        total_revenue += value
                        debug_print(f"[BM_DEBUG] Found {field_name}: ${value:,.0f} -> {stream_type.value}")
            
            if not revenue_components:
                debug_print(f"[BM_DEBUG] No revenue components found in SEC data for {ticker}")
                # Check if this is a pre-revenue company by looking at available fields
                all_fields = list(us_gaap.keys())
                debug_print(f"[BM_DEBUG] Available XBRL fields: {all_fields[:5]}...")
                return None
            
            # Determine primary stream (largest component)
            primary_stream = max(revenue_components.items(), key=lambda x: x[1])[0]
            secondary_streams = [stream for stream in revenue_components.keys() if stream != primary_stream]
            
            # Calculate recurring percentage based on stream types
            recurring_percentage = self._calculate_recurring_from_streams(revenue_components, total_revenue)
            
            debug_print(f"[BM_DEBUG] SEC revenue analysis for {ticker}: Primary={primary_stream.value}, Components={len(revenue_components)}, Total=${total_revenue:,.0f}, Recurring={recurring_percentage:.2f}")
            
            return RevenueStreamAnalysis(
                primary_stream=primary_stream,
                secondary_streams=secondary_streams,
                recurring_percentage=recurring_percentage,
                growth_consistency=None  # Would need historical data
            )
            
        except Exception as e:
            debug_print(f"[BM_DEBUG] SEC revenue stream analysis failed for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_revenue_streams_from_llm(self, ticker: str, business_model_type: BusinessModelType, 
                                        financial_metrics: Dict[str, Any]) -> Optional[RevenueStreamAnalysis]:
        """Analyze revenue streams using LLM"""
        try:
            llm_manager = self.llm_manager or LLMManager()
            
            company_name = financial_metrics.get('long_name', ticker)
            sector = financial_metrics.get('sector', '')
            industry = financial_metrics.get('industry', '')
            total_revenue = financial_metrics.get('total_revenue', 0)
            
            prompt = f"""
Analyze revenue streams for {company_name} ({ticker}) and respond with JSON:

Company: {company_name}
Sector: {sector}
Industry: {industry}
Business Model: {business_model_type.value}
Total Revenue: ${total_revenue:,.0f}

Revenue Stream Types:
- SUBSCRIPTION: Recurring subscription/SaaS revenue
- PRODUCT_SALES: One-time product sales
- TRANSACTION_FEES: Marketplace/platform fees
- INTEREST_INCOME: Financial services interest
- ADVERTISING: Ad-based revenue
- RENTAL_INCOME: Asset rental/leasing
- MIXED: Multiple significant streams

Respond with JSON:
{{
    "primary_stream": "SUBSCRIPTION",
    "secondary_streams": ["PRODUCT_SALES"],
    "recurring_percentage": 0.75,
    "revenue_breakdown": {{
        "subscription_revenue": 75.0,
        "product_sales": 25.0
    }}
}}
"""
            
            response = llm_manager.generate_response(prompt, temperature=0)
            json_str = self._extract_json_from_response(response)
            
            if json_str:
                import json
                result = json.loads(json_str)
                
                # Map string to enum
                primary_stream = RevenueStreamType(result['primary_stream'])
                secondary_streams = [RevenueStreamType(s) for s in result.get('secondary_streams', [])]
                
                debug_print(f"[BM_DEBUG] LLM revenue streams: Primary={primary_stream.value}, Recurring={result.get('recurring_percentage', 0):.2f}")
                
                return RevenueStreamAnalysis(
                    primary_stream=primary_stream,
                    secondary_streams=secondary_streams,
                    recurring_percentage=result.get('recurring_percentage', 0.5),
                    growth_consistency=self._calculate_growth_consistency(financial_metrics)
                )
            
            return None
            
        except Exception as e:
            debug_print(f"[BM_DEBUG] LLM revenue stream analysis failed: {e}")
            return None
    
    def _calculate_recurring_from_streams(self, revenue_components: Dict, total_revenue: float) -> float:
        """Calculate recurring percentage based on revenue stream composition"""
        if total_revenue <= 0:
            return 0.0
        
        # Recurring revenue weights by stream type
        recurring_weights = {
            RevenueStreamType.SUBSCRIPTION: 0.95,
            RevenueStreamType.INTEREST_INCOME: 0.80,
            RevenueStreamType.RENTAL_INCOME: 0.85,
            RevenueStreamType.TRANSACTION_FEES: 0.60,
            RevenueStreamType.ADVERTISING: 0.40,
            RevenueStreamType.PRODUCT_SALES: 0.20,
            RevenueStreamType.MIXED: 0.50
        }
        
        weighted_recurring = 0
        for stream_type, amount in revenue_components.items():
            weight = recurring_weights.get(stream_type, 0.30)
            weighted_recurring += (amount / total_revenue) * weight
        
        return min(weighted_recurring, 1.0)
    
    def _estimate_recurring_percentage_hardcoded(self, business_model_type: BusinessModelType,
                                     financial_metrics: Dict[str, Any]) -> Optional[float]:
        """LEGACY: Estimate percentage of recurring revenue (kept for future use)"""
        
        # Business model-based estimates
        recurring_estimates = {
            BusinessModelType.B2B_SAAS: 0.85,
            BusinessModelType.B2C_SUBSCRIPTION: 0.80,
            BusinessModelType.FINANCIAL_SERVICES: 0.70,
            BusinessModelType.MARKETPLACE: 0.60,
            BusinessModelType.ASSET_HEAVY: 0.75,
            BusinessModelType.ADVERTISING_BASED: 0.40,
            BusinessModelType.TRADITIONAL_RETAIL: 0.20,
            BusinessModelType.MANUFACTURING: 0.30,
            BusinessModelType.PLATFORM: 0.50
        }
        
        return recurring_estimates.get(business_model_type, 0.30)
    
    def _calculate_growth_consistency(self, financial_metrics: Dict[str, Any]) -> Optional[float]:
        """Calculate revenue growth consistency (lower is more consistent)"""
        
        # Get quarterly revenue data if available
        quarterly_revenues = financial_metrics.get('quarterly_revenues', [])
        
        if len(quarterly_revenues) < 4:
            return None
        
        # Calculate quarter-over-quarter growth rates
        growth_rates = []
        for i in range(1, len(quarterly_revenues)):
            if quarterly_revenues[i-1] > 0:
                growth_rate = (quarterly_revenues[i] - quarterly_revenues[i-1]) / quarterly_revenues[i-1]
                growth_rates.append(growth_rate)
        
        if not growth_rates:
            return None
        
        # Return coefficient of variation (std dev / mean)
        mean_growth = np.mean(growth_rates)
        std_growth = np.std(growth_rates)
        
        if mean_growth == 0:
            return 1.0  # High inconsistency
        
        return min(abs(std_growth / mean_growth), 2.0)  # Cap at 2.0
    
    def _assess_revenue_quality(self, revenue_analysis: RevenueStreamAnalysis,
                              financial_metrics: Dict[str, Any]) -> RevenueQuality:
        """Assess overall revenue quality"""
        
        score = 0
        factors = 0
        
        # Recurring revenue factor
        if revenue_analysis.recurring_percentage is not None:
            if revenue_analysis.recurring_percentage > 0.7:
                score += 2
            elif revenue_analysis.recurring_percentage > 0.4:
                score += 1
            factors += 1
        
        # Growth consistency factor
        if revenue_analysis.growth_consistency is not None:
            if revenue_analysis.growth_consistency < 0.3:
                score += 2
            elif revenue_analysis.growth_consistency < 0.6:
                score += 1
            factors += 1
        
        # Revenue growth factor
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        if revenue_growth is not None and revenue_growth > 0.15:
            score += 2
        elif revenue_growth is not None and revenue_growth > 0.05:
            score += 1
        factors += 1
        
        if factors == 0:
            return RevenueQuality.FAIR
        
        avg_score = score / factors
        
        if avg_score >= 1.5:
            return RevenueQuality.EXCELLENT
        elif avg_score >= 1.0:
            return RevenueQuality.GOOD
        elif avg_score >= 0.5:
            return RevenueQuality.FAIR
        else:
            return RevenueQuality.POOR
    
    def _calculate_key_metrics(self, financial_metrics: Dict[str, Any],
                             business_model_type: BusinessModelType) -> Dict[str, float]:
        """Calculate key business model metrics"""
        
        metrics = {}
        
        # Common metrics
        metrics['revenue_growth'] = financial_metrics.get('revenue_growth', 0)
        metrics['profit_margin'] = financial_metrics.get('profit_margins', 0)
        metrics['asset_turnover'] = financial_metrics.get('total_revenue', 0) / max(financial_metrics.get('total_assets', 1), 1)
        
        # Business model specific metrics
        if business_model_type in [BusinessModelType.B2B_SAAS, BusinessModelType.B2C_SUBSCRIPTION]:
            # Estimate customer metrics (would need more data for accuracy)
            metrics['estimated_ltv_cac'] = 3.0  # Placeholder
            metrics['churn_estimate'] = 0.05  # Placeholder
        
        return metrics
    
    def _get_business_context_text(self, sec_business_data: Optional[Dict[str, Any]], financial_metrics: Dict[str, Any]) -> str:
        """Prefer the SEC 10-K Item 1 Business text (longer, filing-sourced)
        over Yahoo's shorter business_summary; falls back to the latter for
        tickers with no SEC filing (e.g. non-US-listed, confirmed elsewhere
        in this app for ASX/NZX tickers)."""
        if sec_business_data and sec_business_data.get('business_description'):
            return sec_business_data['business_description']
        return financial_metrics.get('business_summary', '') or ''

    def _select_segment_overview_slice(self, full_text: str, segment_financials: Optional[Dict[str, Any]], cap: int = 5000) -> Tuple[str, Dict[str, Any]]:
        """For each real segment name (from get_segment_financials), grab the
        text starting at its first mention in the filing - the paragraph(s)
        that actually introduce what that segment does, not generic
        boilerplate from wherever the document happens to start."""
        if not full_text:
            return '', {'method': 'empty_source'}
        annual = (segment_financials or {}).get('annual') or {}
        segment_names = list((annual.get('segments') or {}).keys())
        if not segment_names:
            return full_text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'no_segment_names'}

        per_segment_cap = max(500, cap // len(segment_names))
        chunks, used_names = [], []
        text_lower = full_text.lower()
        for name in segment_names:
            # Case-insensitive: the segment name as parsed from XBRL is
            # Title Case (e.g. "Distribution and Services Segment"), but
            # confirmed directly that the real prose mentions it mid-sentence
            # in lowercase ("...through its distribution and services
            # segment..."), which a case-sensitive find() never matches.
            idx = text_lower.find(name.lower())
            if idx == -1:
                continue
            chunks.append(full_text[idx:idx + per_segment_cap])
            used_names.append(name)
        if not chunks:
            return full_text[:cap], {'method': 'fallback_first_n_chars', 'reason': 'segment_names_not_found_in_text'}
        slice_text = ' '.join(chunks)[:cap]
        return slice_text, {'method': 'segment_overview_paragraphs', 'segment_names_used': used_names, 'chars_used': len(slice_text)}

    @staticmethod
    def _normalize_company_name(name: str) -> str:
        suffix_pattern = re.compile(r'\b(inc|incorporated|corp|corporation|company|co|ltd|limited|llc|plc|group|holdings?)\b\.?', re.IGNORECASE)
        name = suffix_pattern.sub('', name or '')
        name = re.sub(r'[^a-z0-9\s]', '', name.lower())
        return re.sub(r'\s+', ' ', name).strip()

    def _validate_competitors(self, competitors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dedupe by normalized name, then validate each remaining
        competitor's LLM-supplied ticker via a live yfinance lookup.

        Confirmed directly that the LLM will supply a wrong ticker with full
        confidence (Tidewater given as "TDE" instead of the real "TDW") or a
        ticker for a completely different company sharing similar words in
        its name ("American Marine Transportation" given ticker "AMT" -
        which is American Tower Corporation). yfinance resolving to a real
        company isn't enough on its own to accept the ticker - the resolved
        company name is also cross-checked against the LLM's claimed name,
        since a wrong-but-real ticker (like AMT) would otherwise pass a bare
        existence check.

        Also confirmed directly (KEX): the LLM can list the exact same
        competitor name twice in one response - deduped here rather than
        shown as two rows.
        """
        import difflib
        import yfinance as yf

        deduped: List[Dict[str, Any]] = []
        seen_names = set()
        for comp in competitors:
            key = self._normalize_company_name(comp.get('name', ''))
            if not key or key in seen_names:
                continue
            seen_names.add(key)
            deduped.append(dict(comp))

        for comp in deduped:
            ticker = comp.get('ticker')
            if not isinstance(ticker, str) or not ticker.strip():
                comp['ticker'] = None
                continue
            ticker = ticker.strip().upper()
            try:
                info = yf.Ticker(ticker).info
                resolved_name = info.get('longName') or info.get('shortName') or ''
                claimed_norm = self._normalize_company_name(comp.get('name', ''))
                resolved_norm = self._normalize_company_name(resolved_name)
                similarity = difflib.SequenceMatcher(None, claimed_norm, resolved_norm).ratio() if claimed_norm and resolved_norm else 0
                if similarity < 0.5:
                    debug_print(f"[BM_DEBUG] Rejecting competitor ticker {ticker}: claimed '{comp.get('name')}' vs resolved '{resolved_name}' (similarity {similarity:.2f})")
                    comp['ticker'] = None
            except Exception as e:
                debug_print(f"[BM_DEBUG] Could not validate competitor ticker {ticker}: {e}")
                comp['ticker'] = None
        return deduped

    _commodity_proxies_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def _load_commodity_proxies(cls) -> Dict[str, Any]:
        if cls._commodity_proxies_cache is None:
            path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'commodity_proxies.yaml')
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    cls._commodity_proxies_cache = yaml.safe_load(f) or {}
            except Exception as e:
                debug_print(f"[BM_DEBUG] Could not load commodity_proxies.yaml: {e}")
                cls._commodity_proxies_cache = {}
        return cls._commodity_proxies_cache

    def _resolve_driver_proxy(self, driver_name: str, synonyms: Optional[List[str]] = None) -> Tuple[Optional[str], str]:
        """Resolve a business driver to a ticker ONLY via the maintained
        commodity_proxies.yaml alias list - never by trusting the LLM's own
        ticker_symbol directly. Confirmed directly why this matters: the LLM
        mapped a "petrochemical demand" driver to NG=F (natural gas futures)
        - a real, valid ticker, just the wrong one. Matching against a
        maintained alias list can't make that specific mistake, since
        "petrochemical" isn't an alias for natural gas.

        Returns (ticker_or_None, status) where status is 'mapped' or
        'no_proxy' - callers use the status to route unmapped drivers to a
        review list rather than silently showing nothing.
        """
        proxies = self._load_commodity_proxies()
        candidate_text = ' '.join([driver_name or ''] + (synonyms or [])).lower()
        for entry in proxies.values():
            for alias in entry.get('aliases', []):
                if alias.lower() in candidate_text:
                    return entry.get('ticker'), 'mapped'
        return None, 'no_proxy'

    def _analyze_product_portfolio(self, ticker: str, company_info: Dict[str, Any], financial_metrics: Dict[str, Any], sec_business_data: Optional[Dict[str, Any]] = None, segment_financials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze product portfolio using SEC filing data + LLM analysis"""
        try:
            # Use injected LLM manager if available, otherwise create new one
            llm_manager = self.llm_manager or LLMManager()

            company_name = financial_metrics.get('long_name', ticker)
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')

            # Build prompt with SEC data if available
            if sec_business_data and sec_business_data.get('business_description'):
                business_context, slice_meta = self._select_segment_overview_slice(
                    sec_business_data['business_description'], segment_financials, cap=5000
                )
                self._slice_log['product_portfolio'] = slice_meta
                filing_date = sec_business_data.get('filing_date', 'Unknown')

                prompt = f"""
Analyze {company_name} ({ticker}) product portfolio using official SEC filing data:

SEC 10-K Business Description (Filed: {filing_date}):
{business_context}

Company: {company_name}
Sector: {sector}
Industry: {industry}

Based on the official SEC filing above, analyze the product portfolio and respond with ONLY valid JSON:
{{
    "product_breadth": "Narrow/Moderate/Broad",
    "product_depth": "Shallow/Moderate/Deep", 
    "core_products": ["Specific Product 1", "Specific Product 2", "Specific Product 3"],
    "innovation_level": "Low/Moderate/High",
    "cross_selling_potential": "Low/Moderate/High",
    "product_strengths": ["Strength 1", "Strength 2"],
    "product_weaknesses": ["Weakness 1", "Weakness 2"],
    "data_source": "SEC Filing + LLM Analysis"
}}
"""
            else:
                # Fallback to general analysis if no SEC data
                prompt = f"""
Analyze {company_name} ({ticker}) product portfolio:

Company: {company_name}
Sector: {sector}
Industry: {industry}

Note: SEC filing data not available, using general industry knowledge.

Respond with ONLY valid JSON:
{{
    "product_breadth": "Narrow/Moderate/Broad",
    "product_depth": "Shallow/Moderate/Deep", 
    "core_products": ["Specific Product 1", "Specific Product 2", "Specific Product 3"],
    "innovation_level": "Low/Moderate/High",
    "cross_selling_potential": "Low/Moderate/High",
    "product_strengths": ["Strength 1", "Strength 2"],
    "product_weaknesses": ["Weakness 1", "Weakness 2"],
    "data_source": "LLM Analysis Only"
}}
"""
            
            response = llm_manager.generate_response(prompt, temperature=0)
            debug_print(f"[BM_DEBUG] LLM response for {ticker}: {response[:100]}...")
            
            json_str = self._extract_json_from_response(response)
            if json_str:
                import json
                result = json.loads(json_str)
                debug_print(f"[BM_DEBUG] Parsed JSON for {ticker}: {result}")
                return result
            else:
                debug_print(f"[BM_DEBUG] No JSON found for {ticker}, using fallback")
                return self._get_fallback_product_analysis(sector, industry)
            
        except Exception as e:
            debug_print(f"[BM_DEBUG] Error in product analysis for {ticker}: {e}")
            return self._get_fallback_product_analysis(sector, industry)
    
    def _analyze_competitive_differentiation(self, ticker: str, company_info: Dict[str, Any], product_analysis: Dict[str, Any], financial_metrics: Dict[str, Any], sec_business_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze competitive differentiation and positioning"""
        try:
            # Use injected LLM manager if available, otherwise create new one
            llm_manager = self.llm_manager or LLMManager()

            company_name = financial_metrics.get('long_name', company_info.get('long_name', ticker))
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            core_products = product_analysis.get('core_products', [])
            # sector/industry alone (e.g. "Basic Materials"/"Specialty Chemicals" for
            # Alto Ingredients, a corn-ethanol producer) is too generic for the LLM to
            # identify a company's actual external dependencies or real competitors -
            # confirmed directly: without real business context this call hallucinated
            # an unrelated specialty-polymer/adhesives business for ALTO, and invented
            # a wrong ticker (TDE instead of TDW) and a wrong company entirely (AMT,
            # American Tower, instead of a real tank-barge competitor) for KEX.
            full_business_text = self._get_business_context_text(sec_business_data, financial_metrics)
            if sec_business_data and sec_business_data.get('business_description'):
                # Select the Competition-subsection/Jones-Act/competitor-mention
                # slice out of the full filing rather than always sending
                # whatever the first 5k characters happen to be.
                business_context, slice_meta = select_keyword_context(
                    full_business_text, ['Jones Act', 'competitor', 'compete', 'Competition'], cap=5000
                )
            else:
                business_context, slice_meta = full_business_text, {'method': 'yahoo_summary_no_slice'}
            self._slice_log['competitive_differentiation'] = slice_meta

            prompt = f"""
Analyze competitive differentiation for {company_name} ({ticker}) in the {industry} industry.

Business Description: {business_context}

Core Products: {', '.join(core_products)}
Sector: {sector}

Analyze competitive positioning and respond with JSON:
{{
    "differentiation_strategy": "Cost Leadership/Differentiation/Focus/Hybrid",
    "competitive_advantages": ["Advantage 1", "Advantage 2", "Advantage 3"],
    "unique_value_propositions": ["UVP 1", "UVP 2"],
    "key_competitors": [
        {{"name": "Competitor Company Name", "ticker": "TICK or null if private/unknown"}}
    ],
    "competitive_positioning": "Leader/Challenger/Follower/Niche",
    "barriers_to_entry": ["Barrier 1", "Barrier 2"],
    "switching_costs": "Low/Moderate/High",
    "brand_strength": "Weak/Moderate/Strong",
    "technology_moat": "None/Moderate/Strong",
    "distribution_advantages": ["Advantage 1", "Advantage 2"],
    "competitive_threats": ["Threat 1", "Threat 2"],
    "business_drivers": [
        {{
            "driver_name": "Corn prices",
            "driver_type": "commodity_input",
            "channel": "cost",
            "effect_of_increase": "negative",
            "relationship": "Corn is the company's primary ethanol feedstock; rising corn prices compress production margins.",
            "synonyms": ["corn", "corn feedstock", "corn prices", "feedstock costs"]
        }}
    ]
}}

For key_competitors: take real, named competitors from the business description above
(e.g. a filing's Competition section) where possible. If the filing names no public
competitors (common when competitors are private), return an empty list rather than
inventing one - do not fill the slot with a guess. Only supply a ticker you are
confident is correct for that exact company - if you're not certain, use null rather
than guess (a wrong ticker is worse than none; it will be independently verified and
dropped if wrong).

For business_drivers: identify the company's real external business drivers based on
the business description above - the specific commodities, currencies, interest rates,
or other macro/input factors it is economically exposed to (e.g. corn for an ethanol
producer, sugar/aluminum for a beverage bottler, ad pricing or cloud compute costs for
an internet platform - these vary enormously by company, infer from the actual
business, don't default to generic industry boilerplate).
driver_type is one of: commodity_input, commodity_output, fx, rate, regulatory,
demand_side, other.
channel is "cost" if this driver primarily affects the company's costs, or "revenue" if
it primarily affects revenue/demand.
effect_of_increase is "positive" or "negative": if this driver's own value RISES, does
that help ("positive") or hurt ("negative") the company's profitability? Answer this
for a RISE specifically, not a fall - e.g. for a commodity input cost, a price RISE is
almost always "negative" (channel "cost"); don't describe what a fall would do instead.
Keep "relationship" consistent with effect_of_increase: it must explain why a RISE in
the driver has that effect, not why a fall would have the opposite one.
List the most significant drivers, typically 3-5, but include more than 5 only if the
company genuinely has that many materially significant external dependencies - do not
omit a real driver just to stay at 5.
synonyms: 2-4 short alternate phrasings for the driver's own underlying commodity/
factor (e.g. for "Diesel fuel price": "fuel", "fuel costs", "bunker fuel") - used only
to match this driver against filing text elsewhere in the document; a ticker is
resolved independently afterward from a maintained list, not taken from you directly,
so do not include a ticker_symbol field.
"""

            response = llm_manager.generate_response(prompt, temperature=0)
            json_str = self._extract_json_from_response(response)
            if not json_str:
                # This is the largest, most reasoning-heavy prompt in this
                # analyzer (business_description context + the direction-
                # consistency ask for business_drivers). Confirmed directly:
                # reasoning_tokens alone hit 5803 of a 6622-token completion
                # on one successful run (88%), and a repeat run with the
                # identical prompt came back with 0 visible chars - reasoning
                # had consumed the entire budget that time. This is
                # non-deterministic per attempt, not a hard ceiling problem
                # (confirmed: retrying the exact same prompt succeeded in
                # every observed case), so one retry is a more reliable fix
                # here than raising MAX_COMPLETION_TOKENS further.
                debug_print(f"[BM_DEBUG] Empty/unparseable competitive_differentiation response for {ticker}, retrying once")
                response = llm_manager.generate_response(prompt, temperature=0)
                json_str = self._extract_json_from_response(response)
            result = json.loads(json_str) if json_str else self._get_fallback_competitive_analysis(industry)

            # key_competitors moved from list[str] to list[{"name","ticker"}] -
            # a fallback/older-cached result may still be the old flat-string
            # shape, so normalize before validating.
            competitors = result.get('key_competitors') or []
            normalized_competitors = []
            for c in competitors:
                if isinstance(c, dict):
                    normalized_competitors.append({'name': c.get('name', 'Unknown'), 'ticker': c.get('ticker')})
                elif isinstance(c, str):
                    normalized_competitors.append({'name': c, 'ticker': None})
            validated_competitors = self._validate_competitors(normalized_competitors)
            result['key_competitors'] = validated_competitors
            # Confirmed directly on KO: an empty list here does NOT mean the
            # industry's competitors are actually private - it can just mean
            # the ~5k-char slice this call received didn't happen to name
            # any (KO obviously has well-known public competitors). "Private"
            # is a specific claim this code hasn't verified, so the note
            # stays neutral about why none were identified.
            result['key_competitors_note'] = None if validated_competitors else (
                'No competitors confirmed from filing text'
            )

            result.setdefault('business_drivers', [])
            exposure_map = {
                ('cost', 'negative'): 'cost_headwind',
                ('cost', 'positive'): 'cost_tailwind',
                ('revenue', 'negative'): 'revenue_headwind',
                ('revenue', 'positive'): 'revenue_tailwind',
            }
            for driver in result['business_drivers']:
                driver['exposure'] = exposure_map.get(
                    (driver.get('channel'), driver.get('effect_of_increase')), driver.get('exposure', 'unknown')
                )
            self._attach_driver_price_trends(ticker, result['business_drivers'])

            # Deterministic pass-through scan over the FULL filing text (not
            # the ~5k competition slice above) - the escalation-clause
            # language that matters can sit anywhere in the document (e.g.
            # KEX's fuel escalation clauses are in a different paragraph
            # than its Competition section).
            for driver in result['business_drivers']:
                terms = [driver.get('driver_name', '')] + (driver.get('synonyms') or [])
                pass_through = scan_pass_through(full_business_text, terms)
                if pass_through:
                    driver['pass_through'] = pass_through

            self._apply_consistency_checks(result)
            return result

        except Exception:
            return self._get_fallback_competitive_analysis(industry)

    # Below this, a driver-vs-stock correlation isn't a reliable enough
    # signal to treat the stated price direction as confirmed - flagged
    # rather than silently trusted. Confirmed directly: KEX's crude oil
    # driver showed only +0.09 correlation despite being labeled with
    # confidence, well under this threshold.
    _CORRELATION_CONFIRMATION_THRESHOLD = 0.15

    def _attach_driver_price_trends(self, ticker: str, business_drivers: List[Dict[str, Any]]) -> None:
        """Resolve each driver to a ticker via the maintained proxy YAML
        (never the LLM's own ticker_symbol - see _resolve_driver_proxy),
        then fetch its live 3-month price trend and the stock's own actual
        3-month return correlation against it, mutating each driver dict in
        place.

        The correlation is a real computed number, not an LLM assertion - it
        exists because an LLM-stated "headwind"/"tailwind" label can be
        internally inconsistent with its own relationship text (confirmed
        directly on KEX: crude oil labeled a headwind while described as
        moving the same direction as revenue), and a computed correlation is
        independent evidence a reader can use to judge that claim themselves.
        A weak correlation (|r| below _CORRELATION_CONFIRMATION_THRESHOLD)
        gets an explicit confirmation_flag rather than being shown as if it
        supports the driver either way.
        """
        import yfinance as yf
        import pandas as pd

        stock_returns = None
        try:
            stock_hist = yf.Ticker(ticker).history(period='3mo')
            stock_returns = stock_hist['Close'].pct_change().dropna()
        except Exception as e:
            debug_print(f"[BM_DEBUG] Could not fetch {ticker}'s own price history for driver correlation: {e}")

        for driver in business_drivers:
            symbol, proxy_status = self._resolve_driver_proxy(driver.get('driver_name', ''), driver.get('synonyms'))
            driver['ticker_symbol'] = symbol
            driver['proxy_status'] = proxy_status
            if not symbol:
                continue
            try:
                hist = yf.Ticker(symbol).history(period='3mo')
                closes = hist['Close'].dropna()
                if len(closes) < 2:
                    continue
                start_price, end_price = float(closes.iloc[0]), float(closes.iloc[-1])
                driver['current_price'] = end_price
                driver['price_change_3mo_pct'] = ((end_price - start_price) / start_price * 100) if start_price else None

                if stock_returns is not None and len(stock_returns) >= 5:
                    driver_returns = hist['Close'].pct_change().dropna()
                    aligned = pd.concat(
                        [stock_returns.rename('stock'), driver_returns.rename('driver')], axis=1, join='inner'
                    ).dropna()
                    if len(aligned) >= 5:
                        corr = aligned['stock'].corr(aligned['driver'])
                        if corr is not None and corr == corr:  # NaN != NaN, cheap isnan check with no extra import
                            driver['correlation_3mo'] = float(corr)
                            if abs(corr) < self._CORRELATION_CONFIRMATION_THRESHOLD:
                                driver['confirmation_flag'] = 'price link not confirmed'
            except Exception as e:
                debug_print(f"[BM_DEBUG] Could not fetch price trend for driver ticker {symbol}: {e}")

    # A correlation this large contradicting the stated direction is unlikely
    # to be noise - below this, direction mismatches are too common among
    # genuinely-unrelated series to treat as a contradiction (confirmed:
    # driver correlations in the 0.1-0.2 range turn up even for drivers with
    # no real relationship, from pure market-wide co-movement).
    _CORRELATION_CONTRADICTION_THRESHOLD = 0.3

    def _apply_consistency_checks(self, result: Dict[str, Any]) -> None:
        """Deterministic checks the LLM output must not contradict itself
        on, mutating `result` in place by adding a `consistency_flags` list
        to each affected driver. Doesn't reject/alter the underlying content -
        flags it so a reader (or a future hard gate) can act on it.

        1. A driver named as a competitive_advantage should not also be
           listed as a headwind - confirmed directly on KEX: the Jones Act
           appeared in competitive_advantages (a real strength - it restricts
           domestic shipping to US-built, US-crewed vessels) while also
           showing up as a 🔴 headwind driver, i.e. two parts of the same
           report disagreeing with each other.
        2. A driver's stated direction should not contradict a strong
           observed correlation (see _CORRELATION_CONTRADICTION_THRESHOLD) -
           confirmed directly on KEX: crude oil labeled a cost headwind while
           its own relationship text described it as "driving freight rates"
           up (i.e. a revenue tailwind).
        """
        drivers = result.get('business_drivers') or []
        advantages_text = ' '.join(result.get('competitive_advantages') or []).lower()

        headwind_exposures = {'cost_headwind', 'revenue_headwind'}
        tailwind_exposures = {'cost_tailwind', 'revenue_tailwind'}

        for driver in drivers:
            flags = []
            driver_name = driver.get('driver_name', '')
            exposure = driver.get('exposure')

            if exposure in headwind_exposures and driver_name:
                # Require ALL significant words, not just one - confirmed
                # directly this matters: a one-word match alone flagged
                # "Environmental regulation" (headwind) against an advantage
                # that separately praised "environmental... standards" - a
                # coincidental shared word, not the same contradiction as
                # Jones Act appearing as BOTH an advantage and a headwind.
                name_words = [w for w in re.sub(r'[^a-z0-9\s]', '', driver_name.lower()).split() if len(w) > 3]
                if name_words and all(w in advantages_text for w in name_words):
                    flags.append('contradicts competitive_advantages')

            corr = driver.get('correlation_3mo')
            if isinstance(corr, (int, float)) and abs(corr) >= self._CORRELATION_CONTRADICTION_THRESHOLD:
                if (exposure in headwind_exposures and corr > 0) or (exposure in tailwind_exposures and corr < 0):
                    flags.append('direction contradicts observed correlation')

            if flags:
                driver['consistency_flags'] = flags

    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response with robust error handling"""
        debug_print(f"[BM_DEBUG] Raw LLM response: {response[:200]}...")
        result = extract_json_from_llm_response(response)
        if result is None:
            debug_print(f"[BM_DEBUG] No valid JSON found in response")
        return result
    
    def _get_fallback_product_analysis(self, sector: str, industry: str) -> Dict[str, Any]:
        """Fallback product analysis when LLM fails"""
        # Industry-specific fallbacks
        if 'Technology' in sector:
            return {
                "product_breadth": "Broad",
                "product_depth": "Deep",
                "core_products": ["Software Platform", "Cloud Services"],
                "innovation_level": "High",
                "cross_selling_potential": "High"
            }
        elif 'Consumer' in sector:
            return {
                "product_breadth": "Moderate",
                "product_depth": "Moderate",
                "core_products": ["Consumer Products", "Brand Portfolio"],
                "innovation_level": "Moderate",
                "cross_selling_potential": "Moderate"
            }
        else:
            return {
                "product_breadth": "Moderate",
                "product_depth": "Moderate",
                "core_products": ["Primary Product", "Secondary Product"],
                "innovation_level": "Moderate",
                "cross_selling_potential": "Moderate"
            }
    
    def _get_fallback_competitive_analysis(self, industry: str) -> Dict[str, Any]:
        """Fallback competitive analysis when LLM fails"""
        return {
            "differentiation_strategy": "Differentiation",
            "competitive_advantages": ["Market position", "Experience"],
            "unique_value_propositions": ["Industry expertise"],
            "key_competitors": ["Industry peers"],
            "competitive_positioning": "Challenger",
            "barriers_to_entry": ["Capital requirements"],
            "switching_costs": "Moderate",
            "brand_strength": "Moderate",
            "technology_moat": "Moderate",
            "distribution_advantages": ["Established channels"],
            "competitive_threats": ["New entrants", "Technology disruption"]
        }
    
    def _build_segment_data_from_financials(self, segment_financials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build primary_segments and its derived fields entirely from real
        filing numbers (get_segment_financials) - no LLM involved, so the
        model can't output a percentage, margin ranking, or growth label
        that isn't backed by the filing's own figures.

        segment_risks/cross_segment_synergies are left empty here rather
        than asking the LLM to invent qualitative color around real numbers
        it didn't produce - the numbers are the part that was previously
        wrong (confirmed: KEX showed 78%/22% with margins reversed vs the
        real 58%/42% with Marine having the HIGHER margin), and are the
        focus of this fix.
        """
        annual = (segment_financials or {}).get('annual')
        if not annual or len(annual.get('segments') or {}) < 2:
            return None

        segments = annual['segments']
        total_revenue = annual.get('total_revenue') or sum(d['revenue'] for d in segments.values())
        if not total_revenue:
            return None

        margins = {name: (d['profit'] / d['revenue']) for name, d in segments.items() if d.get('profit') is not None and d.get('revenue')}
        margin_rank = sorted(margins, key=lambda n: margins[n], reverse=True)

        def margin_profile(name: str) -> str:
            if name not in margin_rank:
                return 'Unknown'
            idx = margin_rank.index(name)
            if idx == 0:
                return 'High'
            if idx == len(margin_rank) - 1:
                return 'Low'
            return 'Medium'

        def growth_trend(d: Dict[str, Any]) -> str:
            rev, prior = d.get('revenue'), d.get('revenue_prior')
            if not rev or not prior:
                return 'Unknown'
            growth = (rev - prior) / prior
            if growth > 0.05:
                return 'Growing'
            if growth < -0.05:
                return 'Declining'
            return 'Stable'

        primary_segments = []
        growth_by_name = {}
        for name, d in segments.items():
            pct = (d['revenue'] / total_revenue) * 100
            growth_by_name[name] = ((d['revenue'] - d['revenue_prior']) / d['revenue_prior']) if d.get('revenue_prior') else None
            primary_segments.append({
                'segment_name': name,
                'revenue_percentage': round(pct, 1),
                'growth_trend': growth_trend(d),
                'margin_profile': margin_profile(name),
                'revenue': d['revenue'],
                'profit': d.get('profit'),
                'profit_measure': d.get('profit_measure'),
            })

        largest = max(segments, key=lambda n: segments[n]['revenue'])
        growable = {n: g for n, g in growth_by_name.items() if g is not None}
        fastest_growing = max(growable, key=growable.get) if growable else largest
        largest_share = segments[largest]['revenue'] / total_revenue
        diversification = 'Low' if largest_share > 0.70 else ('Medium' if largest_share > 0.50 else 'High')

        return {
            'primary_segments': primary_segments,
            'revenue_diversification': diversification,
            'fastest_growing_segment': fastest_growing,
            'largest_segment': largest,
            'segment_risks': [],
            'cross_segment_synergies': [],
            'data_source': f"SEC {annual.get('source', '10-K')} filing (filed {annual.get('filing_date', 'unknown')})",
        }

    def _extract_segment_revenue_data(self, ticker: str, company_info: Dict[str, Any], financial_metrics: Dict[str, Any], product_analysis: Dict[str, Any] = None, sec_business_data: Optional[Dict[str, Any]] = None, segment_financials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract segment revenue breakdown and growth trends"""
        real_data = self._build_segment_data_from_financials(segment_financials) if segment_financials else None
        if real_data:
            debug_print(f"[BM_DEBUG] Using real filing-sourced segment financials for {ticker}")
            self._slice_log['segment_revenue_data'] = {'method': 'structured_filing_data_no_llm'}
            return real_data

        # Fallback to LLM analysis when no usable structured segment data was
        # found (e.g. KO's column-layout segment table isn't parsed by
        # get_segment_financials yet - a known, documented gap, not silently
        # pretending coverage).
        try:
            llm_manager = self.llm_manager or LLMManager()

            company_name = financial_metrics.get('long_name', ticker)
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            total_revenue = financial_metrics.get('total_revenue', 0)
            # The previous version of this prompt hardcoded "For APPLE: iPhone,
            # Services... For TESLA: Automotive sales..." examples, which push
            # the model toward recognizable archetype segment shapes rather
            # than this company's actual ones - confirmed wrong for both ALTO
            # ("Pet Food"/"Food & Beverage Ingredients") and KEX ("Bulk Carrier
            # Operations"/"Container Shipping", which KEX doesn't even operate).
            business_context = self._get_business_context_text(sec_business_data, financial_metrics)
            self._slice_log['segment_revenue_data'] = {'method': 'llm_estimate_no_structured_data_available'}

            prompt = f"""
Analyze revenue segments for {company_name} ({ticker}) in {industry}.

Business Description: {business_context}

Company: {company_name}
Sector: {sector}
Industry: {industry}
Total Revenue: ${total_revenue:,.0f}

Base the segment names and breakdown on the business description above - use this
company's own actual reporting segments if the description names them, rather than
generic industry categories.

Respond with JSON containing segment breakdown:
{{
    "primary_segments": [
        {{
            "segment_name": "Segment Name",
            "revenue_percentage": 45.2,
            "growth_trend": "Growing/Stable/Declining",
            "margin_profile": "High/Medium/Low"
        }}
    ],
    "revenue_diversification": "High/Medium/Low",
    "fastest_growing_segment": "Segment Name",
    "largest_segment": "Segment Name",
    "segment_risks": ["Risk 1", "Risk 2"],
    "cross_segment_synergies": ["Synergy 1", "Synergy 2"]
}}
"""
            
            response = llm_manager.generate_response(prompt, temperature=0)
            json_str = self._extract_json_from_response(response)
            
            if json_str:
                import json
                result = json.loads(json_str)
                debug_print(f"[BM_DEBUG] Segment revenue data for {ticker}: {result}")
                return result
            else:
                return self._get_fallback_segment_data(sector, industry, product_analysis)
                
        except Exception as e:
            debug_print(f"[BM_DEBUG] Error extracting segment data for {ticker}: {e}")
            return self._get_fallback_segment_data(sector, industry, product_analysis)
    
    def _collect_sec_edgar_data(self, ticker: str) -> Dict[str, Any]:
        """Collect complete SEC Edgar data for the ticker"""
        sec_data = {
            'ticker': ticker,
            'data_available': False
        }
        
        if not self.sec_provider:
            sec_data['error'] = 'SEC provider not available'
            return sec_data
        
        try:
            # Get CIK
            cik = self.sec_provider._get_cik(ticker)
            if cik:
                sec_data['cik'] = cik
                sec_data['data_available'] = True
            
            # Get filing facts - summary only
            facts = self.sec_provider.get_filing_facts(ticker)
            if facts:
                sec_data['filing_facts'] = {
                    'total_xbrl_fields': len(facts.get('facts', {}).get('us-gaap', {})),
                    'entity_name': facts.get('entityName'),
                    'cik': facts.get('cik')
                }
                
                # Count segment-related fields only
                us_gaap = facts.get('facts', {}).get('us-gaap', {})
                segment_field_count = 0
                for field_name in us_gaap.keys():
                    if any(keyword in field_name.lower() for keyword in ['segment', 'reportable', 'product', 'geographic']):
                        segment_field_count += 1
                
                sec_data['segment_fields_count'] = segment_field_count
            
            # Get latest 10-K
            filing_10k = self.sec_provider.get_latest_10k(ticker)
            if filing_10k:
                sec_data['latest_10k'] = filing_10k
            
            # Get business description - summary only
            business_desc = self.sec_provider.get_business_description(ticker)
            if business_desc:
                sec_data['business_description'] = {
                    'filing_date': business_desc.get('filing_date'),
                    'description_length': len(business_desc.get('business_description', '')),
                    'data_source': business_desc.get('data_source')
                }
            
            # Get segment revenue data - summary only
            segment_data = self.sec_provider.get_segment_revenue_data(ticker)
            if segment_data:
                sec_data['segment_data'] = segment_data
            
            # Get management data
            mgmt_data = self.sec_provider.get_management_data(ticker)
            if mgmt_data and 'error' not in mgmt_data:
                sec_data['management_data'] = mgmt_data
            
        except Exception as e:
            sec_data['error'] = str(e)
        
        return sec_data
    
    def _get_fallback_segment_data(self, sector: str, industry: str, product_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback segment data using LLM product analysis when available"""
        
        # Use core products from LLM analysis if available
        if product_analysis and product_analysis.get('core_products'):
            core_products = product_analysis['core_products']
            segments = []
            
            # Distribute revenue across core products
            revenue_per_segment = 100.0 / len(core_products)
            
            for i, product in enumerate(core_products):
                # Clean up product name
                segment_name = product.replace("Repay's ", "").replace("Uber ", "")
                
                segments.append({
                    "segment_name": segment_name,
                    "revenue_percentage": round(revenue_per_segment, 1),
                    "growth_trend": "Growing" if i == 0 else "Stable",
                    "margin_profile": "High" if i == 0 else "Medium"
                })
            
            return {
                "primary_segments": segments,
                "revenue_diversification": "Medium" if len(segments) > 2 else "Low",
                "fastest_growing_segment": segments[0]["segment_name"] if segments else "Unknown",
                "largest_segment": segments[0]["segment_name"] if segments else "Unknown",
                "segment_risks": ["Market competition", "Technology disruption"],
                "cross_segment_synergies": ["Platform integration", "Customer base sharing"]
            }
        
        # Original fallback logic
        if 'Technology' in sector:
            return {
                "primary_segments": [
                    {"segment_name": "Core Technology", "revenue_percentage": 70.0, "growth_trend": "Growing", "margin_profile": "High"},
                    {"segment_name": "Services", "revenue_percentage": 30.0, "growth_trend": "Growing", "margin_profile": "Medium"}
                ],
                "revenue_diversification": "Medium",
                "fastest_growing_segment": "Services",
                "largest_segment": "Core Technology",
                "segment_risks": ["Technology disruption", "Competition"],
                "cross_segment_synergies": ["Platform integration", "Data sharing"]
            }
        else:
            return {
                "primary_segments": [
                    {"segment_name": "Primary Business", "revenue_percentage": 80.0, "growth_trend": "Stable", "margin_profile": "Medium"},
                    {"segment_name": "Secondary Business", "revenue_percentage": 20.0, "growth_trend": "Growing", "margin_profile": "Medium"}
                ],
                "revenue_diversification": "Low",
                "fastest_growing_segment": "Secondary Business",
                "largest_segment": "Primary Business",
                "segment_risks": ["Market concentration", "Economic cycles"],
                "cross_segment_synergies": ["Operational efficiency", "Customer base sharing"]
            }
    def _generate_insights(self, business_model_type: BusinessModelType,
                         revenue_analysis: RevenueStreamAnalysis,
                         key_metrics: Dict[str, float],
                         product_analysis: Dict[str, Any] = None,
                         competitive_differentiation: Dict[str, Any] = None) -> tuple:
        """Generate business model insights"""
        
        strengths = []
        risks = []
        
        # Recurring revenue strengths/risks
        if revenue_analysis.recurring_percentage is not None and revenue_analysis.recurring_percentage > 0.6:
            strengths.append("High recurring revenue provides predictable cash flows")
        elif revenue_analysis.recurring_percentage is not None and revenue_analysis.recurring_percentage < 0.3:
            risks.append("Low recurring revenue creates earnings volatility")
        
        # Growth consistency
        if revenue_analysis.growth_consistency is not None and revenue_analysis.growth_consistency < 0.4:
            strengths.append("Consistent revenue growth pattern")
        elif revenue_analysis.growth_consistency is not None and revenue_analysis.growth_consistency > 0.8:
            risks.append("Volatile revenue growth pattern")
        
        # Business model specific insights
        if business_model_type == BusinessModelType.B2B_SAAS:
            strengths.append("Scalable SaaS model with high switching costs")
            if key_metrics.get('profit_margin', 0) > 0.2:
                strengths.append("Strong unit economics")
        
        elif business_model_type == BusinessModelType.MARKETPLACE:
            strengths.append("Network effects create competitive moat")
            risks.append("Dependent on both supply and demand sides")
        
        # Enhanced: Product portfolio insights
        if product_analysis:
            if product_analysis.get('product_breadth') == 'Broad':
                strengths.append("Diversified product portfolio reduces concentration risk")
            elif product_analysis.get('product_breadth') == 'Narrow':
                risks.append("Concentrated product portfolio increases market risk")
            
            if product_analysis.get('innovation_level') == 'High':
                strengths.append("Strong innovation capabilities drive competitive advantage")
            elif product_analysis.get('innovation_level') == 'Low':
                risks.append("Limited innovation may lead to competitive disadvantage")
            
            if product_analysis.get('cross_selling_potential') == 'High':
                strengths.append("High cross-selling potential enhances customer lifetime value")
        
        # Enhanced: Competitive differentiation insights
        if competitive_differentiation:
            if competitive_differentiation.get('switching_costs') == 'High':
                strengths.append("High switching costs create customer retention advantages")
            elif competitive_differentiation.get('switching_costs') == 'Low':
                risks.append("Low switching costs increase customer churn risk")
            
            if competitive_differentiation.get('brand_strength') == 'Strong':
                strengths.append("Strong brand provides pricing power and market position")
            elif competitive_differentiation.get('brand_strength') == 'Weak':
                risks.append("Weak brand limits pricing power and market differentiation")
            
            if competitive_differentiation.get('technology_moat') == 'Strong':
                strengths.append("Strong technology moat provides sustainable competitive advantage")
            
            competitive_threats = competitive_differentiation.get('competitive_threats', [])
            for threat in competitive_threats[:2]:
                risks.append(f"Competitive threat: {threat}")
        
        return strengths, risks
    
    def _assess_competitive_moat(self, business_model_type: BusinessModelType,
                               key_metrics: Dict[str, float],
                               competitive_differentiation: Dict[str, Any] = None) -> str:
        """Assess competitive moat strength"""
        
        moat_strength = {
            BusinessModelType.B2B_SAAS: "Strong - High switching costs and network effects",
            BusinessModelType.MARKETPLACE: "Strong - Network effects and scale advantages",
            BusinessModelType.PLATFORM: "Strong - Network effects and ecosystem lock-in",
            BusinessModelType.FINANCIAL_SERVICES: "Moderate - Regulatory barriers and trust",
            BusinessModelType.ASSET_HEAVY: "Moderate - Capital requirements and location",
            BusinessModelType.MANUFACTURING: "Weak to Moderate - Scale and brand advantages",
            BusinessModelType.TRADITIONAL_RETAIL: "Weak - Low barriers to entry",
            BusinessModelType.ADVERTISING_BASED: "Weak to Moderate - Scale and data advantages",
            BusinessModelType.B2C_SUBSCRIPTION: "Moderate - Brand loyalty and content"
        }
        
        base_moat = moat_strength.get(business_model_type, "Moderate")
        
        # Enhanced: Adjust moat assessment based on competitive differentiation
        if competitive_differentiation:
            brand_strength = competitive_differentiation.get('brand_strength', 'Moderate')
            technology_moat = competitive_differentiation.get('technology_moat', 'Moderate')
            switching_costs = competitive_differentiation.get('switching_costs', 'Moderate')
            
            # Upgrade moat if multiple strong factors
            strong_factors = sum(1 for factor in [brand_strength, technology_moat, switching_costs] if factor == 'Strong')
            
            if strong_factors >= 2:
                if 'Weak' in base_moat:
                    base_moat = base_moat.replace('Weak', 'Moderate')
                elif 'Moderate' in base_moat:
                    base_moat = base_moat.replace('Moderate', 'Strong')
            elif strong_factors == 0 and all(factor == 'Weak' for factor in [brand_strength, technology_moat, switching_costs]):
                if 'Strong' in base_moat:
                    base_moat = base_moat.replace('Strong', 'Moderate')
                elif 'Moderate' in base_moat:
                    base_moat = base_moat.replace('Moderate', 'Weak')
        
        return base_moat
    
    def _calculate_scalability_score(self, business_model_type: BusinessModelType,
                                   revenue_analysis: RevenueStreamAnalysis,
                                   key_metrics: Dict[str, float]) -> float:
        """Calculate scalability score (0-10)"""
        
        base_scores = {
            BusinessModelType.B2B_SAAS: 9.0,
            BusinessModelType.PLATFORM: 8.5,
            BusinessModelType.MARKETPLACE: 8.0,
            BusinessModelType.ADVERTISING_BASED: 7.5,
            BusinessModelType.B2C_SUBSCRIPTION: 7.0,
            BusinessModelType.FINANCIAL_SERVICES: 6.0,
            BusinessModelType.MANUFACTURING: 4.0,
            BusinessModelType.TRADITIONAL_RETAIL: 3.0,
            BusinessModelType.ASSET_HEAVY: 2.0
        }
        
        base_score = base_scores.get(business_model_type, 5.0)
        
        # Adjust based on metrics
        if key_metrics.get('profit_margin', 0) > 0.2:
            base_score += 0.5
        if revenue_analysis.recurring_percentage is not None and revenue_analysis.recurring_percentage > 0.7:
            base_score += 0.5
        
        return min(base_score, 10.0)
    
    def _generate_recommendation(self, report: BusinessModelReport) -> str:
        """Generate recommendation based on business model analysis"""
        
        if report.revenue_quality == RevenueQuality.EXCELLENT and report.scalability_score > 7:
            return "Strong Buy"
        elif report.revenue_quality in [RevenueQuality.EXCELLENT, RevenueQuality.GOOD] and report.scalability_score > 5:
            return "Buy"
        elif report.revenue_quality == RevenueQuality.POOR or report.scalability_score < 3:
            return "Sell"
        else:
            return "Hold"