import pandas as pd
import numpy as np
from analyst_integration import ProfessionalVsAlgorithmicComparison
import yfinance as yf

class AnalystMatcher:
    def __init__(self):
        self.comparison_engine = ProfessionalVsAlgorithmicComparison()
    
    def find_matching_analyses(self, csv_file_path, sample_size=50):
        """Find stocks where our analysis matches professional analyst forecasts"""
        
        # Read the analysis results
        df = pd.read_csv(csv_file_path)
        
        # Sample for testing (remove for full analysis)
        if sample_size:
            df = df.head(sample_size)
        
        matches = []
        divergences = []
        contrarian_picks = []
        
        print(f"Analyzing {len(df)} stocks for analyst alignment...")
        
        for idx, row in df.iterrows():
            ticker = row['Ticker']
            print(f"Processing {ticker} ({idx+1}/{len(df)})")
            
            try:
                # Get professional vs algorithmic comparison
                comparison = self.comparison_engine.compare_analysis(row)
                
                if not comparison.get('analyst_target'):
                    continue  # Skip if no analyst data
                
                # Categorize the comparison
                assessment = comparison.get('assessment', 'UNKNOWN')
                deviation_score = comparison.get('deviation_score', 999)
                confidence = comparison.get('confidence', 'Low')
                
                comparison_data = {
                    'ticker': ticker,
                    'our_dcf_price': comparison.get('our_dcf_price'),
                    'analyst_target': comparison.get('analyst_target'),
                    'current_price': comparison.get('current_price'),
                    'our_upside': comparison.get('our_upside'),
                    'analyst_upside': comparison.get('analyst_upside'),
                    'deviation_score': deviation_score,
                    'confidence': confidence,
                    'assessment': assessment,
                    'our_recommendation': comparison.get('our_recommendation'),
                    'analyst_recommendation': comparison.get('analyst_recommendation'),
                    'analyst_count': comparison.get('analyst_count', 0),
                    'validation_flags': ', '.join(comparison.get('validation_flags', []))
                }
                
                if assessment in ['INVESTMENT_ALIGNED', 'BULLISH_CONVERGENCE', 'BEARISH_CONVERGENCE']:
                    matches.append(comparison_data)
                elif assessment == 'HIGH_DIVERGENCE':
                    divergences.append(comparison_data)
                elif assessment == 'CONTRARIAN_OPPORTUNITY':
                    contrarian_picks.append(comparison_data)
                    
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                continue
        
        return {
            'consensus_matches': pd.DataFrame(matches),
            'high_divergences': pd.DataFrame(divergences),
            'contrarian_opportunities': pd.DataFrame(contrarian_picks)
        }
    
    def generate_analyst_report(self, results):
        """Generate a comprehensive report of analyst comparisons"""
        
        report = []
        report.append("=== ANALYST ALIGNMENT REPORT ===")
        report.append("")
        
        # Consensus Matches
        matches_df = results['consensus_matches']
        if not matches_df.empty:
            report.append(f"INVESTMENT ALIGNED STOCKS ({len(matches_df)} found):")
            report.append("These stocks show directional convergence with professional analysts (both see significant opportunities)")
            report.append("")
            
            for _, row in matches_df.iterrows():
                our_upside = row['our_upside'] or 0
                analyst_upside = row['analyst_upside'] or 0
                report.append(f"• {row['ticker']}: Our {our_upside:+.1f}% vs Analysts {analyst_upside:+.1f}% (Deviation: {row['deviation_score']:.1f}%)")
                report.append(f"  Current: ${row['current_price']:.2f} | Our DCF: ${row['our_dcf_price']:.2f} | Analyst Target: ${row['analyst_target']:.2f}")
                report.append(f"  Recommendations: Ours={row['our_recommendation']} | Analysts={row['analyst_recommendation']} | Coverage={row['analyst_count']} analysts")
                report.append("")
        else:
            report.append("INVESTMENT ALIGNED STOCKS: None found in sample")
            report.append("")
        
        # High Divergences
        divergences_df = results['high_divergences']
        if not divergences_df.empty:
            report.append(f"HIGH DIVERGENCE STOCKS ({len(divergences_df)} found):")
            report.append("These stocks show significant disagreement with analyst consensus")
            report.append("")
            
            for _, row in divergences_df.iterrows():
                our_upside = row['our_upside'] or 0
                analyst_upside = row['analyst_upside'] or 0
                report.append(f"• {row['ticker']}: Our {our_upside:+.1f}% vs Analysts {analyst_upside:+.1f}% (Deviation: {row['deviation_score']:.1f}%)")
                report.append(f"  Current: ${row['current_price']:.2f} | Our DCF: ${row['our_dcf_price']:.2f} | Analyst Target: ${row['analyst_target']:.2f}")
                if row['validation_flags']:
                    report.append(f"  Issues: {row['validation_flags']}")
                report.append("")
        
        # Contrarian Opportunities
        contrarian_df = results['contrarian_opportunities']
        if not contrarian_df.empty:
            report.append(f"CONTRARIAN OPPORTUNITIES ({len(contrarian_df)} found):")
            report.append("These stocks show opposite directional views vs analyst consensus")
            report.append("")
            
            for _, row in contrarian_df.iterrows():
                our_upside = row['our_upside'] or 0
                analyst_upside = row['analyst_upside'] or 0
                report.append(f"• {row['ticker']}: Our {our_upside:+.1f}% vs Analysts {analyst_upside:+.1f}%")
                report.append(f"  Current: ${row['current_price']:.2f} | Our DCF: ${row['our_dcf_price']:.2f} | Analyst Target: ${row['analyst_target']:.2f}")
                report.append(f"  Recommendations: Ours={row['our_recommendation']} | Analysts={row['analyst_recommendation']}")
                report.append("")
        
        # Summary Statistics
        total_analyzed = len(matches_df) + len(divergences_df) + len(contrarian_df)
        if total_analyzed > 0:
            report.append("SUMMARY STATISTICS:")
            report.append(f"• Total stocks with analyst coverage: {total_analyzed}")
            report.append(f"• Investment aligned: {len(matches_df)} ({len(matches_df)/total_analyzed*100:.1f}%)")
            report.append(f"• High divergence: {len(divergences_df)} ({len(divergences_df)/total_analyzed*100:.1f}%)")
            report.append(f"• Contrarian opportunities: {len(contrarian_df)} ({len(contrarian_df)/total_analyzed*100:.1f}%)")
            
            # Average deviations
            all_deviations = []
            for df in [matches_df, divergences_df, contrarian_df]:
                if not df.empty:
                    all_deviations.extend(df['deviation_score'].dropna().tolist())
            
            if all_deviations:
                report.append(f"• Average deviation from consensus: {np.mean(all_deviations):.1f}%")
        
        return "\n".join(report)

if __name__ == "__main__":
    # Initialize the matcher
    matcher = AnalystMatcher()
    
    # Analyze the stock data
    csv_path = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\stock_analysis.csv"
    
    print("Finding analyst alignment matches...")
    results = matcher.find_matching_analyses(csv_path, sample_size=5064)  # Test with 100 stocks
    
    # Generate and display report
    report = matcher.generate_analyst_report(results)
    print("\n" + report)
    report_file = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\analysis\\analyst_report.txt"
    # Save report to file
    with open(report_file, 'w') as f:
        f.write(report)        # Save detailed results
    output_dir = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\analysis\\"
    
    if not results['consensus_matches'].empty:
        results['consensus_matches'].to_csv(f"{output_dir}consensus_matches.csv", index=False)
        print(f"\nConsensus matches saved to consensus_matches.csv")
    
    if not results['high_divergences'].empty:
        results['high_divergences'].to_csv(f"{output_dir}high_divergences.csv", index=False)
        print(f"High divergences saved to high_divergences.csv")
    
    if not results['contrarian_opportunities'].empty:
        results['contrarian_opportunities'].to_csv(f"{output_dir}contrarian_opportunities.csv", index=False)
        print(f"Contrarian opportunities saved to contrarian_opportunities.csv")