from typing import Dict, Any, List, Optional
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...interfaces.sec_data_provider import SECDataProvider
from ...implementations.llm_providers.llm_manager import LLMManager
import json
import statistics

class IndustryAnalysisAnalyzer(IAnalyzer):
    """Enhanced industry and sector analysis with Porter's Five Forces and regulatory assessment"""
    
    def __init__(self, data_provider: IDataProvider, sec_provider: Optional[SECDataProvider] = None):
        self.data_provider = data_provider
        self.sec_provider = sec_provider
        self.llm_manager = LLMManager()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive industry analysis"""
        try:
            financial_metrics = data.get('financial_metrics', {})
            sector = financial_metrics.get('sector', 'Unknown')
            industry = financial_metrics.get('industry', 'Unknown')
            
            if sector == 'Unknown' or industry == 'Unknown':
                return {
                    'applicable': False,
                    'reason': 'Insufficient sector/industry data for analysis'
                }
            
            # Get existing analyzer data if available
            business_model_data = data.get('business_model', {})
            financial_health_data = data.get('financial_health', {})
            management_data = data.get('management_quality', {})
            
            # Get SEC data for enhanced analysis
            sec_data = self._get_sec_industry_data(ticker) if self.sec_provider else {}
            
            # Get peer companies for benchmarking
            peer_data = self._get_peer_analysis(sector, industry, financial_metrics)
            
            # Core industry analysis
            industry_insights = self._analyze_industry_dynamics_enhanced(
                ticker, sector, industry, financial_metrics, sec_data, peer_data
            )
            
            # Porter's Five Forces analysis
            porters_analysis = self._analyze_porters_five_forces(
                ticker, sector, industry, financial_metrics, sec_data, peer_data
            )
            
            # Regulatory environment assessment
            regulatory_analysis = self._assess_regulatory_environment(
                ticker, sector, industry, sec_data
            )
            
            # ESG factors assessment
            esg_analysis = self._assess_esg_factors(
                ticker, sector, sec_data, management_data
            )
            
            # Market sizing and growth analysis
            market_analysis = self._analyze_market_metrics(
                industry, peer_data, financial_metrics
            )
            
            # Enhanced competitive positioning
            competitive_analysis = self._analyze_competitive_position_enhanced(
                ticker, sector, industry, financial_metrics, business_model_data, peer_data
            )
            
            # Market catalysts with regulatory context
            market_catalysts = self._identify_market_catalysts_enhanced(
                ticker, sector, industry, regulatory_analysis, sec_data
            )
            
            # Generate comprehensive recommendation
            recommendation = self._generate_enhanced_recommendation(
                industry_insights, porters_analysis, regulatory_analysis, 
                competitive_analysis, market_catalysts, esg_analysis
            )
            
            return {
                'method': 'Enhanced Industry Analysis',
                'applicable': True,
                'sector': sector,
                'industry': industry,
                'recommendation': recommendation['recommendation'],
                'confidence': recommendation['confidence'],
                'predicted_price': recommendation.get('target_price'),
                
                # Core analysis
                'industry_outlook': industry_insights.get('outlook', 'Neutral'),
                'competitive_position': competitive_analysis.get('position', 'Average'),
                'market_catalysts': market_catalysts,
                
                # Enhanced analysis
                'porters_five_forces': porters_analysis,
                'regulatory_risk': regulatory_analysis.get('risk_level', 'Medium'),
                'esg_score': esg_analysis.get('overall_score', 5.0),
                'market_size_estimate': market_analysis.get('market_size', 'Unknown'),
                'industry_growth_rate': market_analysis.get('growth_rate'),
                
                # Detailed insights
                'industry_insights': industry_insights,
                'competitive_analysis': competitive_analysis,
                'regulatory_analysis': regulatory_analysis,
                'esg_analysis': esg_analysis,
                'market_analysis': market_analysis,
                'peer_benchmarks': peer_data.get('benchmarks', {}),
                
                'key_risks': self._identify_comprehensive_risks(
                    sector, industry, regulatory_analysis, esg_analysis
                ),
                'analysis_type': 'enhanced_industry_analysis'
            }
            
        except Exception as e:
            return {'error': f"Enhanced industry analysis failed: {str(e)}"}
    
    def _get_sec_industry_data(self, ticker: str) -> Dict[str, Any]:
        """Get SEC filing data for industry analysis"""
        try:
            facts = self.sec_provider.get_filing_facts(ticker)
            if not facts:
                return {}
            
            # Extract industry-relevant data from SEC filings
            us_gaap = facts.get('facts', {}).get('us-gaap', {})
            
            # Revenue concentration and customer data
            revenue_concentration = self._extract_revenue_concentration(facts)
            supplier_data = self._extract_supplier_information(facts)
            regulatory_mentions = self._extract_regulatory_mentions(facts)
            
            return {
                'revenue_concentration': revenue_concentration,
                'supplier_data': supplier_data,
                'regulatory_mentions': regulatory_mentions,
                'filing_date': self._get_latest_filing_date(facts)
            }
        except:
            return {}
    
    def _get_peer_analysis(self, sector: str, industry: str, metrics: Dict) -> Dict[str, Any]:
        """Get peer company data for benchmarking"""
        try:
            # This would ideally use a peer identification service
            # For now, use basic industry classification
            market_cap = metrics.get('market_cap', 0)
            
            # Estimate peer metrics based on industry patterns
            peer_benchmarks = self._estimate_industry_benchmarks(sector, industry, market_cap)
            
            return {
                'benchmarks': peer_benchmarks,
                'peer_count': peer_benchmarks.get('estimated_peers', 10)
            }
        except:
            return {'benchmarks': {}, 'peer_count': 0}
    
    def _analyze_porters_five_forces(self, ticker: str, sector: str, industry: str, 
                                   metrics: Dict, sec_data: Dict, peer_data: Dict) -> Dict[str, Any]:
        """Analyze Porter's Five Forces framework with detailed reasoning"""
        
        market_cap = metrics.get('market_cap', 0)
        revenue = metrics.get('total_revenue', 0)
        profit_margin = metrics.get('profit_margins', 0)
        
        # Revenue concentration affects buyer power
        revenue_concentration = sec_data.get('revenue_concentration', 'Unknown')
        
        prompt = f"""Analyze Porter's Five Forces for {ticker} in {industry} ({sector}) with detailed reasoning:

Company Data:
- Market Cap: ${market_cap:,.0f}
- Revenue: ${revenue:,.0f}
- Profit Margin: {profit_margin:.1%}
- Revenue Concentration: {revenue_concentration}

For each force, provide:
1. Detailed assessment with chain of thought reasoning
2. Specific industry factors and evidence
3. Impact on company's competitive position
4. Future outlook and trends

Provide Porter's Five Forces analysis in JSON format:
{{
    "supplier_power": {{
        "level": "High/Medium/Low",
        "score": 1-10,
        "detailed_assessment": "Comprehensive analysis of supplier dynamics, concentration, switching costs, and bargaining power. Include specific industry factors and evidence.",
        "key_factors": ["factor1 with explanation", "factor2 with reasoning"],
        "impact_on_company": "How this specifically affects {ticker}'s operations and profitability",
        "future_trends": "Expected changes in supplier power over next 2-3 years"
    }},
    "buyer_power": {{
        "level": "High/Medium/Low", 
        "score": 1-10,
        "detailed_assessment": "Thorough analysis of customer concentration, switching costs, price sensitivity, and negotiating power in {industry}",
        "key_factors": ["factor1 with explanation", "factor2 with reasoning"],
        "impact_on_company": "How buyer power affects {ticker}'s pricing and market position",
        "future_trends": "Expected evolution of buyer power dynamics"
    }},
    "competitive_rivalry": {{
        "level": "High/Medium/Low",
        "score": 1-10,
        "detailed_assessment": "In-depth analysis of competitive intensity, market growth, differentiation, and rivalry dynamics in {industry}",
        "key_factors": ["factor1 with explanation", "factor2 with reasoning"],
        "impact_on_company": "How competitive rivalry affects {ticker}'s market share and profitability",
        "future_trends": "Expected changes in competitive landscape"
    }},
    "threat_of_substitutes": {{
        "level": "High/Medium/Low",
        "score": 1-10,
        "detailed_assessment": "Comprehensive evaluation of substitute products/services, technology disruption, and alternative solutions in {industry}",
        "key_factors": ["factor1 with explanation", "factor2 with reasoning"],
        "impact_on_company": "How substitute threats affect {ticker}'s long-term viability",
        "future_trends": "Emerging substitutes and technological disruptions"
    }},
    "barriers_to_entry": {{
        "level": "High/Medium/Low",
        "score": 1-10,
        "detailed_assessment": "Detailed analysis of capital requirements, regulatory barriers, economies of scale, and entry obstacles in {industry}",
        "key_factors": ["factor1 with explanation", "factor2 with reasoning"],
        "impact_on_company": "How entry barriers protect or threaten {ticker}'s market position",
        "future_trends": "Expected changes in barriers to entry"
    }},
    "overall_attractiveness": "High/Medium/Low",
    "industry_profitability_outlook": "Improving/Stable/Declining",
    "strategic_implications": "Key strategic insights and recommendations based on Five Forces analysis for {ticker}"
}}

Provide detailed, evidence-based analysis specific to {industry} dynamics."""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str)
        except:
            return self._get_fallback_porters_analysis(sector, industry)
    
    def _assess_regulatory_environment(self, ticker: str, sector: str, industry: str, sec_data: Dict) -> Dict[str, Any]:
        """Assess regulatory environment with detailed analysis and reasoning"""
        
        regulatory_mentions = sec_data.get('regulatory_mentions', [])
        
        prompt = f"""Conduct comprehensive regulatory environment assessment for {industry} in {sector} sector:

Company: {ticker}
Regulatory Context: {regulatory_mentions[:3] if regulatory_mentions else 'Standard industry regulations'}

Provide detailed regulatory analysis with reasoning:

1. **Risk Level Assessment**: Analyze current and future regulatory risks
2. **Regulatory Landscape**: Map key regulations and their impact
3. **Compliance Analysis**: Evaluate compliance burden and costs
4. **Policy Trends**: Identify regulatory trends and their implications
5. **Strategic Impact**: How regulations affect competitive positioning

Provide regulatory analysis in JSON format:
{{
    "risk_level": "Very High/High/Medium/Low/Very Low",
    "score": 1-10,
    "detailed_assessment": "Comprehensive analysis of regulatory environment, including current landscape, emerging trends, and specific impact on {ticker}. Provide reasoning chain for risk level determination.",
    "key_regulations": [
        {{
            "regulation": "Regulation name",
            "impact": "Detailed explanation of how this regulation affects {ticker} and {industry}",
            "compliance_cost": "High/Medium/Low",
            "timeline": "Implementation timeline and key dates"
        }}
    ],
    "regulatory_trends": [
        {{
            "trend": "Trend description",
            "reasoning": "Why this trend is emerging and its drivers",
            "impact_on_industry": "Specific impact on {industry} sector",
            "timeline": "Expected timeline for trend development"
        }}
    ],
    "compliance_burden": "High/Medium/Low",
    "compliance_analysis": "Detailed analysis of compliance requirements, costs, and operational impact on {ticker}",
    "policy_risks": [
        {{
            "risk": "Risk description",
            "probability": "High/Medium/Low",
            "impact": "Detailed explanation of potential impact on {ticker}",
            "mitigation": "Potential mitigation strategies"
        }}
    ],
    "regulatory_opportunities": [
        {{
            "opportunity": "Opportunity description",
            "reasoning": "Why this represents an opportunity for {ticker}",
            "timeline": "When this opportunity might materialize",
            "requirements": "What {ticker} needs to do to capitalize"
        }}
    ],
    "upcoming_changes": [
        {{
            "change": "Regulatory change description",
            "timeline": "Implementation timeline",
            "impact_analysis": "Detailed analysis of impact on {ticker} and {industry}",
            "preparation_needed": "Steps {ticker} should take to prepare"
        }}
    ],
    "strategic_implications": "Key strategic insights and recommendations for {ticker} based on regulatory analysis"
}}

Focus on {industry}-specific regulatory landscape with detailed reasoning and evidence."""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str)
        except:
            return self._get_fallback_regulatory_analysis(sector, industry)
    
    def _assess_esg_factors(self, ticker: str, sector: str, sec_data: Dict, management_data: Dict) -> Dict[str, Any]:
        """Assess ESG factors using available data"""
        
        governance_risk = management_data.get('governance_risk', 'Medium')
        insider_ownership = management_data.get('insider_ownership', 0)
        
        prompt = f"""Assess ESG factors for {ticker} in {sector}:

Governance Data:
- Governance Risk: {governance_risk}
- Insider Ownership: {insider_ownership:.1%}

Provide ESG assessment in JSON format:
{{
    "environmental_score": 1-10,
    "social_score": 1-10,
    "governance_score": 1-10,
    "overall_score": 1-10,
    "esg_risks": ["risk1", "risk2"],
    "esg_opportunities": ["opportunity1", "opportunity2"],
    "sustainability_trends": ["trend1", "trend2"],
    "stakeholder_concerns": ["concern1", "concern2"]
}}

Consider {sector} industry ESG standards and expectations."""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str)
        except:
            return self._get_fallback_esg_analysis(sector)
    
    def _analyze_market_metrics(self, industry: str, peer_data: Dict, metrics: Dict) -> Dict[str, Any]:
        """Analyze market size and growth metrics"""
        
        revenue = metrics.get('total_revenue', 0)
        revenue_growth = metrics.get('yearly_revenue_growth', 0) or 0
        
        # Estimate market size based on company size and assumed market share
        estimated_market_share = 0.05  # Assume 5% market share for estimation
        if revenue > 0:
            estimated_market_size = revenue / estimated_market_share
        else:
            estimated_market_size = 0
        
        return {
            'market_size': self._categorize_market_size(estimated_market_size),
            'estimated_market_value': estimated_market_size,
            'growth_rate': revenue_growth,
            'market_maturity': self._assess_market_maturity(industry, revenue_growth),
            'concentration': 'Medium',  # Default assumption
            'geographic_scope': 'Global' if estimated_market_size > 10e9 else 'Regional'
        }
    
    def _analyze_industry_dynamics_enhanced(self, ticker: str, sector: str, industry: str, 
                                          metrics: Dict, sec_data: Dict, peer_data: Dict) -> Dict:
        """Enhanced industry dynamics analysis with detailed reasoning"""
        
        market_cap = metrics.get('market_cap', 0)
        revenue_growth = metrics.get('yearly_revenue_growth', 0) or 0
        profit_margin = metrics.get('profit_margins', 0)
        
        # Include peer benchmarking context
        peer_benchmarks = peer_data.get('benchmarks', {})
        avg_growth = peer_benchmarks.get('avg_revenue_growth', revenue_growth)
        avg_margin = peer_benchmarks.get('avg_profit_margin', profit_margin)
        
        prompt = f"""Conduct comprehensive industry dynamics analysis for {industry} sector ({sector}):

Company: {ticker}
Market Cap: ${market_cap:,.0f}
Revenue Growth: {revenue_growth:.1%} (Industry Avg: {avg_growth:.1%})
Profit Margin: {profit_margin:.1%} (Industry Avg: {avg_margin:.1%})

Provide detailed industry analysis with reasoning chains:

1. **Industry Outlook**: Analyze current state and future prospects
2. **Growth Dynamics**: Evaluate growth drivers and constraints
3. **Market Structure**: Assess market characteristics and evolution
4. **Technology Impact**: Analyze disruption and innovation trends
5. **Competitive Dynamics**: Evaluate competitive intensity and structure

Provide comprehensive industry analysis in JSON format:
{{
    "outlook": "Very Positive/Positive/Neutral/Negative/Very Negative",
    "outlook_reasoning": "Detailed explanation of industry outlook with supporting evidence, trend analysis, and future projections. Include specific factors driving the assessment.",
    "growth_drivers": [
        {{
            "driver": "Growth driver name",
            "explanation": "Detailed explanation of how this driver impacts {industry}",
            "timeline": "When this driver will have maximum impact",
            "magnitude": "High/Medium/Low impact on industry growth"
        }}
    ],
    "headwinds": [
        {{
            "headwind": "Challenge name",
            "explanation": "Detailed explanation of how this challenge affects {industry}",
            "severity": "High/Medium/Low impact on industry",
            "mitigation": "Potential ways industry players can address this challenge"
        }}
    ],
    "market_size": "Large/Medium/Small/Niche",
    "market_analysis": "Comprehensive analysis of market size, addressable market, and growth potential for {industry}",
    "maturity": "Emerging/Growth/Mature/Declining",
    "maturity_reasoning": "Detailed explanation of industry maturity assessment with supporting evidence",
    "cyclicality": "High/Medium/Low",
    "cyclicality_analysis": "Analysis of industry cyclical patterns, economic sensitivity, and seasonal factors",
    "technology_disruption": "High/Medium/Low",
    "technology_analysis": "Comprehensive assessment of technological disruption, innovation pace, and digital transformation impact on {industry}",
    "supply_demand_balance": "Oversupply/Balanced/Undersupply",
    "supply_demand_reasoning": "Analysis of current supply-demand dynamics and future projections",
    "pricing_power": "Strong/Moderate/Weak",
    "pricing_analysis": "Assessment of industry pricing power, price elasticity, and competitive pricing dynamics",
    "capital_intensity": "High/Medium/Low",
    "capital_analysis": "Analysis of capital requirements, barriers to entry, and investment patterns in {industry}",
    "innovation_pace": "Rapid/Moderate/Slow",
    "innovation_analysis": "Assessment of R&D intensity, innovation cycles, and competitive advantage from innovation",
    "globalization_impact": "High/Medium/Low",
    "globalization_analysis": "Analysis of global trade impact, international competition, and geographic market dynamics",
    "strategic_implications": "Key strategic insights and recommendations for companies in {industry} based on industry dynamics analysis"
}}

Focus on current trends, competitive dynamics, and future outlook for {industry} with detailed reasoning."""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str)
        except:
            return self._get_fallback_industry_analysis(sector, industry)
    
    def _analyze_competitive_position_enhanced(self, ticker: str, sector: str, industry: str, 
                                             metrics: Dict, business_model_data: Dict, peer_data: Dict) -> Dict:
        """Enhanced competitive position analysis"""
        
        market_cap = metrics.get('market_cap', 0)
        revenue = metrics.get('total_revenue', 0)
        revenue_growth = metrics.get('yearly_revenue_growth', 0) or 0
        
        # Categorize company size
        if market_cap > 200e9:
            size_category = "Mega Cap (>$200B)"
        elif market_cap > 10e9:
            size_category = "Large Cap ($10B-$200B)"
        elif market_cap > 2e9:
            size_category = "Mid Cap ($2B-$10B)"
        elif market_cap > 300e6:
            size_category = "Small Cap ($300M-$2B)"
        else:
            size_category = "Micro Cap (<$300M)"
        
        # Include business model insights
        business_model_type = business_model_data.get('business_model_type', 'Unknown')
        competitive_moat = business_model_data.get('competitive_moat', 'Unknown')
        scalability_score = business_model_data.get('scalability_score', 5.0)
        
        prompt = f"""Analyze competitive position for {ticker} in {industry}:

COMPANY SIZE CONTEXT (CRITICAL):
- Market Cap: ${market_cap:,.0f} ({size_category})
- Annual Revenue: ${revenue:,.0f}
- Revenue Growth: {revenue_growth:.1%}

Business Model:
- Type: {business_model_type}
- Competitive Moat: {competitive_moat}
- Scalability Score: {scalability_score}/10

IMPORTANT GUIDELINES:
- Market Leader: Only for companies with >$10B market cap AND dominant market share (>20%)
- Strong Player: Large companies ($2B-$10B+) with significant market presence
- Average: Mid-sized companies with moderate market share
- Weak: Struggling companies losing market share
- Niche Player: Small/micro-cap companies (<$2B) serving specialized markets, regardless of moat strength

For micro-cap and small-cap companies (<$2B), default to "Niche Player" unless they truly dominate their entire industry.

Provide competitive analysis in JSON format:
{{
    "position": "Market Leader/Strong Player/Average/Weak/Niche Player",
    "market_share_estimate": "High/Medium/Low/Unknown",
    "competitive_advantages": ["advantage1", "advantage2", "advantage3"],
    "competitive_disadvantages": ["disadvantage1", "disadvantage2"],
    "differentiation_strategy": "Cost Leadership/Differentiation/Focus/Hybrid",
    "moat_strength": "Strong/Moderate/Weak",
    "scalability_assessment": "High/Medium/Low",
    "innovation_position": "Leading/Following/Lagging",
    "brand_recognition": "Strong/Average/Weak",
    "customer_loyalty": "High/Medium/Low",
    "switching_costs": "High/Medium/Low",
    "network_effects": "Strong/Moderate/Weak/None"
}}

Consider absolute company size, not just business model quality."""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str)
        except:
            return self._get_fallback_competitive_analysis()
    
    def _identify_market_catalysts_enhanced(self, ticker: str, sector: str, industry: str, 
                                          regulatory_analysis: Dict, sec_data: Dict) -> List[str]:
        """Identify market catalysts with detailed reasoning and timeframes"""
        
        regulatory_trends = regulatory_analysis.get('regulatory_trends', [])
        upcoming_changes = regulatory_analysis.get('upcoming_changes', [])
        
        prompt = f"""Identify and analyze market catalysts for {industry} sector ({ticker}) with detailed reasoning:

Regulatory Context:
- Trends: {regulatory_trends[:2] if regulatory_trends else 'Standard trends'}
- Upcoming Changes: {upcoming_changes[:2] if upcoming_changes else 'No major changes'}

For each catalyst, provide:
1. Detailed explanation of the catalyst and its mechanism
2. Specific impact on {ticker} and {industry}
3. Realistic timeframe and probability
4. Quantitative impact estimate where possible
5. Risk factors that could prevent realization

Analyze catalysts across these categories:
- Technology/Innovation catalysts (new products, R&D breakthroughs)
- Regulatory/Policy catalysts (approvals, policy changes, compliance)
- Market/Economic catalysts (demand shifts, economic cycles)
- Industry-specific catalysts (consolidation, partnerships)
- ESG/Sustainability catalysts (environmental initiatives, social impact)

Return as detailed analysis with format:
**[Catalyst Title]** ([Category], [Timeframe]): [Detailed explanation of catalyst mechanism, specific impact on {ticker}, probability assessment, and potential quantitative impact. Include reasoning chain and supporting evidence.]

Provide 5-7 most impactful catalysts with comprehensive analysis."""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            catalysts = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line.startswith('**') or line.startswith('-') or line.startswith('•')):
                    catalyst = line.lstrip('-•').strip()
                    if catalyst and len(catalyst) > 50:  # Ensure detailed responses
                        catalysts.append(catalyst)
            return catalysts[:7]  # Limit to 7
        except:
            return self._get_fallback_catalysts(sector, industry)
    
    def _generate_enhanced_recommendation(self, industry_insights: Dict, porters_analysis: Dict,
                                        regulatory_analysis: Dict, competitive_analysis: Dict,
                                        market_catalysts: List, esg_analysis: Dict) -> Dict:
        """Generate enhanced recommendation with multiple factors"""
        
        # Industry outlook scoring
        outlook_scores = {
            'Very Positive': 2, 'Positive': 1, 'Neutral': 0, 
            'Negative': -1, 'Very Negative': -2
        }
        
        # Competitive position scoring
        position_scores = {
            'Market Leader': 2, 'Strong Player': 1, 'Average': 0,
            'Weak': -1, 'Niche Player': 0
        }
        
        # Porter's Five Forces scoring (higher attractiveness = higher score)
        attractiveness_scores = {
            'High': 2, 'Medium': 0, 'Low': -2
        }
        
        # Regulatory risk scoring (lower risk = higher score)
        regulatory_scores = {
            'Very Low': 2, 'Low': 1, 'Medium': 0, 'High': -1, 'Very High': -2
        }
        
        # Calculate component scores
        outlook_score = outlook_scores.get(industry_insights.get('outlook', 'Neutral'), 0)
        position_score = position_scores.get(competitive_analysis.get('position', 'Average'), 0)
        attractiveness_score = attractiveness_scores.get(porters_analysis.get('overall_attractiveness', 'Medium'), 0)
        regulatory_score = regulatory_scores.get(regulatory_analysis.get('risk_level', 'Medium'), 0)
        catalyst_score = min(len(market_catalysts), 5) - 3  # -3 to +2 based on catalyst count
        esg_score = (esg_analysis.get('overall_score', 5.0) - 5.0) / 2.5  # -2 to +2 based on ESG score
        
        # Calculate total score
        total_score = outlook_score + position_score + attractiveness_score + regulatory_score + catalyst_score + esg_score
        
        # Generate recommendation
        if total_score >= 6:
            recommendation = 'Strong Buy'
            confidence = 'High'
        elif total_score >= 3:
            recommendation = 'Buy'
            confidence = 'High' if total_score >= 4 else 'Medium'
        elif total_score >= 1:
            recommendation = 'Buy'
            confidence = 'Medium'
        elif total_score <= -6:
            recommendation = 'Strong Sell'
            confidence = 'High'
        elif total_score <= -3:
            recommendation = 'Sell'
            confidence = 'High' if total_score <= -4 else 'Medium'
        elif total_score <= -1:
            recommendation = 'Sell'
            confidence = 'Medium'
        else:
            recommendation = 'Hold'
            confidence = 'Medium'
        
        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'total_score': round(total_score, 1),
            'component_scores': {
                'industry_outlook': outlook_score,
                'competitive_position': position_score,
                'industry_attractiveness': attractiveness_score,
                'regulatory_environment': regulatory_score,
                'market_catalysts': catalyst_score,
                'esg_factors': round(esg_score, 1)
            }
        }
    
    def _identify_comprehensive_risks(self, sector: str, industry: str, 
                                    regulatory_analysis: Dict, esg_analysis: Dict) -> List[str]:
        """Identify comprehensive industry risks"""
        
        risks = []
        
        # Base sector risks
        sector_risks = {
            'Technology': ['Technology obsolescence', 'Cybersecurity threats', 'Talent competition'],
            'Healthcare': ['Regulatory approval risks', 'Patent expiration', 'Reimbursement changes'],
            'Energy': ['Commodity price volatility', 'Environmental regulations', 'Energy transition'],
            'Financial Services': ['Interest rate changes', 'Credit losses', 'Regulatory compliance'],
            'Consumer Cyclical': ['Economic downturn', 'Consumer spending changes', 'Supply chain disruption'],
            'Basic Materials': ['Commodity price cycles', 'Environmental regulations', 'Global demand shifts'],
            'Industrials': ['Economic cycles', 'Trade policy changes', 'Automation disruption'],
            'Utilities': ['Regulatory changes', 'Infrastructure investment needs', 'Energy transition'],
            'Real Estate': ['Interest rate sensitivity', 'Economic cycles', 'Regulatory changes'],
            'Communication Services': ['Regulatory scrutiny', 'Technology disruption', 'Content costs']
        }
        
        risks.extend(sector_risks.get(sector, ['Market volatility', 'Competitive pressure']))
        
        # Add regulatory risks
        policy_risks = regulatory_analysis.get('policy_risks', [])
        risks.extend(policy_risks[:2])  # Add top 2 regulatory risks
        
        # Add ESG risks
        esg_risks = esg_analysis.get('esg_risks', [])
        risks.extend(esg_risks[:2])  # Add top 2 ESG risks
        
        return risks[:6]  # Limit to 6 total risks
    
    # Helper methods for data extraction and fallbacks
    def _extract_revenue_concentration(self, facts: Dict) -> str:
        """Extract revenue concentration from SEC filings"""
        # This would analyze customer concentration disclosures
        # For now, return a default assessment
        return "Moderate concentration"
    
    def _extract_supplier_information(self, facts: Dict) -> Dict:
        """Extract supplier information from SEC filings"""
        return {'supplier_concentration': 'Medium', 'key_suppliers': []}
    
    def _extract_regulatory_mentions(self, facts: Dict) -> List[str]:
        """Extract regulatory mentions from SEC filings"""
        return ['Standard industry regulations']
    
    def _get_latest_filing_date(self, facts: Dict) -> Optional[str]:
        """Get latest filing date"""
        try:
            us_gaap = facts.get('facts', {}).get('us-gaap', {})
            for metric_data in us_gaap.values():
                units = metric_data.get('units', {}).get('USD', [])
                if units:
                    latest = max(units, key=lambda x: x.get('filed', ''))
                    return latest.get('filed')
        except:
            pass
        return None
    
    def _estimate_industry_benchmarks(self, sector: str, industry: str, market_cap: float) -> Dict:
        """Estimate industry benchmarks"""
        # Basic industry benchmark estimates
        benchmarks = {
            'avg_revenue_growth': 0.08,  # 8% default
            'avg_profit_margin': 0.12,   # 12% default
            'avg_roe': 0.15,             # 15% default
            'estimated_peers': 15
        }
        
        # Adjust based on sector
        if 'Technology' in sector:
            benchmarks['avg_revenue_growth'] = 0.15
            benchmarks['avg_profit_margin'] = 0.20
        elif 'Utilities' in sector:
            benchmarks['avg_revenue_growth'] = 0.03
            benchmarks['avg_profit_margin'] = 0.10
        
        return benchmarks
    
    def _categorize_market_size(self, market_size: float) -> str:
        """Categorize market size"""
        if market_size > 100e9:  # >$100B
            return 'Large'
        elif market_size > 10e9:  # >$10B
            return 'Medium'
        elif market_size > 1e9:   # >$1B
            return 'Small'
        else:
            return 'Niche'
    
    def _assess_market_maturity(self, industry: str, growth_rate: float) -> str:
        """Assess market maturity based on growth rate"""
        if growth_rate > 0.20:
            return 'Emerging'
        elif growth_rate > 0.10:
            return 'Growth'
        elif growth_rate > 0.02:
            return 'Mature'
        else:
            return 'Declining'
    
    # Fallback methods
    def _get_fallback_porters_analysis(self, sector: str, industry: str) -> Dict:
        """Fallback Porter's analysis"""
        return {
            'supplier_power': {'level': 'Medium', 'factors': ['Standard suppliers'], 'score': 5},
            'buyer_power': {'level': 'Medium', 'factors': ['Diverse customers'], 'score': 5},
            'competitive_rivalry': {'level': 'Medium', 'factors': ['Industry competition'], 'score': 5},
            'threat_of_substitutes': {'level': 'Medium', 'factors': ['Alternative solutions'], 'score': 5},
            'barriers_to_entry': {'level': 'Medium', 'factors': ['Capital requirements'], 'score': 5},
            'overall_attractiveness': 'Medium',
            'industry_profitability_outlook': 'Stable'
        }
    
    def _get_fallback_regulatory_analysis(self, sector: str, industry: str) -> Dict:
        """Fallback regulatory analysis"""
        return {
            'risk_level': 'Medium',
            'key_regulations': ['Industry standards'],
            'regulatory_trends': ['Stable environment'],
            'compliance_burden': 'Medium',
            'policy_risks': ['Regulatory changes'],
            'regulatory_opportunities': ['Policy support'],
            'upcoming_changes': ['Standard updates'],
            'score': 5
        }
    
    def _get_fallback_esg_analysis(self, sector: str) -> Dict:
        """Fallback ESG analysis"""
        return {
            'environmental_score': 5,
            'social_score': 5,
            'governance_score': 5,
            'overall_score': 5.0,
            'esg_risks': ['Environmental compliance'],
            'esg_opportunities': ['Sustainability initiatives'],
            'sustainability_trends': ['ESG focus'],
            'stakeholder_concerns': ['Standard concerns']
        }
    
    def _get_fallback_industry_analysis(self, sector: str, industry: str) -> Dict:
        """Fallback industry analysis"""
        return {
            'outlook': 'Neutral',
            'growth_drivers': ['Market expansion', 'Innovation'],
            'headwinds': ['Competition', 'Regulation'],
            'market_size': 'Medium',
            'maturity': 'Mature',
            'cyclicality': 'Medium',
            'technology_disruption': 'Medium',
            'supply_demand_balance': 'Balanced',
            'pricing_power': 'Moderate',
            'capital_intensity': 'Medium',
            'innovation_pace': 'Moderate',
            'globalization_impact': 'Medium'
        }
    
    def _get_fallback_competitive_analysis(self) -> Dict:
        """Fallback competitive analysis"""
        return {
            'position': 'Average',
            'market_share_estimate': 'Unknown',
            'competitive_advantages': ['Established operations'],
            'competitive_disadvantages': ['Market competition'],
            'differentiation_strategy': 'Hybrid',
            'moat_strength': 'Moderate',
            'scalability_assessment': 'Medium',
            'innovation_position': 'Following',
            'brand_recognition': 'Average',
            'customer_loyalty': 'Medium',
            'switching_costs': 'Medium',
            'network_effects': 'Moderate'
        }
    
    def _get_fallback_catalysts(self, sector: str, industry: str) -> List[str]:
        """Fallback catalysts"""
        return [
            'Market expansion opportunities',
            'Regulatory clarity and support',
            'Technology adoption trends',
            'Economic recovery momentum',
            'Industry consolidation potential'
        ]
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response"""
        import re
        
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return response
    
    def is_applicable(self, company_type: str) -> bool:
        """Enhanced industry analysis applicable to all company types"""
        return True
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response"""
        import re
        
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return response
    
    def _get_fallback_industry_analysis(self, sector: str, industry: str) -> Dict:
        """Fallback industry analysis when LLM fails"""
        return {
            'outlook': 'Neutral',
            'growth_drivers': ['Market expansion', 'Innovation'],
            'headwinds': ['Competition', 'Regulation'],
            'market_size': 'Medium',
            'maturity': 'Mature',
            'cyclicality': 'Medium',
            'regulatory_environment': 'Neutral',
            'technology_disruption': 'Medium',
            'supply_demand_balance': 'Balanced'
        }
    
    def _get_fallback_competitive_analysis(self) -> Dict:
        """Fallback competitive analysis when LLM fails"""
        return {
            'position': 'Average',
            'market_share': 'Unknown',
            'competitive_advantages': ['Established operations'],
            'competitive_disadvantages': ['Market competition'],
            'barriers_to_entry': 'Medium',
            'switching_costs': 'Medium',
            'brand_strength': 'Average',
            'cost_position': 'Average',
            'innovation_capability': 'Following'
        }
    

    
    def _get_recent_news(self, ticker: str) -> List[str]:
        """Get recent news titles for context"""
        try:
            news_data = self.data_provider.get_news_data(ticker)
            if news_data and 'articles' in news_data:
                return [article.get('title', '') for article in news_data['articles'][:3] if article.get('title')]
            return []
        except:
            return []
    
    def _get_fallback_catalysts(self, sector: str, industry: str) -> List[str]:
        """Fallback catalysts when LLM fails"""
        return [
            'Market expansion opportunities',
            'Regulatory clarity',
            'Technology adoption',
            'Economic recovery'
        ]
    
    def is_applicable(self, company_type: str) -> bool:
        """Industry analysis applicable to all company types"""
        return True