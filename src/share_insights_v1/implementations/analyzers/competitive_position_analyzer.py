from typing import Dict, Any, Optional, List
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...models.competitive_position import (
    CompetitivePositionReport, MarketPosition, CompetitiveAdvantage, 
    CompetitiveThreat, CompetitiveStrength, ThreatLevel
)
from ...models.company import CompanyType

class CompetitivePositionAnalyzer(IAnalyzer):
    """Analyzer for competitive position assessment"""
    
    def __init__(self, data_provider: IDataProvider):
        self.data_provider = data_provider
        
        # Industry competitive dynamics
        self.industry_dynamics = {
            'Software - Infrastructure': {'barriers': 'High', 'switching_costs': 'High', 'network_effects': True, 'capital_intensity': 'Low'},
            'Software - Application': {'barriers': 'Medium', 'switching_costs': 'High', 'network_effects': True, 'capital_intensity': 'Low'},
            'Consumer Electronics': {'barriers': 'High', 'switching_costs': 'Low', 'network_effects': False, 'capital_intensity': 'High'},
            'Internet Retail': {'barriers': 'High', 'switching_costs': 'Low', 'network_effects': True, 'capital_intensity': 'Medium'},
            'Entertainment': {'barriers': 'Medium', 'switching_costs': 'Low', 'network_effects': False, 'capital_intensity': 'High'},
            'Banks - Diversified': {'barriers': 'High', 'switching_costs': 'High', 'network_effects': False, 'capital_intensity': 'High'},
            'Banks - Regional': {'barriers': 'High', 'switching_costs': 'High', 'network_effects': False, 'capital_intensity': 'High'},
            'Biotechnology': {'barriers': 'Very High', 'switching_costs': 'High', 'network_effects': False, 'capital_intensity': 'Very High'},
            'Pharmaceuticals': {'barriers': 'Very High', 'switching_costs': 'High', 'network_effects': False, 'capital_intensity': 'Very High'},
            'Auto Manufacturers': {'barriers': 'Very High', 'switching_costs': 'Medium', 'network_effects': False, 'capital_intensity': 'Very High'},
            'Aerospace & Defense': {'barriers': 'Very High', 'switching_costs': 'Very High', 'network_effects': False, 'capital_intensity': 'Very High'},
            'Oil & Gas': {'barriers': 'Very High', 'switching_costs': 'Low', 'network_effects': False, 'capital_intensity': 'Very High'},
            'Utilities': {'barriers': 'Very High', 'switching_costs': 'Very High', 'network_effects': False, 'capital_intensity': 'Very High'},
            'Real Estate': {'barriers': 'High', 'switching_costs': 'Medium', 'network_effects': False, 'capital_intensity': 'Very High'},
            'Restaurants': {'barriers': 'Low', 'switching_costs': 'Very Low', 'network_effects': False, 'capital_intensity': 'Medium'},
            'Specialty Retail': {'barriers': 'Low', 'switching_costs': 'Low', 'network_effects': False, 'capital_intensity': 'Medium'},
            'Insurance': {'barriers': 'High', 'switching_costs': 'Medium', 'network_effects': False, 'capital_intensity': 'High'},
            'Telecommunications': {'barriers': 'Very High', 'switching_costs': 'High', 'network_effects': True, 'capital_intensity': 'Very High'}
        }
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitive position"""
        try:
            company_info = data.get('company_info', {})
            financial_metrics = data.get('financial_metrics', {})
            
            company_type = data.get('company_type', CompanyType.MATURE_PROFITABLE.value)
            report = self.analyze_competitive_position(ticker, company_info, financial_metrics, company_type)
            
            if not report:
                return {'error': 'Could not analyze competitive position'}
            
            return {
                'method': 'Competitive Position Analysis',
                'applicable': True,
                'overall_position_score': report.overall_position_score,
                'competitive_strength': report.market_position.competitive_strength.value,
                'market_share_estimate': report.market_position.market_share_estimate,
                'position_trend': report.position_trend,
                'key_differentiators': report.key_differentiators,
                'competitive_advantages': [adv.advantage_type for adv in report.competitive_advantages],
                'competitive_threats': [threat.threat_type for threat in report.competitive_threats],
                'strategic_risks': report.strategic_risks,
                'confidence': 'Medium',
                'recommendation': self._generate_recommendation(report)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def is_applicable(self, company_type: str) -> bool:
        """Competitive analysis applies to most company types"""
        excluded_types = [CompanyType.ETF.value]
        return company_type not in excluded_types
    
    def analyze_competitive_position(self, ticker: str, company_info: Dict[str, Any], 
                                   financial_metrics: Dict[str, Any], company_type: str = None) -> Optional[CompetitivePositionReport]:
        """Perform detailed competitive position analysis"""
        
        sector = company_info.get('sector', '')
        industry = company_info.get('industry', '')
        market_cap = financial_metrics.get('market_cap', 0)
        if not company_type:
            company_type = CompanyType.MATURE_PROFITABLE.value
        
        # Assess market position
        market_position = self._assess_market_position(ticker, sector, industry, financial_metrics, company_type)
        
        # Identify competitive advantages
        competitive_advantages = self._identify_competitive_advantages(
            ticker, sector, industry, financial_metrics, market_cap, company_type
        )
        
        # Assess competitive threats
        competitive_threats = self._assess_competitive_threats(
            ticker, sector, industry, financial_metrics, company_type
        )
        
        # Calculate overall position score
        overall_score = self._calculate_position_score(
            market_position, competitive_advantages, competitive_threats
        )
        
        # Determine position trend
        position_trend = self._assess_position_trend(financial_metrics)
        
        # Generate insights
        key_differentiators = self._identify_key_differentiators(
            ticker, competitive_advantages, financial_metrics
        )
        strategic_risks = self._identify_strategic_risks(
            competitive_threats, financial_metrics
        )
        
        return CompetitivePositionReport(
            ticker=ticker,
            market_position=market_position,
            competitive_advantages=competitive_advantages,
            competitive_threats=competitive_threats,
            overall_position_score=overall_score,
            position_trend=position_trend,
            key_differentiators=key_differentiators,
            strategic_risks=strategic_risks
        )
    
    def _assess_market_position(self, ticker: str, sector: str, industry: str, 
                              financial_metrics: Dict[str, Any], company_type: str) -> MarketPosition:
        """Assess market position based on size and performance"""
        
        market_cap = financial_metrics.get('market_cap', 0)
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        
        # Company type-specific assessment
        if company_type == CompanyType.STARTUP_LOSS_MAKING.value:
            market_share_estimate = 0.001
            market_rank_estimate = 50
            strength = CompetitiveStrength.WEAK if revenue_growth < 0.5 else CompetitiveStrength.MODERATE
        elif company_type == CompanyType.TURNAROUND.value:
            market_share_estimate = 0.01
            market_rank_estimate = 15
            strength = CompetitiveStrength.WEAK if revenue_growth < 0.05 else CompetitiveStrength.MODERATE
        else:
            # Traditional market cap-based assessment
            if market_cap > 500_000_000_000:  # >$500B
                market_share_estimate = 0.15
                market_rank_estimate = 1
                strength = CompetitiveStrength.DOMINANT
            elif market_cap > 100_000_000_000:  # >$100B
                market_share_estimate = 0.08
                market_rank_estimate = 2
                strength = CompetitiveStrength.STRONG
            elif market_cap > 50_000_000_000:  # >$50B
                market_share_estimate = 0.05
                market_rank_estimate = 3
                strength = CompetitiveStrength.MODERATE
            elif market_cap > 10_000_000_000:  # >$10B
                market_share_estimate = 0.02
                market_rank_estimate = 5
                strength = CompetitiveStrength.MODERATE
            else:
                market_share_estimate = 0.01
                market_rank_estimate = 10
                strength = CompetitiveStrength.WEAK
            
            # Adjust based on growth
            if revenue_growth and revenue_growth > 0.15:
                if strength == CompetitiveStrength.WEAK:
                    strength = CompetitiveStrength.MODERATE
                elif strength == CompetitiveStrength.MODERATE:
                    strength = CompetitiveStrength.STRONG
        
        return MarketPosition(
            market_share_estimate=market_share_estimate,
            market_rank_estimate=market_rank_estimate,
            growth_vs_market=revenue_growth,
            competitive_strength=strength
        )
    
    def _identify_competitive_advantages(self, ticker: str, sector: str, industry: str,
                                       financial_metrics: Dict[str, Any], 
                                       market_cap: int, company_type: str) -> List[CompetitiveAdvantage]:
        """Identify competitive advantages"""
        
        advantages = []
        industry_dynamics = self.industry_dynamics.get(industry, {})
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        
        # Company type-specific advantages
        if company_type == CompanyType.STARTUP_LOSS_MAKING.value:
            if revenue_growth and revenue_growth > 0.3:
                advantages.append(CompetitiveAdvantage(
                    advantage_type="High Growth Potential",
                    strength=CompetitiveStrength.MODERATE,
                    description="Rapid growth indicates strong market acceptance",
                    sustainability=0.5
                ))
            advantages.append(CompetitiveAdvantage(
                advantage_type="Agility & Innovation",
                strength=CompetitiveStrength.MODERATE,
                description="Small size enables rapid adaptation and innovation",
                sustainability=0.6
            ))
        elif company_type == CompanyType.TURNAROUND.value:
            if revenue_growth and revenue_growth > 0:
                advantages.append(CompetitiveAdvantage(
                    advantage_type="Recovery Momentum",
                    strength=CompetitiveStrength.MODERATE,
                    description="Successful turnaround creates operational leverage",
                    sustainability=0.4
                ))
        else:
            # Scale advantages for established companies
            if market_cap > 100_000_000_000:
                advantages.append(CompetitiveAdvantage(
                    advantage_type="Scale Economics",
                    strength=CompetitiveStrength.STRONG,
                    description="Large scale provides cost advantages and market power",
                    sustainability=0.8
                ))
        
        # Technology advantages
        if 'Technology' in sector:
            strength = CompetitiveStrength.STRONG if company_type not in [CompanyType.STARTUP_LOSS_MAKING.value] else CompetitiveStrength.MODERATE
            advantages.append(CompetitiveAdvantage(
                advantage_type="Technology Leadership",
                strength=strength,
                description="Advanced technology platform and R&D capabilities",
                sustainability=0.7
            ))
        
        # Financial strength (not applicable to loss-making companies)
        if company_type != CompanyType.STARTUP_LOSS_MAKING.value:
            roe = financial_metrics.get('roe', 0)
            if roe and roe > 0.15:
                advantages.append(CompetitiveAdvantage(
                    advantage_type="Financial Performance",
                    strength=CompetitiveStrength.MODERATE,
                    description="Superior return on equity demonstrates efficient operations",
                    sustainability=0.6
                ))
        
        # Brand strength (for consumer companies)
        if 'Consumer' in sector:
            advantages.append(CompetitiveAdvantage(
                advantage_type="Brand Recognition",
                strength=CompetitiveStrength.MODERATE,
                description="Strong brand provides pricing power and customer loyalty",
                sustainability=0.7
            ))
        
        # Network effects
        if industry_dynamics.get('network_effects'):
            advantages.append(CompetitiveAdvantage(
                advantage_type="Network Effects",
                strength=CompetitiveStrength.STRONG,
                description="Platform benefits from network effects and user growth",
                sustainability=0.9
            ))
        
        # Regulatory advantages
        if industry_dynamics.get('barriers') == 'Very High':
            advantages.append(CompetitiveAdvantage(
                advantage_type="Regulatory Barriers",
                strength=CompetitiveStrength.STRONG,
                description="High regulatory barriers protect market position",
                sustainability=0.8
            ))
        
        return advantages
    
    def _assess_competitive_threats(self, ticker: str, sector: str, industry: str,
                                  financial_metrics: Dict[str, Any], company_type: str) -> List[CompetitiveThreat]:
        """Assess competitive threats"""
        
        threats = []
        industry_dynamics = self.industry_dynamics.get(industry, {})
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        profit_margin = financial_metrics.get('profit_margins', 0)
        
        # Company type-specific threats
        if company_type == CompanyType.STARTUP_LOSS_MAKING.value:
            threats.append(CompetitiveThreat(
                threat_type="Funding Risk",
                level=ThreatLevel.HIGH,
                description="Dependence on external funding for growth",
                timeline="Immediate"
            ))
            threats.append(CompetitiveThreat(
                threat_type="Scale Competition",
                level=ThreatLevel.HIGH,
                description="Larger competitors can outspend and outscale",
                timeline="Near-term"
            ))
            threats.append(CompetitiveThreat(
                threat_type="Cash Burn Risk",
                level=ThreatLevel.CRITICAL,
                description="Ongoing losses threaten financial sustainability",
                timeline="Immediate"
            ))
        elif company_type == CompanyType.TURNAROUND.value:
            threats.append(CompetitiveThreat(
                threat_type="Execution Risk",
                level=ThreatLevel.HIGH,
                description="Risk of turnaround strategy failure",
                timeline="Near-term"
            ))
        
        # Technology disruption based on industry barriers
        if industry_dynamics.get('barriers') in ['Low', 'Medium']:
            threats.append(CompetitiveThreat(
                threat_type="Technology Disruption",
                level=ThreatLevel.HIGH,
                description="Low barriers enable disruptive new entrants",
                timeline="Long-term"
            ))
        
        # Regulatory threats
        if 'Financial' in sector or industry in ['Utilities', 'Pharmaceuticals']:
            threats.append(CompetitiveThreat(
                threat_type="Regulatory Changes",
                level=ThreatLevel.MODERATE,
                description="Heavy regulation creates compliance and change risks",
                timeline="Near-term"
            ))
        
        # Market saturation
        if revenue_growth and revenue_growth < 0.05 and company_type not in [CompanyType.TURNAROUND.value]:
            threats.append(CompetitiveThreat(
                threat_type="Market Saturation",
                level=ThreatLevel.MODERATE,
                description="Slowing growth indicates market maturity",
                timeline="Immediate"
            ))
        
        # Competitive pressure
        if profit_margin and profit_margin < 0.1:
            level = ThreatLevel.CRITICAL if company_type == CompanyType.STARTUP_LOSS_MAKING.value else ThreatLevel.HIGH
            threats.append(CompetitiveThreat(
                threat_type="Margin Pressure",
                level=level,
                description="Low margins indicate intense competitive pressure",
                timeline="Immediate"
            ))
        
        # Capital intensity threats
        if industry_dynamics.get('capital_intensity') == 'Very High':
            threats.append(CompetitiveThreat(
                threat_type="Capital Requirements",
                level=ThreatLevel.MODERATE,
                description="High capital needs limit flexibility and growth",
                timeline="Long-term"
            ))
        
        return threats
    
    def _calculate_position_score(self, market_position: MarketPosition,
                                advantages: List[CompetitiveAdvantage],
                                threats: List[CompetitiveThreat]) -> float:
        """Calculate overall competitive position score"""
        
        # Base score from market position
        strength_scores = {
            CompetitiveStrength.DOMINANT: 9.0,
            CompetitiveStrength.STRONG: 7.5,
            CompetitiveStrength.MODERATE: 5.5,
            CompetitiveStrength.WEAK: 3.5,
            CompetitiveStrength.VULNERABLE: 2.0
        }
        
        base_score = strength_scores[market_position.competitive_strength]
        
        # Adjust for advantages
        advantage_boost = len(advantages) * 0.3
        
        # Adjust for threats
        threat_penalty = len([t for t in threats if t.level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]]) * 0.5
        
        final_score = base_score + advantage_boost - threat_penalty
        return max(0.0, min(10.0, final_score))
    
    def _assess_position_trend(self, financial_metrics: Dict[str, Any]) -> str:
        """Assess whether competitive position is strengthening or weakening"""
        
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        earnings_growth = financial_metrics.get('earnings_growth', 0)
        
        if revenue_growth and revenue_growth > 0.1:
            return "Strengthening"
        elif revenue_growth and revenue_growth < 0:
            return "Weakening"
        else:
            return "Stable"
    
    def _identify_key_differentiators(self, ticker: str, advantages: List[CompetitiveAdvantage],
                                    financial_metrics: Dict[str, Any]) -> List[str]:
        """Identify key competitive differentiators"""
        
        differentiators = []
        
        # Extract from advantages
        for advantage in advantages:
            if advantage.strength in [CompetitiveStrength.STRONG, CompetitiveStrength.DOMINANT]:
                differentiators.append(advantage.advantage_type)
        
        # Add financial differentiators
        roe = financial_metrics.get('roe', 0)
        if roe and roe > 0.2:
            differentiators.append("Superior Profitability")
        
        return differentiators[:5]  # Limit to top 5
    
    def _identify_strategic_risks(self, threats: List[CompetitiveThreat],
                                financial_metrics: Dict[str, Any]) -> List[str]:
        """Identify key strategic risks"""
        
        risks = []
        
        # Extract from threats
        for threat in threats:
            if threat.level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                risks.append(threat.threat_type)
        
        # Add financial risks
        debt_to_equity = financial_metrics.get('debt_to_equity', 0)
        if debt_to_equity > 0.5:
            risks.append("High Leverage Risk")
        
        return risks[:5]  # Limit to top 5
    
    def _generate_recommendation(self, report: CompetitivePositionReport) -> str:
        """Generate recommendation based on competitive position"""
        
        if report.overall_position_score >= 8.0:
            return "Strong Buy"
        elif report.overall_position_score >= 6.5:
            return "Buy"
        elif report.overall_position_score >= 4.0:
            return "Hold"
        else:
            return "Sell"