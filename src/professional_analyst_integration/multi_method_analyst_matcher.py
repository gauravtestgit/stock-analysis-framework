import pandas as pd
import numpy as np
from . analyst_integration import AnalystDataProvider, calculate_consensus_deviation

class MultiMethodAnalystMatcher:
    def __init__(self):
        self.analyst_provider = AnalystDataProvider()
    
    def compare_all_methods(self, csv_file_path, sample_size=100):
        """Compare all 4 valuation methods against analyst consensus"""
        
        df = pd.read_csv(csv_file_path)
        if sample_size:
            df = df.head(sample_size)
        
        results = {
            'dcf_results': [],
            'technical_results': [],
            'comparable_results': [],
            'startup_results': [],
            'method_summary': {}
        }
        
        print(f"Analyzing {len(df)} stocks across 4 valuation methods...")
        
        for idx, row in df.iterrows():
            ticker = row['Ticker']
            print(f"Processing {ticker} ({idx+1}/{len(df)})")
            
            try:
                analyst_data = self.analyst_provider.get_analyst_data(ticker)
                if not analyst_data.get('target_price'):
                    continue
                
                current_price = pd.to_numeric(str(row['Current_Price']).replace('$', '').replace(',', ''), errors='coerce')
                analyst_target = analyst_data.get('target_price')
                
                # Extract all 4 prices
                prices = {
                    'dcf': pd.to_numeric(str(row['DCF_Price']).replace('$', '').replace(',', ''), errors='coerce'),
                    'technical': pd.to_numeric(str(row['Technical_Price']).replace('$', '').replace(',', ''), errors='coerce'),
                    'comparable': pd.to_numeric(str(row['Comparable_Price']).replace('$', '').replace(',', ''), errors='coerce'),
                    'startup': pd.to_numeric(str(row['Startup_Price']).replace('$', '').replace(',', ''), errors='coerce')
                }
                
                # Compare each method
                for method, price in prices.items():
                    if pd.notna(price) and price > 0:
                        comparison = calculate_consensus_deviation(price, analyst_target, current_price)
                        
                        result = {
                            'ticker': ticker,
                            'method': method,
                            'our_price': price,
                            'analyst_target': analyst_target,
                            'current_price': current_price,
                            'our_upside': comparison.get('our_upside', 0),
                            'analyst_upside': comparison.get('analyst_upside', 0),
                            'deviation_score': comparison.get('deviation_score', 999),
                            'alignment': comparison.get('alignment', 'Divergent'),
                            'both_bullish': comparison.get('both_bullish', False),
                            'both_bearish': comparison.get('both_bearish', False),
                            'analyst_count': analyst_data.get('analyst_count', 0)
                        }
                        
                        results[f'{method}_results'].append(result)
                        
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                continue
        
        # Calculate method summary statistics
        for method in ['dcf', 'technical', 'comparable', 'startup']:
            method_results = results[f'{method}_results']
            if method_results:
                aligned = len([r for r in method_results if r['alignment'] != 'Divergent'])
                bullish_convergent = len([r for r in method_results if r['both_bullish']])
                avg_deviation = np.mean([r['deviation_score'] for r in method_results if r['deviation_score'] < 999])
                
                results['method_summary'][method] = {
                    'total_comparisons': len(method_results),
                    'aligned_count': aligned,
                    'bullish_convergent': bullish_convergent,
                    'alignment_rate': aligned / len(method_results) * 100,
                    'avg_deviation': avg_deviation
                }
        
        return results
    
    def generate_multi_method_report(self, results):
        """Generate comprehensive multi-method comparison report"""
        
        report = []
        report.append("=== MULTI-METHOD ANALYST ALIGNMENT REPORT ===")
        report.append("")
        
        # Method Performance Summary
        report.append("METHOD PERFORMANCE SUMMARY:")
        summary = results['method_summary']
        
        for method, stats in summary.items():
            if stats['total_comparisons'] > 0:
                report.append(f"{method.upper()} METHOD:")
                report.append(f"  • Total comparisons: {stats['total_comparisons']}")
                report.append(f"  • Alignment rate: {stats['alignment_rate']:.1f}%")
                report.append(f"  • Bullish convergent: {stats['bullish_convergent']}")
                report.append(f"  • Avg deviation: {stats['avg_deviation']:.1f}%")
                report.append("")
        
        # Best performing method
        best_method = max(summary.keys(), key=lambda x: summary[x]['alignment_rate'] if summary[x]['total_comparisons'] > 0 else 0)
        report.append(f"BEST PERFORMING METHOD: {best_method.upper()} ({summary[best_method]['alignment_rate']:.1f}% alignment)")
        report.append("")
        
        # Top aligned stocks by method
        for method in ['dcf', 'technical', 'comparable', 'startup']:
            method_results = results[f'{method}_results']
            aligned_stocks = [r for r in method_results if r['alignment'] in ['Investment_Aligned', 'Precise_Aligned']]
            
            if aligned_stocks:
                report.append(f"{method.upper()} ALIGNED STOCKS ({len(aligned_stocks)} found):")
                for stock in aligned_stocks[:5]:  # Top 5
                    report.append(f"  • {stock['ticker']}: Our {stock['our_upside']:+.1f}% vs Analysts {stock['analyst_upside']:+.1f}% (Dev: {stock['deviation_score']:.1f}%)")
                if len(aligned_stocks) > 5:
                    report.append(f"  ... and {len(aligned_stocks) - 5} more")
                report.append("")
        
        return "\n".join(report)
    
    def save_method_specific_files(self, results, output_dir):
        """Save separate files for each method's results"""
        
        files_created = []
        
        for method in ['dcf', 'technical', 'comparable', 'startup']:
            method_results = results[f'{method}_results']
            if method_results:
                # Create DataFrame
                df = pd.DataFrame(method_results)
                
                # Separate by alignment type
                aligned = df[df['alignment'].isin(['Investment_Aligned', 'Precise_Aligned'])]
                divergent = df[df['alignment'] == 'Divergent']
                bullish_convergent = df[df['both_bullish'] == True]
                
                # Save method-specific files
                if not aligned.empty:
                    aligned_file = f"{output_dir}{method}_aligned.csv"
                    aligned.to_csv(aligned_file, index=False)
                    files_created.append(aligned_file)
                
                if not divergent.empty:
                    divergent_file = f"{output_dir}{method}_divergent.csv"
                    divergent.to_csv(divergent_file, index=False)
                    files_created.append(divergent_file)
                
                if not bullish_convergent.empty:
                    bullish_file = f"{output_dir}{method}_bullish_convergent.csv"
                    bullish_convergent.to_csv(bullish_file, index=False)
                    files_created.append(bullish_file)
        
        return files_created

if __name__ == "__main__":
    matcher = MultiMethodAnalystMatcher()
    
    # Analyze stock data
    csv_path = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\stock_analysis.csv"
    
    print("Running multi-method analyst comparison...")
    results = matcher.compare_all_methods(csv_path, sample_size=5064)  # Test with 200 stocks
    
    # Generate comprehensive report
    report = matcher.generate_multi_method_report(results)
    print("\n" + report)
    
    # Save main report
    output_dir = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\analysis\\"
    report_file = f"{output_dir}multi_method_analyst_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    # Save method-specific files
    files_created = matcher.save_method_specific_files(results, output_dir)
    
    print(f"\nReport saved to: {report_file}")
    print(f"Method-specific files created: {len(files_created)}")
    for file in files_created:
        filename = file.split('\\')[-1]
        print(f"  • {filename}")