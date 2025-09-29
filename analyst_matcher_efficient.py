import pandas as pd
import numpy as np
import json

class EfficientAnalystMatcher:
    def __init__(self):
        pass
    
    def analyze_batch_results(self, batch_results_path):
        """Analyze batch results to find analyst alignment patterns"""
        
        df = pd.read_csv(batch_results_path)
        
        # Parse JSON columns
        df['Problematic_Stocks_Dict'] = df['Problematic_Stocks'].apply(lambda x: json.loads(x) if pd.notna(x) and x != '{}' else {})
        df['Validation_Issues_Dict'] = df['Validation_Issues'].apply(lambda x: json.loads(x) if pd.notna(x) and x != '{}' else {})
        
        # Extract analyst alignment metrics
        alignment_summary = {
            'total_batches': len(df),
            'avg_consensus_deviation': df['Avg_Consensus_Deviation'].str.rstrip('%').astype(float).mean(),
            'high_divergence_batches': len(df[df['High_Divergence_Count'] > 0]),
            'contrarian_opportunities': [],
            'investment_aligned_stocks': [],
            'high_divergence_stocks': []
        }
        
        # Collect contrarian opportunities
        for _, row in df.iterrows():
            if pd.notna(row['Contrarian_Opportunities']) and row['Contrarian_Opportunities']:
                tickers = [t.strip() for t in str(row['Contrarian_Opportunities']).split(',')]
                alignment_summary['contrarian_opportunities'].extend(tickers)
        
        # Analyze validation issues for analyst-related problems
        analyst_issues = {}
        for _, row in df.iterrows():
            issues = row['Validation_Issues_Dict']
            for issue_type, count in issues.items():
                if 'ANALYST' in issue_type or 'CONTRARIAN' in issue_type:
                    analyst_issues[issue_type] = analyst_issues.get(issue_type, 0) + count
        
        # Extract stocks with specific analyst issues and identify aligned stocks
        all_stocks_with_analyst_data = set()
        
        for _, row in df.iterrows():
            problematic = row['Problematic_Stocks_Dict']
            
            # Track all stocks that have analyst data (mentioned in validation)
            for ticker, issues in problematic.items():
                has_analyst_data = any('ANALYST_DIVERGENCE' in issue or 'CONTRARIAN_POSITION' in issue for issue in issues)
                if has_analyst_data:
                    all_stocks_with_analyst_data.add(ticker)
                
                for issue in issues:
                    if 'ANALYST_DIVERGENCE' in issue and 'deviation from consensus' in issue:
                        deviation = float(issue.split('deviation from consensus')[0].split(':')[1].strip().rstrip('%'))
                        if deviation > 100:
                            alignment_summary['high_divergence_stocks'].append({
                                'ticker': ticker,
                                'deviation': deviation,
                                'batch': row['Batch_Number']
                            })
                        elif deviation <= 50:  # Low deviation = good alignment
                            alignment_summary['investment_aligned_stocks'].append({
                                'ticker': ticker,
                                'deviation': deviation,
                                'batch': row['Batch_Number']
                            })
                    elif 'CONTRARIAN_POSITION' in issue:
                        alignment_summary['contrarian_opportunities'].append(ticker)
        
        # Identify investment aligned stocks (those with analyst data but no major issues)
        high_div_tickers = {stock['ticker'] for stock in alignment_summary['high_divergence_stocks']}
        contrarian_tickers = set(alignment_summary['contrarian_opportunities'])
        
        # Stocks with analyst data but not in problematic categories are likely aligned
        for ticker in all_stocks_with_analyst_data:
            if ticker not in high_div_tickers and ticker not in contrarian_tickers:
                alignment_summary['investment_aligned_stocks'].append({
                    'ticker': ticker,
                    'deviation': 'Unknown',
                    'batch': 'Multiple'
                })
        
        return alignment_summary, analyst_issues
    
    def generate_efficient_report(self, alignment_summary, analyst_issues):
        """Generate report from batch analysis results"""
        
        report = []
        report.append("=== EFFICIENT ANALYST ALIGNMENT REPORT ===")
        report.append("(Based on batch analysis results)")
        report.append("")
        
        # Overall statistics
        report.append("OVERALL STATISTICS:")
        report.append(f"• Total batches analyzed: {alignment_summary['total_batches']}")
        report.append(f"• Average consensus deviation: {alignment_summary['avg_consensus_deviation']:.1f}%")
        report.append(f"• Batches with high divergence: {alignment_summary['high_divergence_batches']}")
        report.append("")
        
        # Analyst validation issues
        if analyst_issues:
            report.append("ANALYST-RELATED VALIDATION ISSUES:")
            for issue_type, count in sorted(analyst_issues.items(), key=lambda x: x[1], reverse=True):
                report.append(f"• {issue_type}: {count} occurrences")
            report.append("")
        
        # High divergence stocks
        high_div_stocks = alignment_summary['high_divergence_stocks']
        if high_div_stocks:
            report.append(f"HIGH DIVERGENCE STOCKS ({len(high_div_stocks)} found):")
            report.append("Stocks with >100% deviation from analyst consensus")
            report.append("")
            
            # Sort by deviation
            high_div_stocks.sort(key=lambda x: x['deviation'], reverse=True)
            for stock in high_div_stocks[:10]:  # Top 10
                report.append(f"• {stock['ticker']}: {stock['deviation']:.1f}% deviation (Batch {stock['batch']})")
            
            if len(high_div_stocks) > 10:
                report.append(f"... and {len(high_div_stocks) - 10} more")
            report.append("")
        
        # Investment aligned stocks
        aligned_stocks = alignment_summary['investment_aligned_stocks']
        if aligned_stocks:
            report.append(f"INVESTMENT ALIGNED STOCKS ({len(aligned_stocks)} found):")
            report.append("Stocks with good alignment to analyst consensus")
            report.append("")
            
            # Show stocks with known low deviation first
            low_dev_stocks = [s for s in aligned_stocks if isinstance(s.get('deviation'), (int, float))]
            low_dev_stocks.sort(key=lambda x: x['deviation'])
            
            for stock in low_dev_stocks[:10]:
                report.append(f"• {stock['ticker']}: {stock['deviation']:.1f}% deviation (Batch {stock['batch']})")
            
            # Show other aligned stocks
            other_stocks = [s for s in aligned_stocks if not isinstance(s.get('deviation'), (int, float))]
            for stock in other_stocks[:5]:
                report.append(f"• {stock['ticker']}: Good alignment (no major issues)")
            
            if len(aligned_stocks) > 15:
                report.append(f"... and {len(aligned_stocks) - 15} more")
            report.append("")
        
        # Contrarian opportunities
        contrarian_stocks = list(set(alignment_summary['contrarian_opportunities']))  # Remove duplicates
        if contrarian_stocks:
            report.append(f"CONTRARIAN OPPORTUNITIES ({len(contrarian_stocks)} unique stocks):")
            report.append("Stocks where our analysis opposes analyst consensus")
            report.append("")
            
            for i, ticker in enumerate(contrarian_stocks[:15]):  # Top 15
                report.append(f"• {ticker}")
                if (i + 1) % 5 == 0:  # New line every 5 stocks
                    report.append("")
            
            if len(contrarian_stocks) > 15:
                report.append(f"... and {len(contrarian_stocks) - 15} more")
            report.append("")
        
        # Investment insights
        report.append("INVESTMENT INSIGHTS:")
        if alignment_summary['avg_consensus_deviation'] > 100:
            report.append("• High average deviation suggests significant disagreement with analyst consensus")
        elif alignment_summary['avg_consensus_deviation'] < 50:
            report.append("• Moderate deviation suggests reasonable alignment with analyst consensus")
        
        if len(contrarian_stocks) > 20:
            report.append("• High number of contrarian positions - potential for unique opportunities")
        
        if alignment_summary['high_divergence_batches'] > alignment_summary['total_batches'] * 0.3:
            report.append("• Many batches show high divergence - systematic differences in methodology")
        
        return "\n".join(report)

