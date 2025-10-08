import pandas as pd
import os

class BullishConvergenceService:
    """Service to consolidate bullish convergent stocks across all valuation methods"""
    
    def __init__(self):
        pass
    
    def consolidate_bullish_convergent_stocks(self, base_dir: str):
        """Consolidate all bullish convergent stocks from different methods into a single view"""
        
        methods = ['dcf', 'technical', 'comparable', 'startup']
        all_bullish = []
        convergent_type = 'bullish_convergent'
        
        for method in methods:
            file_path = f"{base_dir}{method}_{convergent_type}.csv"
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                if not df.empty:
                    df['method'] = method.upper()
                    df_subset = df[['ticker', 'method', 'our_upside', 'analyst_upside', 'deviation_score', 'analyst_count']].copy()
                    all_bullish.append(df_subset)
                    print(f"Loaded {len(df)} stocks from {method} method")
        
        if not all_bullish:
            print(f"No {convergent_type} files found!")
            return None
        
        # Combine all data
        combined_df = pd.concat(all_bullish, ignore_index=True)
        
        # Create pivot table showing which methods each stock appears in
        pivot_df = combined_df.pivot_table(
            index='ticker', 
            columns='method', 
            values='our_upside', 
            aggfunc='first'
        ).fillna('')
        
        # Add summary columns
        pivot_df['methods_count'] = (pivot_df != '').sum(axis=1)
        pivot_df['methods_list'] = pivot_df.apply(
            lambda row: ', '.join([col for col in ['DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP'] if row[col] != '']), 
            axis=1
        )
        
        # Get additional data for each stock
        stock_details = combined_df.groupby('ticker').agg({
            'analyst_upside': 'first',
            'analyst_count': 'first'
        }).round(1)
        
        # Merge with pivot table
        final_df = pivot_df.merge(stock_details, left_index=True, right_index=True)
        
        # Reorder columns
        cols = ['methods_count', 'methods_list', 'DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP', 'analyst_upside', 'analyst_count']
        final_df = final_df[cols]
        
        # Sort by number of methods (most convergent first)
        final_df = final_df.sort_values(['methods_count', 'analyst_upside'], ascending=[False, False])
        
        # Save consolidated file
        output_file = f"{base_dir}{convergent_type}_consolidated.csv"
        final_df.to_csv(output_file)
        
        # Generate and save report
        report = self.generate_consolidation_report(final_df, convergent_type)
        report_file = f"{base_dir}{convergent_type}_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\nConsolidation complete!")
        print(f"• Consolidated file: {convergent_type}_consolidated.csv")
        print(f"• Summary report: {convergent_type}_report.txt")
        print(f"• Total unique stocks: {len(final_df)}")
        print(f"• Multi-method convergent: {len(final_df[final_df['methods_count'] > 1])}")
        
        return final_df
    
    def generate_consolidation_report(self, final_df, convergent_type):
        """Generate comprehensive consolidation report"""
        
        report = []
        report.append(f"=== {convergent_type.upper()} CONVERGENT STOCKS CONSOLIDATION ===")
        report.append("")
        
        # Overall statistics
        total_unique_stocks = len(final_df)
        multi_method_stocks = len(final_df[final_df['methods_count'] > 1])
        
        report.append(f"SUMMARY STATISTICS:")
        report.append(f"• Total unique {convergent_type} stocks: {total_unique_stocks}")
        report.append(f"• Stocks convergent in multiple methods: {multi_method_stocks} ({multi_method_stocks/total_unique_stocks*100:.1f}%)")
        report.append("")
        
        # Method coverage
        for method in ['DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP']:
            count = len(final_df[final_df[method] != ''])
            report.append(f"• {method}: {count} stocks")
        
        report.append("")
        
        # Top multi-method convergent stocks
        multi_method = final_df[final_df['methods_count'] > 1].head(10)
        if not multi_method.empty:
            report.append("TOP MULTI-METHOD CONVERGENT STOCKS:")
            for ticker, row in multi_method.iterrows():
                report.append(f"• {ticker}: {row['methods_list']} (Analyst: +{row['analyst_upside']:.1f}%)")
            report.append("")
        
        # Strongest single-method convergent stocks
        for method in ['DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP']:
            single_method = final_df[(final_df['methods_count'] == 1) & (final_df[method] != '')].head(5)
            if not single_method.empty:
                report.append(f"TOP {method}-ONLY CONVERGENT STOCKS:")
                for ticker, row in single_method.iterrows():
                    our_upside = row[method]
                    report.append(f"• {ticker}: Our +{our_upside:.1f}% vs Analysts +{row['analyst_upside']:.1f}%")
                report.append("")
        
        return "\n".join(report)