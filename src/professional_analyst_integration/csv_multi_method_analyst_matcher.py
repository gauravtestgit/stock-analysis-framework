import pandas as pd
import numpy as np

class CSVMultiMethodAnalystMatcher:
    """Multi-method analyst matcher using data directly from stock_analysis.csv"""
    
    def __init__(self):
        pass
    
    def calculate_upside(self, target_price, current_price):
        """Calculate upside percentage"""
        if pd.isna(target_price) or pd.isna(current_price) or current_price <= 0:
            return None
        return ((target_price - current_price) / current_price) * 100
    
    def determine_alignment(self, our_upside, analyst_upside, threshold=20):
        """Determine alignment between our analysis and analyst consensus"""
        if pd.isna(our_upside) or pd.isna(analyst_upside):
            return 'No_Data'
        
        deviation = abs(our_upside - analyst_upside)
        
        # Both suggest significant upside (investment threshold)
        if our_upside >= threshold and analyst_upside >= threshold:
            return 'Investment_Aligned'
        
        # Close agreement (within 10%)
        if deviation <= 10:
            return 'Precise_Aligned'
        
        # Moderate agreement (within 25%)
        if deviation <= 25:
            return 'Moderate_Aligned'
        
        return 'Divergent'
    
    def compare_all_methods(self, csv_file_path, sample_size=None):
        """Compare all 4 valuation methods against analyst consensus using CSV data"""
        
        df = pd.read_csv(csv_file_path)
        if sample_size:
            df = df.head(sample_size)
        
        # Clean price columns
        price_columns = ['Current_Price', 'DCF_Price', 'Technical_Price', 'Comparable_Price', 'Startup_Price', 'Professional_Price']
        for col in price_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce')
        
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
            
            # Skip if no analyst data
            if pd.isna(row.get('Professional_Price')) or row.get('Professional_Price', 0) <= 0:
                continue
            
            current_price = row['Current_Price']
            analyst_target = row['Professional_Price']
            analyst_count = row.get('Professional_Count', 0)
            
            if pd.isna(current_price) or current_price <= 0:
                continue
            
            analyst_upside = self.calculate_upside(analyst_target, current_price)
            
            # Extract all 4 method prices
            methods = {
                'dcf': row.get('DCF_Price'),
                'technical': row.get('Technical_Price'),
                'comparable': row.get('Comparable_Price'),
                'startup': row.get('Startup_Price')
            }
            
            # Compare each method
            for method, price in methods.items():
                if pd.notna(price) and price > 0:
                    our_upside = self.calculate_upside(price, current_price)
                    alignment = self.determine_alignment(our_upside, analyst_upside)
                    
                    deviation_score = abs(our_upside - analyst_upside) if pd.notna(our_upside) and pd.notna(analyst_upside) else 999
                    
                    result = {
                        'ticker': ticker,
                        'method': method,
                        'our_price': price,
                        'analyst_target': analyst_target,
                        'current_price': current_price,
                        'our_upside': our_upside,
                        'analyst_upside': analyst_upside,
                        'deviation_score': deviation_score,
                        'alignment': alignment,
                        'both_bullish': our_upside >= 20 and analyst_upside >= 20,
                        'both_bearish': our_upside <= -10 and analyst_upside <= -10,
                        'analyst_count': analyst_count
                    }
                    
                    results[f'{method}_results'].append(result)
        
        # Calculate method summary statistics
        for method in ['dcf', 'technical', 'comparable', 'startup']:
            method_results = results[f'{method}_results']
            if method_results:
                aligned = len([r for r in method_results if r['alignment'] in ['Investment_Aligned', 'Precise_Aligned', 'Moderate_Aligned']])
                bullish_convergent = len([r for r in method_results if r['both_bullish']])
                valid_deviations = [r['deviation_score'] for r in method_results if r['deviation_score'] < 999]
                avg_deviation = np.mean(valid_deviations) if valid_deviations else 0
                
                results['method_summary'][method] = {
                    'total_comparisons': len(method_results),
                    'aligned_count': aligned,
                    'bullish_convergent': bullish_convergent,
                    'alignment_rate': aligned / len(method_results) * 100 if method_results else 0,
                    'avg_deviation': avg_deviation
                }
        
        return results
    
    def generate_multi_method_report(self, results):
        """Generate comprehensive multi-method comparison report"""
        
        report = []
        report.append("=== CSV MULTI-METHOD ANALYST ALIGNMENT REPORT ===")
        report.append("")
        
        # Method Performance Summary
        report.append("METHOD PERFORMANCE SUMMARY:")
        summary = results['method_summary']
        
        method_performance = []
        for method, stats in summary.items():
            if stats['total_comparisons'] > 0:
                method_performance.append((method, stats['alignment_rate'], stats))
        
        # Sort by alignment rate
        method_performance.sort(key=lambda x: x[1], reverse=True)
        
        for method, rate, stats in method_performance:
            report.append(f"{method.upper()} METHOD:")
            report.append(f"  • Total comparisons: {stats['total_comparisons']}")
            report.append(f"  • Alignment rate: {stats['alignment_rate']:.1f}%")
            report.append(f"  • Bullish convergent: {stats['bullish_convergent']}")
            report.append(f"  • Avg deviation: {stats['avg_deviation']:.1f}%")
            report.append("")
        
        # Best performing method
        if method_performance:
            best_method, best_rate, _ = method_performance[0]
            report.append(f"BEST PERFORMING METHOD: {best_method.upper()} ({best_rate:.1f}% alignment)")
            report.append("")
        
        # Top aligned stocks by method
        for method in ['dcf', 'technical', 'comparable', 'startup']:
            method_results = results[f'{method}_results']
            aligned_stocks = [r for r in method_results if r['alignment'] in ['Investment_Aligned', 'Precise_Aligned']]
            aligned_stocks.sort(key=lambda x: x['deviation_score'])  # Sort by best alignment
            
            if aligned_stocks:
                report.append(f"{method.upper()} TOP ALIGNED STOCKS ({len(aligned_stocks)} found):")
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
                aligned = df[df['alignment'].isin(['Investment_Aligned', 'Precise_Aligned', 'Moderate_Aligned'])]
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
    matcher = CSVMultiMethodAnalystMatcher()
    
    # Analyze stock data from CSV
    csv_path = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\src\\resources\\stock_analysis.csv"
    
    print("Running CSV-based multi-method analyst comparison...")
    results = matcher.compare_all_methods(csv_path, sample_size=None)  # Process all stocks
    
    # Generate comprehensive report
    report = matcher.generate_multi_method_report(results)
    print("\n" + report)
    
    # Save main report
    output_dir = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\src\\resources\\analysis\\"
    report_file = f"{output_dir}csv_multi_method_analyst_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    # Save method-specific files
    files_created = matcher.save_method_specific_files(results, output_dir)
    
    print(f"\nReport saved to: {report_file}")
    print(f"Method-specific files created: {len(files_created)}")
    for file in files_created:
        print(f"  • {file}")