if __name__ == "__main__":
    # Initialize efficient matcher
    matcher = EfficientAnalystMatcher()
    
    # Analyze batch results
    batch_results_path = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\batch_analysis_results.csv"
    
    print("Analyzing batch results for analyst alignment...")
    alignment_summary, analyst_issues = matcher.analyze_batch_results(batch_results_path)
    
    # Generate report
    report = matcher.generate_efficient_report(alignment_summary, analyst_issues)
    print("\n" + report)
    
    # Save report
    report_file = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\efficient_analyst_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    
    # Save detailed data
    output_dir = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\"
    
    # Investment aligned stocks
    if alignment_summary['investment_aligned_stocks']:
        aligned_df = pd.DataFrame(alignment_summary['investment_aligned_stocks'])
        aligned_df.to_csv(f"{output_dir}investment_aligned_efficient.csv", index=False)
        print(f"Investment aligned stocks saved to investment_aligned_efficient.csv")
    
    # High divergence stocks
    if alignment_summary['high_divergence_stocks']:
        high_div_df = pd.DataFrame(alignment_summary['high_divergence_stocks'])
        high_div_df.to_csv(f"{output_dir}high_divergence_efficient.csv", index=False)
        print(f"High divergence stocks saved to high_divergence_efficient.csv")
    
    # Contrarian opportunities
    if alignment_summary['contrarian_opportunities']:
        contrarian_df = pd.DataFrame({'ticker': list(set(alignment_summary['contrarian_opportunities']))})
        contrarian_df.to_csv(f"{output_dir}contrarian_efficient.csv", index=False)
        print(f"Contrarian opportunities saved to contrarian_efficient.csv")