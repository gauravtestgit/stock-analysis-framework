from typing import Dict, Any, Optional, List
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...interfaces.sec_data_provider import SECDataProvider
from ...models.management_quality import (
    ManagementQualityReport, ExecutiveProfile, GovernanceMetrics,
    ManagementQuality, GovernanceRisk
)
from ...models.company import CompanyType

class ManagementQualityAnalyzer(IAnalyzer):
    """Analyzer for management quality and governance assessment"""
    
    def __init__(self, data_provider: IDataProvider, sec_provider: Optional[SECDataProvider] = None):
        self.data_provider = data_provider
        self.sec_provider = sec_provider
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze management quality"""
        try:
            financial_metrics = data.get('financial_metrics', {})
            
            # Get management data (prioritize SEC, fallback to Yahoo)
            management_data = self._get_management_data(ticker)
            
            if not management_data:
                return {'error': 'Could not retrieve management data'}
            
            # Generate management quality report
            report = self._analyze_management_quality(ticker, management_data, financial_metrics)
            
            return {
                'method': 'Management Quality Analysis',
                'applicable': True,
                'overall_quality_score': report.overall_quality_score,
                'management_quality': report.management_quality.value,
                'governance_risk': report.governance_risk.value,
                'executive_count': len(report.executive_profiles),
                'insider_ownership': report.governance_metrics.insider_ownership_pct,
                'strengths': report.strengths,
                'concerns': report.concerns,
                'key_insights': report.key_insights,
                'confidence': 'Medium',
                'recommendation': self._generate_recommendation(report)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def is_applicable(self, company_type: str) -> bool:
        """Management analysis applies to most company types"""
        excluded_types = [CompanyType.ETF.value]
        return company_type not in excluded_types
    
    def _get_management_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get management data prioritizing SEC EDGAR, fallback to Yahoo"""
        
        # Try SEC EDGAR first
        if self.sec_provider:
            sec_data = self.sec_provider.get_management_data(ticker)
            if 'error' not in sec_data:
                # Get Yahoo data for additional details
                yahoo_data = self.data_provider.get_management_data(ticker)
                if 'error' not in yahoo_data:
                    return {**sec_data, 'yahoo_data': yahoo_data}
                return sec_data
        
        # Fallback to Yahoo Finance
        yahoo_data = self.data_provider.get_management_data(ticker)
        if 'error' not in yahoo_data:
            return {'yahoo_data': yahoo_data}
        
        return None
    
    def _analyze_management_quality(self, ticker: str, management_data: Dict[str, Any], 
                                  financial_metrics: Dict[str, Any]) -> ManagementQualityReport:
        """Analyze management quality and governance"""
        
        # Get both SEC and Yahoo data
        sec_data = management_data.get('management_metrics', {})
        yahoo_data = management_data.get('yahoo_data', {})
        mgmt_info = yahoo_data.get('management_data', {})
        officers = yahoo_data.get('officers_summary', [])
        
        # Extract governance metrics
        governance_metrics = GovernanceMetrics(
            compensation_risk=mgmt_info.get('compensation_risk'),
            board_risk=mgmt_info.get('board_risk'),
            audit_risk=mgmt_info.get('audit_risk'),
            overall_risk=mgmt_info.get('overall_risk'),
            insider_ownership_pct=mgmt_info.get('held_percent_insiders'),
            institutional_ownership_pct=mgmt_info.get('held_percent_institutions')
        )
        
        # Create executive profiles
        executive_profiles = []
        for officer in officers[:5]:  # Top 5 executives
            executive_profiles.append(ExecutiveProfile(
                name=officer.get('name', 'N/A'),
                title=officer.get('title', 'N/A'),
                total_compensation=officer.get('total_pay'),
                age=officer.get('age')
            ))
        
        # Calculate quality score (include SEC data)
        quality_score = self._calculate_quality_score(governance_metrics, financial_metrics, sec_data)
        
        # Determine quality rating
        management_quality = self._determine_quality_rating(quality_score)
        
        # Assess governance risk
        governance_risk = self._assess_governance_risk(governance_metrics)
        
        # Generate insights (include SEC data)
        strengths, concerns, key_insights = self._generate_insights(
            governance_metrics, executive_profiles, financial_metrics, sec_data
        )
        
        return ManagementQualityReport(
            ticker=ticker,
            overall_quality_score=quality_score,
            management_quality=management_quality,
            governance_risk=governance_risk,
            executive_profiles=executive_profiles,
            governance_metrics=governance_metrics,
            strengths=strengths,
            concerns=concerns,
            key_insights=key_insights
        )
    
    def _calculate_quality_score(self, governance: GovernanceMetrics, 
                               financial_metrics: Dict[str, Any], sec_data: Dict[str, Any] = None) -> float:
        """Calculate overall management quality score (0-10)"""
        
        score = 5.0  # Base score
        
        # Governance risk adjustment (lower risk = higher score)
        if governance.overall_risk:
            if governance.overall_risk <= 3:
                score += 2.0
            elif governance.overall_risk <= 6:
                score += 1.0
            elif governance.overall_risk >= 8:
                score -= 2.0
        
        # Insider ownership (moderate levels are good)
        if governance.insider_ownership_pct:
            if 0.05 <= governance.insider_ownership_pct <= 0.25:  # 5-25% is optimal
                score += 1.0
            elif governance.insider_ownership_pct > 0.5:  # >50% may indicate entrenchment
                score -= 1.0
        
        # Financial performance proxy for management effectiveness
        roe = financial_metrics.get('roe', 0)
        if roe and roe > 0.15:
            score += 1.0
        elif roe and roe < 0.05:
            score -= 1.0
        
        # Revenue growth consistency
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        if revenue_growth and revenue_growth > 0.1:
            score += 0.5
        elif revenue_growth and revenue_growth < 0:
            score -= 0.5
        
        # SEC data bonus (having recent proxy filings indicates good disclosure)
        if sec_data and sec_data.get('proxy_filings_found', 0) > 0:
            score += 0.5
            # Recent proxy filing bonus
            latest_proxy = sec_data.get('latest_proxy_date')
            if latest_proxy and latest_proxy >= '2023-01-01':  # Recent filing
                score += 0.5
        
        return max(0.0, min(10.0, score))
    
    def _determine_quality_rating(self, score: float) -> ManagementQuality:
        """Determine management quality rating from score"""
        
        if score >= 8.0:
            return ManagementQuality.EXCELLENT
        elif score >= 6.5:
            return ManagementQuality.GOOD
        elif score >= 4.5:
            return ManagementQuality.AVERAGE
        elif score >= 2.5:
            return ManagementQuality.POOR
        else:
            return ManagementQuality.CONCERNING
    
    def _assess_governance_risk(self, governance: GovernanceMetrics) -> GovernanceRisk:
        """Assess overall governance risk level"""
        
        if not governance.overall_risk:
            return GovernanceRisk.MEDIUM  # Default when no data
        
        if governance.overall_risk <= 3:
            return GovernanceRisk.LOW
        elif governance.overall_risk <= 6:
            return GovernanceRisk.MEDIUM
        elif governance.overall_risk <= 8:
            return GovernanceRisk.HIGH
        else:
            return GovernanceRisk.VERY_HIGH
    
    def _generate_insights(self, governance: GovernanceMetrics, executives: List[ExecutiveProfile],
                         financial_metrics: Dict[str, Any], sec_data: Dict[str, Any] = None) -> tuple:
        """Generate management insights"""
        
        strengths = []
        concerns = []
        key_insights = []
        
        # Governance strengths/concerns
        if governance.overall_risk and governance.overall_risk <= 4:
            strengths.append("Low overall governance risk profile")
        elif governance.overall_risk and governance.overall_risk >= 7:
            concerns.append("High governance risk requires attention")
        
        # Insider ownership analysis
        if governance.insider_ownership_pct:
            if 0.05 <= governance.insider_ownership_pct <= 0.25:
                strengths.append("Optimal insider ownership alignment")
            elif governance.insider_ownership_pct < 0.02:
                concerns.append("Very low insider ownership may indicate lack of alignment")
            elif governance.insider_ownership_pct > 0.4:
                concerns.append("High insider ownership may limit shareholder influence")
        
        # Executive team insights
        if executives:
            key_insights.append(f"Leadership team of {len(executives)} key executives identified")
            
            # Compensation analysis
            compensated_execs = [e for e in executives if e.total_compensation]
            if compensated_execs:
                avg_comp = sum(e.total_compensation for e in compensated_execs) / len(compensated_execs)
                key_insights.append(f"Average executive compensation: ${avg_comp:,.0f}")
        
        # SEC filing insights
        if sec_data:
            proxy_count = sec_data.get('proxy_filings_found', 0)
            if proxy_count > 0:
                key_insights.append(f"SEC proxy filings available: {proxy_count} recent filings")
                
            latest_proxy = sec_data.get('latest_proxy_date')
            if latest_proxy:
                key_insights.append(f"Latest proxy filing: {latest_proxy}")
                if latest_proxy >= '2023-01-01':
                    strengths.append("Recent SEC proxy filings demonstrate transparency")
        
        # Financial performance context
        roe = financial_metrics.get('roe', 0)
        if roe and roe > 0.2:
            strengths.append("Strong financial performance under current management")
        elif roe and roe < 0.05:
            concerns.append("Weak financial performance may reflect management issues")
        
        return strengths, concerns, key_insights
    
    def _generate_recommendation(self, report: ManagementQualityReport) -> str:
        """Generate recommendation based on management quality"""
        
        if report.overall_quality_score >= 7.5 and report.governance_risk in [GovernanceRisk.LOW, GovernanceRisk.MEDIUM]:
            return "Strong Buy"
        elif report.overall_quality_score >= 6.0:
            return "Buy"
        elif report.overall_quality_score >= 4.0:
            return "Hold"
        else:
            return "Sell"