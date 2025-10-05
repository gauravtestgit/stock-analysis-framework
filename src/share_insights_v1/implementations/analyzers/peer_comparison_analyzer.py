from typing import Dict, Any, List, Optional
from ...interfaces.peer_comparison_provider import PeerComparisonProvider
from ...interfaces.data_provider import DataProvider
from ...models.peer_comparison import PeerComparison, PeerMetrics, RelativePosition

class PeerComparisonAnalyzer:
    """Analyzer for peer comparison and relative valuation"""
    
    def __init__(self, peer_provider: PeerComparisonProvider, data_provider: DataProvider):
        self.peer_provider = peer_provider
        self.data_provider = data_provider
    
    def analyze_peer_comparison(self, ticker: str, sector: str, industry: str) -> Optional[PeerComparison]:
        """Perform comprehensive peer comparison analysis"""
        
        # Get peer companies
        peer_tickers = self.peer_provider.get_industry_peers(ticker, sector, industry)
        if not peer_tickers:
            return None
        
        # Get target company metrics
        target_metrics = self._get_company_metrics(ticker)
        if not target_metrics:
            return None
        
        # Get peer metrics
        peer_data = self.peer_provider.get_peer_metrics(peer_tickers)
        peer_metrics = []
        
        for peer_ticker, data in peer_data.items():
            if data:  # Only include peers with valid data
                peer_metrics.append(PeerMetrics(
                    ticker=peer_ticker,
                    pe_ratio=data.get('pe_ratio'),
                    ev_ebitda=data.get('ev_ebitda'),
                    price_to_sales=data.get('price_to_sales'),
                    price_to_book=data.get('price_to_book'),
                    roe=data.get('roe'),
                    revenue_growth=data.get('revenue_growth'),
                    profit_margin=data.get('profit_margin'),
                    market_cap=data.get('market_cap')
                ))
        
        # Get sector averages
        sector_averages = self.peer_provider.get_sector_averages(sector) or {}
        
        # Calculate relative position
        relative_position = self._calculate_relative_position(target_metrics, peer_metrics, sector_averages)
        
        # Generate insights
        key_insights = self._generate_insights(target_metrics, peer_metrics, relative_position)
        
        # Create valuation summary
        valuation_summary = self._create_valuation_summary(relative_position)
        
        return PeerComparison(
            target_ticker=ticker,
            peer_tickers=peer_tickers,
            target_metrics=target_metrics,
            peer_metrics=peer_metrics,
            sector_averages=sector_averages,
            relative_position=relative_position,
            valuation_summary=valuation_summary,
            key_insights=key_insights
        )
    
    def _get_company_metrics(self, ticker: str) -> Optional[PeerMetrics]:
        """Get financial metrics for target company"""
        
        try:
            financial_data = self.data_provider.get_financial_data(ticker)
            if not financial_data:
                return None
            
            return PeerMetrics(
                ticker=ticker,
                pe_ratio=financial_data.get('trailingPE'),
                ev_ebitda=financial_data.get('enterpriseToEbitda'),
                price_to_sales=financial_data.get('priceToSalesTrailing12Months'),
                price_to_book=financial_data.get('priceToBook'),
                roe=financial_data.get('returnOnEquity'),
                revenue_growth=financial_data.get('revenueGrowth'),
                profit_margin=financial_data.get('profitMargins'),
                market_cap=financial_data.get('marketCap')
            )
            
        except Exception as e:
            print(f"Error getting metrics for {ticker}: {e}")
            return None
    
    def _calculate_relative_position(self, target: PeerMetrics, peers: List[PeerMetrics], sector_avg: Dict[str, float]) -> Dict[str, RelativePosition]:
        """Calculate relative position vs peers and sector"""
        
        relative_pos = {}
        
        # Calculate peer averages
        peer_averages = self._calculate_peer_averages(peers)
        
        # Compare each metric
        metrics_to_compare = ['pe_ratio', 'ev_ebitda', 'price_to_sales', 'price_to_book', 'roe', 'revenue_growth', 'profit_margin']
        
        for metric in metrics_to_compare:
            target_value = getattr(target, metric)
            peer_avg = peer_averages.get(metric)
            
            if target_value is not None and peer_avg is not None:
                # For valuation metrics (lower is better)
                if metric in ['pe_ratio', 'ev_ebitda', 'price_to_sales', 'price_to_book']:
                    if target_value < peer_avg * 0.9:
                        relative_pos[metric] = RelativePosition.DISCOUNT
                    elif target_value > peer_avg * 1.1:
                        relative_pos[metric] = RelativePosition.PREMIUM
                    else:
                        relative_pos[metric] = RelativePosition.INLINE
                
                # For performance metrics (higher is better)
                else:
                    if target_value > peer_avg * 1.1:
                        relative_pos[metric] = RelativePosition.PREMIUM
                    elif target_value < peer_avg * 0.9:
                        relative_pos[metric] = RelativePosition.DISCOUNT
                    else:
                        relative_pos[metric] = RelativePosition.INLINE
        
        return relative_pos
    
    def _calculate_peer_averages(self, peers: List[PeerMetrics]) -> Dict[str, float]:
        """Calculate average metrics across peers"""
        
        averages = {}
        metrics = ['pe_ratio', 'ev_ebitda', 'price_to_sales', 'price_to_book', 'roe', 'revenue_growth', 'profit_margin']
        
        for metric in metrics:
            values = [getattr(peer, metric) for peer in peers if getattr(peer, metric) is not None]
            if values:
                averages[metric] = sum(values) / len(values)
        
        return averages
    
    def _generate_insights(self, target: PeerMetrics, peers: List[PeerMetrics], relative_pos: Dict[str, RelativePosition]) -> List[str]:
        """Generate key insights from peer comparison"""
        
        insights = []
        
        # Valuation insights
        valuation_discounts = sum(1 for metric in ['pe_ratio', 'ev_ebitda', 'price_to_sales', 'price_to_book'] 
                                if relative_pos.get(metric) == RelativePosition.DISCOUNT)
        
        if valuation_discounts >= 3:
            insights.append("Trading at significant discount to peers across multiple valuation metrics")
        elif valuation_discounts >= 2:
            insights.append("Trading at discount to peers on key valuation metrics")
        
        # Performance insights
        if relative_pos.get('roe') == RelativePosition.PREMIUM and relative_pos.get('profit_margin') == RelativePosition.PREMIUM:
            insights.append("Superior profitability metrics vs peer group")
        
        if relative_pos.get('revenue_growth') == RelativePosition.PREMIUM:
            insights.append("Outpacing peer group in revenue growth")
        elif relative_pos.get('revenue_growth') == RelativePosition.DISCOUNT:
            insights.append("Lagging peer group in revenue growth")
        
        # Market cap insights
        if target.market_cap and peers:
            peer_market_caps = [p.market_cap for p in peers if p.market_cap]
            if peer_market_caps:
                avg_market_cap = sum(peer_market_caps) / len(peer_market_caps)
                if target.market_cap > avg_market_cap * 2:
                    insights.append("Significantly larger than peer average")
                elif target.market_cap < avg_market_cap * 0.5:
                    insights.append("Significantly smaller than peer average")
        
        return insights
    
    def _create_valuation_summary(self, relative_pos: Dict[str, RelativePosition]) -> str:
        """Create overall valuation summary"""
        
        valuation_metrics = ['pe_ratio', 'ev_ebitda', 'price_to_sales', 'price_to_book']
        
        discount_count = sum(1 for metric in valuation_metrics if relative_pos.get(metric) == RelativePosition.DISCOUNT)
        premium_count = sum(1 for metric in valuation_metrics if relative_pos.get(metric) == RelativePosition.PREMIUM)
        
        if discount_count >= 3:
            return "Attractive valuation - trading at discount to peers"
        elif premium_count >= 3:
            return "Premium valuation - trading above peer multiples"
        elif discount_count >= 2:
            return "Reasonable valuation - some discount to peers"
        elif premium_count >= 2:
            return "Elevated valuation - some premium to peers"
        else:
            return "Fair valuation - inline with peer group"