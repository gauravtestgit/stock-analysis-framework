import pandas as pd
import csv
from typing import Dict, Any, List, Tuple
from enum import Enum

class AlignmentCategory(Enum):
    PRECISE_ALIGNED = "Precise_Aligned"
    INVESTMENT_ALIGNED = "Investment_Aligned"
    DIRECTIONAL_ALIGNED = "Directional_Aligned"
    DIVERGENT = "Divergent"
    NO_COMPARISON = "No_Comparison"

class BatchComparisonService:
    """Service to compare batch analysis results against professional analyst recommendations"""
    
    def __init__(self):
        self.recommendation_mapping = {
            'Strong Buy': 5, 'Buy': 4, 'Hold': 3, 'Sell': 2, 'Strong Sell': 1,
            'STRONG_BUY': 5, 'BUY': 4, 'HOLD': 3, 'SELL': 2, 'STRONG_SELL': 1
        }
    
    def analyze_batch_csv(self, input_csv_path: str, output_csv_path: str):
        """Analyze batch results and compare with professional analyst recommendations"""
        
        df = pd.read_csv(input_csv_path)
        results = []
        
        print(f"Analyzing {len(df)} stocks for convergence/divergence...")
        
        for _, row in df.iterrows():
            if pd.notna(row['Error']) and row['Error'].strip():  # Skip rows with actual errors
                continue
                
            comparison_result = self._compare_stock_analysis(row)
            results.append(comparison_result)
        
        self._save_comparison_results(results, output_csv_path)
        self._print_summary(results)
        
        return results
    
    def _compare_stock_analysis(self, row: pd.Series) -> Dict[str, Any]:
        """Compare individual stock analysis with professional analyst recommendation"""
        
        ticker = row['Ticker']
        current_price = self._parse_price(row['Current_Price'])
        analyst_price = self._parse_price(row['Analyst_Price'])
        analyst_rec = row['Professional_Analyst_Recommendation']
        final_rec = row['Final_Recommendation']
        
        # Get individual method prices
        dcf_price = self._parse_price(row['DCF_Price'])
        technical_price = self._parse_price(row['Technical_Price'])
        comparable_price = self._parse_price(row['Comparable_Price'])
        startup_price = self._parse_price(row['Startup_Price'])
        
        # Calculate alignment for each method
        dcf_alignment = self._calculate_alignment(current_price, dcf_price, analyst_price, analyst_rec)
        technical_alignment = self._calculate_alignment(current_price, technical_price, analyst_price, analyst_rec)
        comparable_alignment = self._calculate_alignment(current_price, comparable_price, analyst_price, analyst_rec)
        startup_alignment = self._calculate_alignment(current_price, startup_price, analyst_price, analyst_rec)
        final_alignment = self._calculate_recommendation_alignment(final_rec, analyst_rec)
        
        return {
            'Ticker': ticker,
            'Current_Price': f"${current_price:.2f}",
            'Analyst_Price': f"${analyst_price:.2f}" if analyst_price > 0 else "$0.00",
            'Analyst_Recommendation': analyst_rec,
            'Final_Recommendation': final_rec,
            'DCF_Alignment': dcf_alignment.value,
            'Technical_Alignment': technical_alignment.value,
            'Comparable_Alignment': comparable_alignment.value,
            'Startup_Alignment': startup_alignment.value,
            'Final_Alignment': final_alignment.value,
            'Company_Type': row['Company_Type'],
            'Sector': row['Sector']
        }
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float"""
        if pd.isna(price_str) or price_str == '' or price_str == '$0.00':
            return 0.0
        return float(price_str.replace('$', '').replace(',', ''))
    
    def _calculate_alignment(self, current_price: float, method_price: float, analyst_price: float, analyst_rec: str) -> AlignmentCategory:
        """Calculate alignment between method prediction and analyst prediction"""
        
        if method_price == 0 or analyst_price == 0 or current_price == 0:
            return AlignmentCategory.NO_COMPARISON
        
        # Calculate percentage differences
        method_change = (method_price - current_price) / current_price
        analyst_change = (analyst_price - current_price) / current_price
        
        # Precise alignment (within 5%)
        if abs(method_change - analyst_change) <= 0.05:
            return AlignmentCategory.PRECISE_ALIGNED
        
        # Investment alignment (same direction, within 15%)
        if (method_change > 0 and analyst_change > 0) or (method_change < 0 and analyst_change < 0):
            if abs(method_change - analyst_change) <= 0.15:
                return AlignmentCategory.INVESTMENT_ALIGNED
            else:
                return AlignmentCategory.DIRECTIONAL_ALIGNED
        
        # Divergent (opposite directions)
        return AlignmentCategory.DIVERGENT
    
    def _calculate_recommendation_alignment(self, final_rec: str, analyst_rec: str) -> AlignmentCategory:
        """Calculate alignment between final recommendation and analyst recommendation"""
        
        # Handle NaN/missing values
        if pd.isna(final_rec) or pd.isna(analyst_rec) or not str(final_rec).strip() or not str(analyst_rec).strip():
            return AlignmentCategory.NO_COMPARISON
        
        final_rec_str = str(final_rec).strip()
        analyst_rec_str = str(analyst_rec).strip()
        
        if analyst_rec_str == 'Hold':
            return AlignmentCategory.NO_COMPARISON
        
        final_score = self.recommendation_mapping.get(final_rec_str.upper(), 3)
        analyst_score = self.recommendation_mapping.get(analyst_rec_str.upper(), 3)
        
        # Precise alignment (exact match)
        if final_score == analyst_score:
            return AlignmentCategory.PRECISE_ALIGNED
        
        # Investment alignment (within 1 level)
        if abs(final_score - analyst_score) == 1:
            return AlignmentCategory.INVESTMENT_ALIGNED
        
        # Directional alignment (same side of neutral)
        if (final_score > 3 and analyst_score > 3) or (final_score < 3 and analyst_score < 3):
            return AlignmentCategory.DIRECTIONAL_ALIGNED
        
        # Divergent (opposite sides)
        return AlignmentCategory.DIVERGENT
    
    def _save_comparison_results(self, results: List[Dict[str, Any]], output_path: str):
        """Save comparison results to CSV"""
        
        if not results:
            return
        
        fieldnames = [
            'Ticker', 'Current_Price', 'Analyst_Price', 'Analyst_Recommendation', 'Final_Recommendation',
            'DCF_Alignment', 'Technical_Alignment', 'Comparable_Alignment', 'Startup_Alignment', 'Final_Alignment',
            'Company_Type', 'Sector'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    def _print_summary(self, results: List[Dict[str, Any]]):
        """Print summary statistics of alignment analysis"""
        
        if not results:
            return
        
        total_stocks = len(results)
        
        # Count alignments for each method
        methods = ['DCF_Alignment', 'Technical_Alignment', 'Comparable_Alignment', 'Startup_Alignment', 'Final_Alignment']
        
        print(f"\n=== Alignment Summary for {total_stocks} stocks ===")
        
        for method in methods:
            method_name = method.replace('_Alignment', '')
            alignment_counts = {}
            
            for result in results:
                alignment = result[method]
                alignment_counts[alignment] = alignment_counts.get(alignment, 0) + 1
            
            print(f"\n{method_name} Method:")
            for alignment, count in alignment_counts.items():
                percentage = (count / total_stocks) * 100
                print(f"  {alignment}: {count} ({percentage:.1f}%)")