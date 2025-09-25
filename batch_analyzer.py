import pandas as pd
import numpy as np
from datetime import datetime
import json
import re
# from analyst_integration import AnalystDataProvider, ProfessionalVsAlgorithmicComparison, validate_against_analysts
# Temporarily disable analyst integration for testing

def validate_price_accuracy(row):
    """Validate if DCF, technical, and comparable prices seem reasonable"""
    validations = []
    
    # Extract numeric values
    current_price = pd.to_numeric(str(row['Current_Price']).replace('$', '').replace(',', ''), errors='coerce')
    dcf_price = pd.to_numeric(str(row['DCF_Price']).replace('$', '').replace(',', ''), errors='coerce')
    tech_price = pd.to_numeric(str(row['Technical_Price']).replace('$', '').replace(',', ''), errors='coerce')
    comp_price = pd.to_numeric(str(row['Comparable_Price']).replace('$', '').replace(',', ''), errors='coerce')
    
    # Get company fundamentals
    pe_ratio = pd.to_numeric(row.get('PE_Ratio', 0), errors='coerce') or 0
    revenue_growth = pd.to_numeric(row.get('Revenue_Growth', 0), errors='coerce') or 0
    quality_score = pd.to_numeric(row.get('Quality_Score', 0), errors='coerce') or 0
    company_type = str(row.get('Company_Type', '')).lower()
    sector = str(row.get('Sector', ''))
    
    # DCF Validation
    if pd.notna(dcf_price) and dcf_price > 0 and pd.notna(current_price) and current_price > 0:
        dcf_premium = (dcf_price - current_price) / current_price
        
        # Check if DCF makes sense based on company type
        if 'startup_loss_making' in company_type and dcf_price > 0:
            validations.append("DCF_WARNING: Positive DCF for loss-making startup questionable")
        
        # Extreme DCF premiums/discounts
        if abs(dcf_premium) > 3:  # >300% difference
            validations.append(f"DCF_EXTREME: {dcf_premium*100:.0f}% difference from current price")
        
        # DCF vs Quality correlation
        if dcf_premium > 1 and quality_score < 30:  # High DCF upside but poor quality
            validations.append("DCF_QUALITY_MISMATCH: High DCF upside despite poor quality metrics")
    
    # Technical Price Validation
    if pd.notna(tech_price) and tech_price > 0 and pd.notna(current_price) and current_price > 0:
        tech_premium = (tech_price - current_price) / current_price
        
        # Extreme technical targets
        if abs(tech_premium) > 2:  # >200% difference
            validations.append(f"TECH_EXTREME: {tech_premium*100:.0f}% technical target seems aggressive")
    
    # Comparable Price Validation
    if pd.notna(comp_price) and comp_price > 0 and pd.notna(current_price) and current_price > 0:
        comp_premium = (comp_price - current_price) / current_price
        
        # PE ratio vs comparable price consistency
        if pe_ratio > 0:
            if comp_premium > 1 and pe_ratio > 50:  # High comparable target but already expensive
                validations.append("COMP_PE_MISMATCH: High comparable target despite elevated PE ratio")
            elif comp_premium < -0.5 and pe_ratio < 15:  # Low comparable target but cheap PE
                validations.append("COMP_UNDERVALUED: Comparable suggests undervaluation vs PE ratio")
    
    # Cross-validation between methods
    prices = [p for p in [dcf_price, tech_price, comp_price] if pd.notna(p) and p > 0]
    if len(prices) >= 2:
        price_range = (max(prices) - min(prices)) / min(prices)
        if price_range > 5:  # Methods disagree by >500%
            validations.append(f"METHOD_DIVERGENCE: Valuation methods highly divergent ({price_range*100:.0f}% range)")
    
    # Sector-specific validations
    if 'Technology' in sector:
        if (pd.notna(pe_ratio) and pe_ratio > 0 and pe_ratio < 10 and 
            pd.notna(dcf_price) and dcf_price > 0 and pd.notna(current_price) and current_price > 0):
            dcf_premium_check = (dcf_price - current_price) / current_price
            if dcf_premium_check > 0.5:
                validations.append("TECH_ANOMALY: Low PE tech stock with high DCF upside unusual")
    
    elif 'Healthcare' in sector and 'Biotechnology' in str(row.get('Industry', '')):
        if dcf_price > 0 and 'startup_loss_making' in company_type:
            validations.append("BIOTECH_DCF: DCF for pre-revenue biotech should be treated with caution")
    
    return validations

