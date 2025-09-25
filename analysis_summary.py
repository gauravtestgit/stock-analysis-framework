import pandas as pd
import json
from collections import Counter

def analyze_batch_results():
    """Analyze the batch analysis results and provide insights"""
    
    # Read results
    df = pd.read_csv("financial_analyst/resources/batch_analysis_results.csv")
    
    print("=" * 80)
    print("STOCK ANALYSIS BATCH RESULTS SUMMARY (Full Dataset Analysis)")
    print("=" * 80)
    
    # Overall Statistics
    total_stocks = df['Total_Stocks'].sum()
    print(f"\nOVERALL STATISTICS:")
    print(f"   • Total Stocks Analyzed: {total_stocks}")
    print(f"   • Number of Batches: {len(df)}")
    print(f"   • Average Stocks per Batch: {total_stocks/len(df):.1f}")
    
    # Quality Distribution Analysis
    print(f"\nQUALITY DISTRIBUTION ANALYSIS:")
    all_quality = {}
    for quality_str in df['Quality_Distribution']:
        quality_dict = json.loads(quality_str)
        for grade, count in quality_dict.items():
            all_quality[grade] = all_quality.get(grade, 0) + count
    
    total_graded = sum(all_quality.values())
    for grade in ['A', 'B', 'C', 'D']:
        count = all_quality.get(grade, 0)
        pct = (count/total_graded)*100 if total_graded > 0 else 0
        print(f"   • Grade {grade}: {count} stocks ({pct:.1f}%)")
    
    # Company Type Analysis
    print(f"\nCOMPANY TYPE DISTRIBUTION:")
    all_types = {}
    for types_str in df['Company_Types']:
        types_dict = json.loads(types_str)
        for comp_type, count in types_dict.items():
            all_types[comp_type] = all_types.get(comp_type, 0) + count
    
    for comp_type, count in sorted(all_types.items(), key=lambda x: x[1], reverse=True):
        pct = (count/total_stocks)*100
        print(f"   • {comp_type}: {count} stocks ({pct:.1f}%)")
    
    # Validation Issues Analysis
    print(f"\nVALIDATION ISSUES ANALYSIS:")
    all_issues = Counter()
    problematic_stocks = {}
    
    for issues_str in df['Validation_Issues']:
        if issues_str and issues_str != '{}':
            issues_dict = json.loads(issues_str)
            all_issues.update(issues_dict)
    
    for problems_str in df['Problematic_Stocks']:
        if problems_str and problems_str != '{}':
            problems_dict = json.loads(problems_str)
            problematic_stocks.update(problems_dict)
    
    print(f"   • Total Validation Issues: {sum(all_issues.values())}")
    for issue, count in all_issues.most_common(5):
        print(f"   • {issue}: {count} occurrences")
    
    # DCF Analysis
    print(f"\nDCF ANALYSIS:")
    dcf_discounts = []
    for discount_str in df['Avg_DCF_Discount']:
        if discount_str and discount_str != 'inf%':
            try:
                discount = float(discount_str.replace('%', ''))
                if abs(discount) < 10000:  # Filter extreme outliers
                    dcf_discounts.append(discount)
            except:
                continue
    
    if dcf_discounts:
        avg_discount = sum(dcf_discounts) / len(dcf_discounts)
        print(f"   • Average DCF Discount/Premium: {avg_discount:.1f}%")
        print(f"   • Positive DCF (Undervalued): {len([d for d in dcf_discounts if d > 0])} batches")
        print(f"   • Negative DCF (Overvalued): {len([d for d in dcf_discounts if d < 0])} batches")
    
    # Recommendations Analysis
    print(f"\nRECOMMENDATIONS ANALYSIS:")
    all_recs = {}
    for recs_str in df['Recommendation_Summary']:
        recs_dict = json.loads(recs_str)
        for rec, count in recs_dict.items():
            all_recs[rec] = all_recs.get(rec, 0) + count
    
    for rec, count in sorted(all_recs.items(), key=lambda x: x[1], reverse=True):
        pct = (count/total_stocks)*100
        print(f"   • {rec}: {count} stocks ({pct:.1f}%)")
    
    # Top Opportunities
    print(f"\nTOP OPPORTUNITIES IDENTIFIED:")
    all_opportunities = []
    for opps in df['Top_Opportunities']:
        if pd.notna(opps) and str(opps).strip():
            all_opportunities.extend([o.strip() for o in str(opps).split(',') if o.strip()])
    
    opp_counter = Counter(all_opportunities)
    for stock, mentions in opp_counter.most_common(10):
        print(f"   • {stock}: Mentioned in {mentions} batch(es)")
    
    # Key Insights Summary
    print(f"\nKEY INSIGHTS SUMMARY:")
    insights = []
    for insight_str in df['Key_Insights']:
        if pd.notna(insight_str) and str(insight_str).strip():
            insights.extend([i.strip() for i in str(insight_str).split(';')])
    
    # Count common patterns
    quality_concerns = len([i for i in insights if 'Quality concern' in i])
    startup_concentration = len([i for i in insights if 'startup concentration' in i])
    validation_issues = len([i for i in insights if 'Validation issues' in i])
    
    print(f"   • Quality Concerns: {quality_concerns} batches")
    print(f"   • High Startup Concentration: {startup_concentration} batches")
    print(f"   • Validation Issues: {validation_issues} batches")
    
    # Most Problematic Stocks
    print(f"\nMOST PROBLEMATIC STOCKS:")
    stock_issue_count = {}
    for problems_dict in [json.loads(p) for p in df['Problematic_Stocks'] if p and p != '{}']:
        for stock, issues in problems_dict.items():
            stock_issue_count[stock] = len(issues)
    
    for stock, issue_count in sorted(stock_issue_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   • {stock}: {issue_count} validation issues")
    
    print(f"\n" + "=" * 80)

if __name__ == "__main__":
    analyze_batch_results()