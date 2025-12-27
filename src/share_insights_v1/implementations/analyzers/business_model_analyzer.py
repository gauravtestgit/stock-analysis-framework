from typing import Dict, Any, Optional, List
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
from ...implementations.llm_providers.llm_manager import LLMManager

class BusinessModelAnalyzer(IAnalyzer):
    """Analyzer for business model and revenue stream analysis"""
    
    def __init__(self, data_provider: IDataProvider, llm_manager: Optional['LLMManager'] = None, sec_provider: Optional[SECDataProvider] = None):
        self.data_provider = data_provider
        self.llm_manager = llm_manager
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
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze business model and revenue streams"""
        try:
            company_info = data.get('company_info', {})
            financial_metrics = data.get('financial_metrics', {})
            
            print(f"[BM_DEBUG] Analyzing {ticker}: sector={company_info.get('sector')}, industry={company_info.get('industry')}")
            
            # Get business model report
            report = self.analyze_business_model(ticker, company_info, financial_metrics)
            
            if not report:
                print(f"[BM_DEBUG] No report generated for {ticker}")
                return {'error': 'Could not analyze business model'}
            
            print(f"[BM_DEBUG] Generated report for {ticker}: type={report.business_model_type.value}")
            
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
            
            print(f"[BM_DEBUG] Returning result for {ticker}: {result.get('business_model_type')}")
            return result
            
        except Exception as e:
            print(f"[BM_DEBUG] Error analyzing {ticker}: {str(e)}")
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
        
        # Analyze revenue streams
        revenue_stream_analysis = self._analyze_revenue_streams(
            ticker, business_model_type, financial_metrics
        )
        
        # Assess revenue quality
        revenue_quality = self._assess_revenue_quality(revenue_stream_analysis, financial_metrics)
        
        # Calculate key metrics
        key_metrics = self._calculate_key_metrics(financial_metrics, business_model_type)
        
        # Enhanced: Analyze product portfolio, competitive differentiation, and segment revenue
        product_analysis = self._analyze_product_portfolio(ticker, company_info, financial_metrics)
        competitive_differentiation = self._analyze_competitive_differentiation(ticker, company_info, product_analysis, financial_metrics)
        segment_revenue_data = self._extract_segment_revenue_data(ticker, company_info, financial_metrics)
        
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
            
            response = llm_manager.generate_response(prompt)
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
        """Analyze revenue stream characteristics"""
        
        # Determine primary revenue stream based on business model
        primary_stream_mapping = {
            BusinessModelType.B2B_SAAS: RevenueStreamType.SUBSCRIPTION,
            BusinessModelType.B2C_SUBSCRIPTION: RevenueStreamType.SUBSCRIPTION,
            BusinessModelType.MARKETPLACE: RevenueStreamType.TRANSACTION_FEES,
            BusinessModelType.TRADITIONAL_RETAIL: RevenueStreamType.PRODUCT_SALES,
            BusinessModelType.MANUFACTURING: RevenueStreamType.PRODUCT_SALES,
            BusinessModelType.FINANCIAL_SERVICES: RevenueStreamType.INTEREST_INCOME,
            BusinessModelType.ADVERTISING_BASED: RevenueStreamType.ADVERTISING,
            BusinessModelType.ASSET_HEAVY: RevenueStreamType.RENTAL_INCOME,
            BusinessModelType.PLATFORM: RevenueStreamType.MIXED
        }
        
        primary_stream = primary_stream_mapping.get(business_model_type, RevenueStreamType.PRODUCT_SALES)
        
        # Estimate recurring percentage based on business model
        recurring_percentage = self._estimate_recurring_percentage(business_model_type, financial_metrics)
        
        # Calculate growth consistency from revenue history
        growth_consistency = self._calculate_growth_consistency(financial_metrics)
        
        return RevenueStreamAnalysis(
            primary_stream=primary_stream,
            secondary_streams=[],  # Could be enhanced with more detailed analysis
            recurring_percentage=recurring_percentage,
            growth_consistency=growth_consistency
        )
    
    def _estimate_recurring_percentage(self, business_model_type: BusinessModelType,
                                     financial_metrics: Dict[str, Any]) -> Optional[float]:
        """Estimate percentage of recurring revenue"""
        
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
        if revenue_analysis.recurring_percentage:
            if revenue_analysis.recurring_percentage > 0.7:
                score += 2
            elif revenue_analysis.recurring_percentage > 0.4:
                score += 1
            factors += 1
        
        # Growth consistency factor
        if revenue_analysis.growth_consistency:
            if revenue_analysis.growth_consistency < 0.3:
                score += 2
            elif revenue_analysis.growth_consistency < 0.6:
                score += 1
            factors += 1
        
        # Revenue growth factor
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        if revenue_growth > 0.15:
            score += 2
        elif revenue_growth > 0.05:
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
    
    def _analyze_product_portfolio(self, ticker: str, company_info: Dict[str, Any], financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze product portfolio breadth, depth, and innovation"""
        try:
            # Use injected LLM manager if available, otherwise create new one
            llm_manager = self.llm_manager or LLMManager()
            
            company_name = financial_metrics.get('long_name', ticker)
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            business_summary = financial_metrics.get('business_summary', '')
            
            print(f"[BM_DEBUG] Product analysis for {ticker}: {company_name}, sector={sector}, industry={industry}")
            
            prompt = f"""
Analyze {company_name} ({ticker}) product portfolio:

Company: {company_name}
Sector: {sector}
Industry: {industry}

For UBER: Focus on ride-sharing, delivery, freight
For COCA-COLA: Focus on beverages, brands, geographic reach
For TESLA: Focus on vehicles, energy, software
For NVIDIA: Focus on GPUs, AI chips, software platforms

Respond with ONLY valid JSON:
{{
    "product_breadth": "Narrow/Moderate/Broad",
    "product_depth": "Shallow/Moderate/Deep", 
    "core_products": ["Specific Product 1", "Specific Product 2", "Specific Product 3"],
    "innovation_level": "Low/Moderate/High",
    "cross_selling_potential": "Low/Moderate/High",
    "product_strengths": ["Strength 1", "Strength 2"],
    "product_weaknesses": ["Weakness 1", "Weakness 2"]
}}
"""
            
            response = llm_manager.generate_response(prompt)
            print(f"[BM_DEBUG] LLM response for {ticker}: {response[:100]}...")
            
            json_str = self._extract_json_from_response(response)
            if json_str:
                import json
                result = json.loads(json_str)
                print(f"[BM_DEBUG] Parsed JSON for {ticker}: {result}")
                return result
            else:
                print(f"[BM_DEBUG] No JSON found for {ticker}, using fallback")
                return self._get_fallback_product_analysis(sector, industry)
            
        except Exception as e:
            print(f"[BM_DEBUG] Error in product analysis for {ticker}: {e}")
            return self._get_fallback_product_analysis(sector, industry)
    
    def _analyze_competitive_differentiation(self, ticker: str, company_info: Dict[str, Any], product_analysis: Dict[str, Any], financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitive differentiation and positioning"""
        try:
            # Use injected LLM manager if available, otherwise create new one
            llm_manager = self.llm_manager or LLMManager()
            
            company_name = financial_metrics.get('long_name', company_info.get('long_name', ticker))
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            core_products = product_analysis.get('core_products', [])
            
            prompt = f"""
Analyze competitive differentiation for {company_name} ({ticker}) in the {industry} industry.

Core Products: {', '.join(core_products[:3])}
Sector: {sector}

Analyze competitive positioning and respond with JSON:
{{
    "differentiation_strategy": "Cost Leadership/Differentiation/Focus/Hybrid",
    "competitive_advantages": ["Advantage 1", "Advantage 2", "Advantage 3"],
    "unique_value_propositions": ["UVP 1", "UVP 2"],
    "key_competitors": ["Competitor 1", "Competitor 2", "Competitor 3"],
    "competitive_positioning": "Leader/Challenger/Follower/Niche",
    "barriers_to_entry": ["Barrier 1", "Barrier 2"],
    "switching_costs": "Low/Moderate/High",
    "brand_strength": "Weak/Moderate/Strong",
    "technology_moat": "None/Moderate/Strong",
    "distribution_advantages": ["Advantage 1", "Advantage 2"],
    "competitive_threats": ["Threat 1", "Threat 2"]
}}
"""
            
            response = llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str) if json_str else self._get_fallback_competitive_analysis(industry)
            
        except Exception:
            return self._get_fallback_competitive_analysis(industry)
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response"""
        import re
        import json
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find JSON object in the text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            try:
                # Validate it's proper JSON
                json.loads(json_match.group(0))
                return json_match.group(0)
            except:
                pass
        
        return None
    
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
    
    def _extract_segment_revenue_data(self, ticker: str, company_info: Dict[str, Any], financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract segment revenue breakdown and growth trends"""
        # Try SEC data first if provider is available
        if self.sec_provider:
            try:
                sec_data = self.sec_provider.get_segment_revenue_data(ticker)
                if sec_data and sec_data.get('segment_data'):
                    print(f"[BM_DEBUG] Using SEC segment data for {ticker}")
                    return self._process_sec_segment_data(sec_data['segment_data'])
            except Exception as e:
                print(f"[BM_DEBUG] SEC segment data failed for {ticker}: {e}")
        
        # Fallback to LLM analysis
        try:
            llm_manager = self.llm_manager or LLMManager()
            
            company_name = financial_metrics.get('long_name', ticker)
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            total_revenue = financial_metrics.get('total_revenue', 0)
            
            prompt = f"""
Analyze revenue segments for {company_name} ({ticker}) in {industry}.

For APPLE: iPhone, Services, Mac, iPad, Wearables
For MICROSOFT: Productivity, Intelligent Cloud, More Personal Computing
For AMAZON: AWS, Online stores, Physical stores, Advertising, Subscriptions
For TESLA: Automotive sales, Energy generation, Services

Company: {company_name}
Sector: {sector}
Industry: {industry}
Total Revenue: ${total_revenue:,.0f}

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
            
            response = llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            
            if json_str:
                import json
                result = json.loads(json_str)
                print(f"[BM_DEBUG] Segment revenue data for {ticker}: {result}")
                return result
            else:
                return self._get_fallback_segment_data(sector, industry)
                
        except Exception as e:
            print(f"[BM_DEBUG] Error extracting segment data for {ticker}: {e}")
            return self._get_fallback_segment_data(sector, industry)
    
    def _process_sec_segment_data(self, sec_segment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process SEC segment data into standardized format"""
        total_revenue = sec_segment_data.get('total_revenue', 0)
        
        # Basic processing - would need more sophisticated parsing for real segment data
        return {
            "primary_segments": [
                {
                    "segment_name": "Primary Business",
                    "revenue_percentage": 100.0,
                    "growth_trend": "Stable",
                    "margin_profile": "Medium"
                }
            ],
            "revenue_diversification": "Low",
            "fastest_growing_segment": "Primary Business",
            "largest_segment": "Primary Business",
            "segment_risks": ["Regulatory changes", "Market competition"],
            "cross_segment_synergies": ["Operational efficiency"],
            "data_source": "SEC Filing"
        }
    
    def _get_fallback_segment_data(self, sector: str, industry: str) -> Dict[str, Any]:
        """Fallback segment data when LLM fails"""
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
        if revenue_analysis.recurring_percentage and revenue_analysis.recurring_percentage > 0.6:
            strengths.append("High recurring revenue provides predictable cash flows")
        elif revenue_analysis.recurring_percentage and revenue_analysis.recurring_percentage < 0.3:
            risks.append("Low recurring revenue creates earnings volatility")
        
        # Growth consistency
        if revenue_analysis.growth_consistency and revenue_analysis.growth_consistency < 0.4:
            strengths.append("Consistent revenue growth pattern")
        elif revenue_analysis.growth_consistency and revenue_analysis.growth_consistency > 0.8:
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
        if revenue_analysis.recurring_percentage and revenue_analysis.recurring_percentage > 0.7:
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