def analyze_batch(df_batch, batch_num, start_row, end_row):
    """Analyze a batch of 20 rows and return summary statistics"""
    
    # Initialize analyst integration (disabled for testing)
    # analyst_provider = AnalystDataProvider()
    # comparison_engine = ProfessionalVsAlgorithmicComparison()
    
    # Basic stats
    total_stocks = len(df_batch)
    
    # Sector distribution
    sector_counts = df_batch['Sector'].value_counts().to_dict()
    top_sectors = dict(list(sector_counts.items())[:3])
    
    # Company types
    company_types = df_batch['Company_Type'].value_counts().to_dict()
    
    # DCF Analysis
    dcf_prices = pd.to_numeric(df_batch['DCF_Price'].str.replace('$', '').str.replace(',', ''), errors='coerce')
    current_prices = pd.to_numeric(df_batch['Current_Price'].str.replace('$', '').str.replace(',', ''), errors='coerce')
    
    # Calculate DCF discount/premium
    dcf_discount = []
    for i in range(len(dcf_prices)):
        if pd.notna(dcf_prices.iloc[i]) and pd.notna(current_prices.iloc[i]) and dcf_prices.iloc[i] > 0:
            discount = ((dcf_prices.iloc[i] - current_prices.iloc[i]) / current_prices.iloc[i]) * 100
            dcf_discount.append(discount)
    
    avg_dcf_discount = np.mean(dcf_discount) if dcf_discount else 0
    
    # Quality distribution
    quality_counts = df_batch['Quality_Grade'].value_counts().to_dict()
    
    # Risk levels
    risk_counts = df_batch['Risk_Level'].value_counts().to_dict()
    
    # Recommendations
    rec_counts = df_batch['Recommendation'].value_counts().to_dict()
    
    # Top opportunities (Strong Buy with good quality)
    opportunities = df_batch[
        (df_batch['Recommendation'].isin(['BUY', 'STRONG BUY'])) & 
        (df_batch['Quality_Grade'].isin(['A', 'B']))
    ]['Ticker'].tolist()
    
    # Price Validation Analysis (Enhanced with Analyst Data)
    all_validations = []
    validation_summary = {}
    analyst_comparisons = []
    consensus_deviations = []
    
    for idx, row in df_batch.iterrows():
        # Original validations
        validations = validate_price_accuracy(row)
        
        # Analyst-enhanced validations (disabled for testing)
        # try:
        #     analyst_data = analyst_provider.get_analyst_data(row['Ticker'])
        #     analyst_validations = validate_against_analysts(row, analyst_data)
        #     validations.extend(analyst_validations)
        #     
        #     # Professional vs Algorithmic comparison
        #     comparison = comparison_engine.compare_analysis(row)
        #     analyst_comparisons.append(comparison)
        #     
        #     if comparison.get('deviation_score'):
        #         consensus_deviations.append(comparison['deviation_score'])
        #         
        # except Exception as e:
        #     print(f"Analyst validation error for {row['Ticker']}: {e}")
        pass
        
        if validations:
            all_validations.extend(validations)
            validation_summary[row['Ticker']] = validations
    
    # Count validation issues
    validation_counts = {}
    for validation in all_validations:
        issue_type = validation.split(':')[0]
        validation_counts[issue_type] = validation_counts.get(issue_type, 0) + 1
    
    # Key insights
    insights = []
    
    # High DCF upside stocks
    high_upside = df_batch[dcf_prices > current_prices * 1.5]['Ticker'].tolist()
    if high_upside:
        insights.append(f"High DCF upside: {', '.join(high_upside[:3])}")
    
    # Quality concerns
    poor_quality = len(df_batch[df_batch['Quality_Grade'] == 'D'])
    if poor_quality > total_stocks * 0.5:
        insights.append(f"Quality concern: {poor_quality}/{total_stocks} stocks rated D")
    
    # Startup concentration
    startups = len(df_batch[df_batch['Company_Type'].str.contains('startup', na=False)])
    if startups > total_stocks * 0.3:
        insights.append(f"High startup concentration: {startups}/{total_stocks}")
    
    # Analyst Consensus Analysis
    avg_consensus_deviation = np.mean(consensus_deviations) if consensus_deviations else 0
    high_divergence_stocks = [c['ticker'] for c in analyst_comparisons if c.get('assessment') == 'HIGH_DIVERGENCE']
    contrarian_opportunities = [c['ticker'] for c in analyst_comparisons if c.get('assessment') == 'CONTRARIAN_OPPORTUNITY']
    
    # Validation insights
    if validation_counts:
        top_issues = sorted(validation_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        insights.append(f"Validation issues: {', '.join([f'{k}({v})' for k, v in top_issues])}")
    
    # Analyst insights
    if avg_consensus_deviation > 0:
        insights.append(f"Avg consensus deviation: {avg_consensus_deviation:.1f}%")
    if contrarian_opportunities:
        insights.append(f"Contrarian opportunities: {', '.join(contrarian_opportunities[:3])}")
    
    return {
        'Batch_Number': batch_num,
        'Rows_Analyzed': f"{start_row}-{end_row}",
        'Total_Stocks': total_stocks,
        'Sector_Distribution': json.dumps(top_sectors),
        'Company_Types': json.dumps(company_types),
        'Avg_DCF_Discount': f"{avg_dcf_discount:.1f}%",
        'Quality_Distribution': json.dumps(quality_counts),
        'Risk_Summary': json.dumps(risk_counts),
        'Recommendation_Summary': json.dumps(rec_counts),
        'Top_Opportunities': ', '.join(opportunities[:5]),
        'Validation_Issues': json.dumps(validation_counts),
        'Problematic_Stocks': json.dumps({k: v[:2] for k, v in validation_summary.items()}),
        'Avg_Consensus_Deviation': f"{avg_consensus_deviation:.1f}%",
        'High_Divergence_Count': len(high_divergence_stocks),
        'Contrarian_Opportunities': ', '.join(contrarian_opportunities[:5]),
        'Analyst_Coverage_Avg': np.mean([c.get('analyst_count', 0) for c in analyst_comparisons]) if analyst_comparisons else 0,
        'Key_Insights': '; '.join(insights),
        'Processing_Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def process_file_in_batches(file_path, batch_size=20):
    """Process the CSV file in batches"""
    
    # Read the file
    df = pd.read_csv(file_path)
    total_rows = len(df)
    
    print(f"Processing {total_rows} rows in batches of {batch_size}")
    
    results = []
    batch_num = 1
    
    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(start_idx + batch_size, total_rows)
        batch_df = df.iloc[start_idx:end_idx]
        
        print(f"Processing batch {batch_num}: rows {start_idx+1}-{end_idx}")
        
        # Analyze this batch
        batch_result = analyze_batch(batch_df, batch_num, start_idx+1, end_idx)
        results.append(batch_result)
        
        batch_num += 1
        
        # Process all batches in the dataset
        # Removed batch limit to process full dataset
    
    return results

if __name__ == "__main__":
    file_path = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\stock_analysis1.csv"
    results = process_file_in_batches(file_path)
    
    # Convert to DataFrame and save
    results_df = pd.DataFrame(results)
    output_path = "c:\\Users\\x_gau\\source\\repos\\agentic\\langchain\\tutorials\\finance-app\\financial_analyst\\resources\\batch_analysis_results.csv"
    
    # Append to existing file
    results_df.to_csv(output_path, mode='a', header=False, index=False)
    
    print(f"Analysis complete. Results saved to {output_path}")
    print(f"Processed {len(results)} batches")