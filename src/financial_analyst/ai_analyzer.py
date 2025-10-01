from typing import Dict, List, Optional
import json
from datetime import datetime
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class AIAnalyzer:
    """Analyze financial data using AI reasoning with LangChain LLM integration"""
    
    def __init__(self):
        # Initialize LLM
        self.llm = None
        try:
            groq_api_key = os.getenv('GROQ_API_KEY')
            if groq_api_key:
                self.llm = ChatGroq(
                    groq_api_key=groq_api_key,
                    model_name="llama-3.1-8b-instant",  # Current available model
                    temperature=0.1
                )
        except Exception as e:
            print(f"Warning: Could not initialize LLM: {e}")
        
        self.analysis_framework = {
            'revenue_growth_thresholds': {
                'excellent': 20,
                'good': 10,
                'moderate': 5,
                'poor': 0,
                'declining': -5
            },
            'news_sentiment_keywords': {
                'positive': ['beat', 'exceed', 'strong', 'growth', 'profit', 'revenue up', 'guidance raised'],
                'negative': ['miss', 'decline', 'loss', 'weak', 'guidance lowered', 'concern', 'challenge'],
                'neutral': ['meet', 'inline', 'expected', 'maintain', 'stable']
            }
        }
    
    def analyze_earnings_performance(self, earnings_data: Dict) -> Dict:
        """Analyze earnings performance and trends"""
        analysis = {
            'revenue_assessment': 'Unknown',
            'earnings_trend': 'Unknown',
            'surprise_impact': 'Neutral',
            'guidance_analysis': {},
            'key_insights': []
        }
        
        # Extract and analyze company guidance
        guidance_analysis = self.extract_company_guidance(earnings_data)
        analysis['guidance_analysis'] = guidance_analysis
        
        # Analyze revenue growth
        revenue_growth = earnings_data.get('revenue_growth', '')
        if revenue_growth and '%' in revenue_growth:
            try:
                growth_rate = float(revenue_growth.replace('%', ''))
                
                if growth_rate >= self.analysis_framework['revenue_growth_thresholds']['excellent']:
                    analysis['revenue_assessment'] = 'Excellent'
                    analysis['key_insights'].append(f"Strong revenue growth of {revenue_growth}")
                elif growth_rate >= self.analysis_framework['revenue_growth_thresholds']['good']:
                    analysis['revenue_assessment'] = 'Good'
                    analysis['key_insights'].append(f"Solid revenue growth of {revenue_growth}")
                elif growth_rate >= self.analysis_framework['revenue_growth_thresholds']['moderate']:
                    analysis['revenue_assessment'] = 'Moderate'
                    analysis['key_insights'].append(f"Moderate revenue growth of {revenue_growth}")
                elif growth_rate >= self.analysis_framework['revenue_growth_thresholds']['poor']:
                    analysis['revenue_assessment'] = 'Weak'
                    analysis['key_insights'].append(f"Weak revenue growth of {revenue_growth}")
                else:
                    analysis['revenue_assessment'] = 'Declining'
                    analysis['key_insights'].append(f"Revenue declining by {abs(growth_rate):.1f}%")
                    
            except ValueError:
                pass
        
        # Analyze earnings surprise
        surprise = earnings_data.get('earnings_surprise', '')
        if surprise and '%' in surprise:
            try:
                surprise_rate = float(surprise.replace('%', ''))
                if surprise_rate > 5:
                    analysis['surprise_impact'] = 'Positive'
                    analysis['key_insights'].append(f"Beat earnings by {surprise}")
                elif surprise_rate < -5:
                    analysis['surprise_impact'] = 'Negative'
                    analysis['key_insights'].append(f"Missed earnings by {abs(surprise_rate):.1f}%")
                else:
                    analysis['surprise_impact'] = 'Neutral'
                    analysis['key_insights'].append("Earnings roughly in line with expectations")
            except ValueError:
                pass
        
        # Add guidance insights to key insights
        if guidance_analysis.get('guidance_changes'):
            for change in guidance_analysis['guidance_changes']:
                analysis['key_insights'].append(f"Guidance {change}")
        
        return analysis
    
    def analyze_news_sentiment(self, news_articles: List[Dict]) -> Dict:
        """Analyze sentiment from recent news using LLM when available"""
        sentiment_analysis = {
            'overall_sentiment': 'Neutral',
            'sentiment_score': 0,
            'key_themes': [],
            'recent_developments': []
        }
        
        if not news_articles:
            return sentiment_analysis
        
        # Use LLM analysis if available
        if self.llm and len(news_articles) > 0:
            return self._llm_news_analysis(news_articles)
        
        # Fallback to keyword-based analysis
        return self._keyword_news_analysis(news_articles)
    
    def _llm_news_analysis(self, news_articles: List[Dict]) -> Dict:
        """Advanced news analysis using LLM"""
        # Prepare news content for LLM
        news_content = "\n".join([
            f"Title: {article.get('title', '')}\nSummary: {article.get('summary', '')}\nDate: {article.get('publish_date', '')}"
            for article in news_articles[:5]  # Limit to 5 articles for token efficiency
        ])
        
        prompt = ChatPromptTemplate.from_template(
            """Analyze the sentiment and investment implications of these recent news articles:

{news_content}

Provide analysis in JSON format:
{{
    "overall_sentiment": "Positive|Negative|Neutral",
    "sentiment_score": float between -1 and 1,
    "key_themes": ["theme1", "theme2"],
    "investment_implications": "brief analysis",
    "risk_factors": ["risk1", "risk2"]
}}

Focus on financial and business implications for investors."""
        )
        
        try:
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            result = chain.invoke({"news_content": news_content})
            
            # Convert to expected format
            return {
                'news_analysis_method': 'LLM',
                'overall_sentiment': result.get('overall_sentiment', 'Neutral'),
                'sentiment_score': result.get('sentiment_score', 0),
                'key_themes': result.get('key_themes', []),
                'recent_developments': [{
                    'type': result.get('overall_sentiment', 'Neutral'),
                    'analysis': result.get('investment_implications', ''),
                    'risk_factors': result.get('risk_factors', [])
                }]
            }
        except Exception as e:
            print(f"LLM analysis failed, using fallback: {e}")
            return self._keyword_news_analysis(news_articles)
    
    def _keyword_news_analysis(self, news_articles: List[Dict]) -> Dict:
        """Fallback keyword-based sentiment analysis"""
        sentiment_analysis = {
            'news_analysis_method': 'Keyword',
            'overall_sentiment': 'Neutral',
            'sentiment_score': 0,
            'key_themes': [],
            'recent_developments': []
        }
        
        positive_count = 0
        negative_count = 0
        total_articles = len(news_articles)
        
        for article in news_articles:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            content = f"{title} {summary}"
            
            positive_matches = sum(1 for keyword in self.analysis_framework['news_sentiment_keywords']['positive'] 
                                 if keyword in content)
            negative_matches = sum(1 for keyword in self.analysis_framework['news_sentiment_keywords']['negative'] 
                                 if keyword in content)
            
            if positive_matches > negative_matches:
                positive_count += 1
                sentiment_analysis['recent_developments'].append({
                    'type': 'Positive',
                    'headline': article.get('title', '')[:100],
                    'date': article.get('publish_date', '')
                })
            elif negative_matches > positive_matches:
                negative_count += 1
                sentiment_analysis['recent_developments'].append({
                    'type': 'Negative', 
                    'headline': article.get('title', '')[:100],
                    'date': article.get('publish_date', '')
                })
        
        if positive_count > negative_count:
            sentiment_analysis['overall_sentiment'] = 'Positive'
            sentiment_analysis['sentiment_score'] = (positive_count - negative_count) / total_articles
        elif negative_count > positive_count:
            sentiment_analysis['overall_sentiment'] = 'Negative'
            sentiment_analysis['sentiment_score'] = (negative_count - positive_count) / total_articles * -1
        
        return sentiment_analysis
    
    def generate_ai_insights(self, comprehensive_data: Dict) -> Dict:
        """Generate AI-powered insights from all available data"""
        
        earnings_analysis = self.analyze_earnings_performance(comprehensive_data.get('earnings_data', {}))
        # Add revenue data from financial metrics for LLM analysis
        financial_metrics = comprehensive_data.get('financial_metrics', {})
        earnings_analysis['annual_revenue_growth'] = financial_metrics.get('yearly_revenue_growth', 'Unknown')
        earnings_analysis['quarterly_revenue_growth'] = financial_metrics.get('quarterly_revenue_growth', 'Unknown')
        earnings_analysis['current_revenue'] = financial_metrics.get('current_revenue', 'Unknown')
        
        # Add guidance data for comprehensive analysis
        guidance_analysis = earnings_analysis.get('guidance_analysis', {})
        # if guidance_analysis['revenue_guidance'] is None:
        #     ticker = comprehensive_data.get('ticker', 'unknown')
        #     guidance_analysis = self._llm_based_guidance_retrieval(ticker) 
        earnings_analysis['guidance_summary'] = self._summarize_guidance(guidance_analysis)
        
        news_analysis = self.analyze_news_sentiment(comprehensive_data.get('recent_news', []))
        
        # Combine insights
        ai_insights = {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': comprehensive_data.get('ticker', 'Unknown'),
            'company_name': comprehensive_data.get('company_info', {}).get('company_name', 'Unknown'),
            'earnings_analysis': earnings_analysis,
            'news_sentiment': news_analysis,
            'overall_assessment': self._generate_overall_assessment(earnings_analysis, news_analysis),
            'risk_flags': self._identify_risk_flags(earnings_analysis, news_analysis),
            'recommendation_adjustments': self._suggest_adjustments(earnings_analysis, news_analysis)
        }
        
        return ai_insights
    
    def _llm_based_guidance_retrieval(self, ticker : str) -> Dict:
        prompt= ChatPromptTemplate.from_template(
            """Find the earnings call transcript for {ticker} to derive the following:

Provide analysis in JSON format:
{{
    "guidance_summary": "brief summary of company guidance",
    "management_tone": "positive|negative|neutral",
    "guidance_changes": ["change1", "change2"]
}}

Focus on company guidance and management tone for {ticker}."""
        )
        try:
            chain = prompt | self.llm
            raw_result = chain.invoke(ticker)
            return raw_result
        except Exception as e:
            print(f"LLM guidance retrieval failed: {e}")
            return {}

    def _generate_overall_assessment(self, earnings_analysis: Dict, news_analysis: Dict) -> Dict:
        """Generate overall assessment using LLM when available"""
        
        if self.llm:
            return self._llm_overall_assessment(earnings_analysis, news_analysis)
        
        return self._rule_based_assessment(earnings_analysis, news_analysis)
    
    def _llm_overall_assessment(self, earnings_analysis: Dict, news_analysis: Dict) -> Dict:
        """LLM-powered overall assessment"""
        prompt = ChatPromptTemplate.from_template(
            """Analyze the investment outlook based on:

Earnings Analysis:
- Revenue Assessment: {revenue_assessment}
- Surprise Impact: {surprise_impact}
- Key Insights: {earnings_insights}

Company Guidance:
- Guidance Summary: {guidance_summary}
- Management Tone: {management_tone}

News Sentiment:
- Overall Sentiment: {news_sentiment}
- Key Themes: {news_themes}

Financial Data:
- Annual Revenue Growth: {annual_revenue_growth}
- Quarterly Revenue Growth: {quarterly_revenue_growth}
- Current Revenue: {current_revenue}

Analyze:
1. Long-term growth trajectory (annual data)
2. Recent momentum changes (quarterly data)
3. Management guidance vs actual performance
4. Forward-looking guidance credibility
5. Any discrepancies between guidance, actual results, and trends

Provide investment assessment in JSON format:
{{
    "confidence_level": "High|Medium|Low",
    "key_factors": ["factor1", "factor2"],
    "summary": "brief investment outlook including guidance analysis",
    "recommendation_direction": "UPGRADE|DOWNGRADE|MAINTAIN",
    "guidance_credibility": "High|Medium|Low",
    "forward_outlook": "analysis of guidance and future prospects"
}}

Focus on guidance reliability and forward-looking investment insights."""
        )
        
        try:
            # First try without JSON parser to see raw response
            chain = prompt | self.llm
            raw_result = chain.invoke({
                "revenue_assessment": earnings_analysis.get('revenue_assessment', 'Unknown'),
                "surprise_impact": earnings_analysis.get('surprise_impact', 'Neutral'),
                "earnings_insights": earnings_analysis.get('key_insights', []),
                "news_sentiment": news_analysis.get('overall_sentiment', 'Neutral'),
                "news_themes": news_analysis.get('key_themes', []),
                "annual_revenue_growth": earnings_analysis.get('annual_revenue_growth', 'Unknown'),
                "quarterly_revenue_growth": earnings_analysis.get('quarterly_revenue_growth', 'Unknown'),
                "current_revenue": earnings_analysis.get('current_revenue', 'Unknown'),
                "guidance_summary": earnings_analysis.get('guidance_summary', 'No guidance available'),
                "management_tone": earnings_analysis.get('guidance_analysis', {}).get('management_tone', 'Neutral')
            })
            

            
            # Try to parse JSON from content
            try:
                import json
                content = raw_result.content
                
                # Extract JSON from markdown code blocks if present
                if '```json' in content:
                    start = content.find('```json') + 7
                    end = content.find('```', start)
                    if end != -1:
                        content = content[start:end].strip()
                
                result = json.loads(content)

            except json.JSONDecodeError as je:
                print(f"Failed to parse JSON, using text analysis")
                # Extract key info from text response
                content = raw_result.content.lower()
                confidence = 'High' if 'high confidence' in content else 'Low' if 'low confidence' in content else 'Medium'
                summary = raw_result.content[:200] + '...' if len(raw_result.content) > 200 else raw_result.content
                
                return {
                    'confidence_level': confidence,
                    'key_factors': ['LLM analysis available'],
                    'summary': summary,
                    'ai_recommendation': 'MAINTAIN',
                    'raw_response': raw_result.content
                }
            
            return {
                'confidence_level': result.get('confidence_level', 'Medium'),
                'key_factors': result.get('key_factors', []),
                'summary': result.get('summary', 'Mixed signals require analysis'),
                'ai_recommendation': result.get('recommendation_direction', 'MAINTAIN'),
                'raw_response': raw_result.content
            }
        except Exception as e:
            print(f"LLM assessment failed, using fallback: {e}")
            return self._rule_based_assessment(earnings_analysis, news_analysis)
    
    def _rule_based_assessment(self, earnings_analysis: Dict, news_analysis: Dict) -> Dict:
        """Fallback rule-based assessment"""
        assessment = {
            'confidence_level': 'Medium',
            'key_factors': [],
            'summary': ''
        }
        
        revenue_assessment = earnings_analysis.get('revenue_assessment', 'Unknown')
        surprise_impact = earnings_analysis.get('surprise_impact', 'Neutral')
        news_sentiment = news_analysis.get('overall_sentiment', 'Neutral')
        
        positive_factors = 0
        negative_factors = 0
        
        if revenue_assessment in ['Excellent', 'Good']:
            positive_factors += 2
            assessment['key_factors'].append(f"Strong financial performance ({revenue_assessment.lower()} revenue)")
        elif revenue_assessment in ['Weak', 'Declining']:
            negative_factors += 2
            assessment['key_factors'].append(f"Concerning financial performance ({revenue_assessment.lower()} revenue)")
        
        if surprise_impact == 'Positive':
            positive_factors += 1
            assessment['key_factors'].append("Positive earnings surprise")
        elif surprise_impact == 'Negative':
            negative_factors += 1
            assessment['key_factors'].append("Negative earnings surprise")
        
        if news_sentiment == 'Positive':
            positive_factors += 1
            assessment['key_factors'].append("Positive market sentiment")
        elif news_sentiment == 'Negative':
            negative_factors += 1
            assessment['key_factors'].append("Negative market sentiment")
        
        if positive_factors > negative_factors + 1:
            assessment['confidence_level'] = 'High'
            assessment['summary'] = "Multiple positive indicators support bullish outlook"
        elif negative_factors > positive_factors + 1:
            assessment['confidence_level'] = 'High'
            assessment['summary'] = "Multiple negative indicators suggest caution"
        else:
            assessment['confidence_level'] = 'Medium'
            assessment['summary'] = "Mixed signals require careful analysis"
        
        return assessment
    
    def _identify_risk_flags(self, earnings_analysis: Dict, news_analysis: Dict) -> List[str]:
        """Identify potential risk flags"""
        risk_flags = []
        
        if earnings_analysis.get('revenue_assessment') == 'Declining':
            risk_flags.append("Revenue decline trend")
        
        if earnings_analysis.get('surprise_impact') == 'Negative':
            risk_flags.append("Recent earnings miss")
        
        # Check guidance-related risks
        guidance_analysis = earnings_analysis.get('guidance_analysis', {})
        if 'lowered' in str(guidance_analysis.get('guidance_changes', [])).lower():
            risk_flags.append("Management lowered guidance")
        
        if guidance_analysis.get('management_tone') == 'Cautious':
            risk_flags.append("Cautious management outlook")
        
        if news_analysis.get('overall_sentiment') == 'Negative':
            risk_flags.append("Negative media coverage")
        
        # Check for concerning news themes
        recent_developments = news_analysis.get('recent_developments', [])
        negative_news = [dev for dev in recent_developments if dev.get('type') == 'Negative']
        if len(negative_news) >= 3:
            risk_flags.append("Multiple negative news stories")
        
        return risk_flags
    
    def _suggest_adjustments(self, earnings_analysis: Dict, news_analysis: Dict) -> Dict:
        """Suggest adjustments to quantitative analysis"""
        adjustments = {
            'dcf_adjustments': [],
            'risk_premium_changes': [],
            'growth_rate_modifications': []
        }
        
        # DCF adjustments based on earnings
        revenue_assessment = earnings_analysis.get('revenue_assessment', 'Unknown')
        if revenue_assessment == 'Declining':
            adjustments['dcf_adjustments'].append("Consider reducing growth assumptions by 20-30%")
            adjustments['growth_rate_modifications'].append("Apply conservative growth rates")
        elif revenue_assessment == 'Excellent':
            adjustments['dcf_adjustments'].append("Growth assumptions may be conservative")
        
        # Risk premium adjustments based on news
        news_sentiment = news_analysis.get('overall_sentiment', 'Neutral')
        if news_sentiment == 'Negative':
            adjustments['risk_premium_changes'].append("Consider adding 1-2% risk premium")
        elif news_sentiment == 'Positive':
            adjustments['risk_premium_changes'].append("Risk premium could be reduced by 0.5-1%")
        
        # Guidance-based adjustments
        guidance_analysis = earnings_analysis.get('guidance_analysis', {})
        if guidance_analysis.get('guidance_changes'):
            for change in guidance_analysis['guidance_changes']:
                if 'raised' in change.lower():
                    adjustments['growth_rate_modifications'].append("Consider increasing growth rates based on raised guidance")
                elif 'lowered' in change.lower():
                    adjustments['growth_rate_modifications'].append("Reduce growth assumptions due to lowered guidance")
        
        return adjustments



    def extract_company_guidance(self, earnings_data: Dict) -> Dict:
        """Extract and analyze company guidance from earnings data"""
        guidance_analysis = {
            'revenue_guidance': None,
            'earnings_guidance': None,
            'guidance_vs_actual': None,
            'guidance_changes': [],
            'management_tone': 'Neutral',
            'guidance_credibility': 'Medium'
        }
        
        # Extract guidance from earnings call or press release text
        earnings_text = earnings_data.get('earnings_call_text', '') or earnings_data.get('press_release', '')
        
        if earnings_text and self.llm:
            guidance_analysis = self._llm_guidance_extraction(earnings_text)
        else:
            guidance_analysis = self._keyword_guidance_extraction(earnings_data)
        
        return guidance_analysis

    def _llm_guidance_extraction(self, earnings_text: str) -> Dict:
        """Extract guidance using LLM analysis"""
        prompt = ChatPromptTemplate.from_template(
            """Extract company guidance information from this earnings text:

    {earnings_text}

    Provide guidance analysis in JSON format:
    {{
        "revenue_guidance": "Q4 2024 revenue expected $X-Y billion" or null,
        "earnings_guidance": "FY2024 EPS expected $X-Y" or null,
        "guidance_changes": ["raised Q4 revenue guidance", "lowered FY EPS outlook"],
        "management_tone": "Optimistic|Cautious|Neutral",
        "guidance_credibility": "High|Medium|Low",
        "forward_outlook": "brief summary of management's forward view"
    }}

    Focus on specific numerical guidance and directional changes."""
            )
            
        try:
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            result = chain.invoke({"earnings_text": earnings_text[:2000]})  # Limit text length
            
            return {
                'revenue_guidance': result.get('revenue_guidance'),
                'earnings_guidance': result.get('earnings_guidance'),
                'guidance_changes': result.get('guidance_changes', []),
                'management_tone': result.get('management_tone', 'Neutral'),
                'guidance_credibility': result.get('guidance_credibility', 'Medium'),
                'forward_outlook': result.get('forward_outlook', '')
            }
        except Exception as e:
            print(f"LLM guidance extraction failed: {e}")
            return self._keyword_guidance_extraction({'earnings_call_text': earnings_text})
    
    def _keyword_guidance_extraction(self, earnings_data: Dict) -> Dict:
        """Fallback keyword-based guidance extraction"""
        guidance_analysis = {
            'revenue_guidance': None,
            'earnings_guidance': None,
            'guidance_changes': [],
            'management_tone': 'Neutral',
            'guidance_credibility': 'Medium'
        }
        
        # Look for guidance keywords in available text
        text_sources = [
            earnings_data.get('earnings_call_text') or '',
            earnings_data.get('press_release') or '',
            str(earnings_data.get('management_comments') or '')
        ]
        
        # Filter out empty strings and join
        valid_texts = [text for text in text_sources if text and text.strip()]
        full_text = ' '.join(valid_texts).lower()
        
        # Detect guidance changes
        if any(word in full_text for word in ['raised', 'increased', 'upgraded']):
            guidance_analysis['guidance_changes'].append('raised guidance')
            guidance_analysis['management_tone'] = 'Optimistic'
        elif any(word in full_text for word in ['lowered', 'reduced', 'cut', 'downgraded']):
            guidance_analysis['guidance_changes'].append('lowered guidance')
            guidance_analysis['management_tone'] = 'Cautious'
        elif any(word in full_text for word in ['maintained', 'reaffirmed', 'confirmed']):
            guidance_analysis['guidance_changes'].append('maintained guidance')
        
        # Detect tone indicators
        if any(word in full_text for word in ['confident', 'optimistic', 'strong outlook', 'positive']):
            guidance_analysis['management_tone'] = 'Optimistic'
        elif any(word in full_text for word in ['cautious', 'uncertain', 'challenging', 'headwinds']):
            guidance_analysis['management_tone'] = 'Cautious'
        
        return guidance_analysis
    
    def _summarize_guidance(self, guidance_analysis: Dict) -> str:
        """Create a summary of guidance analysis"""
        if not guidance_analysis:
            return "No guidance information available"
        
        summary_parts = []
        
        if guidance_analysis.get('guidance_changes'):
            changes = ', '.join(guidance_analysis['guidance_changes'])
            summary_parts.append(f"Management {changes}")
        
        tone = guidance_analysis.get('management_tone', 'Neutral')
        if tone != 'Neutral':
            summary_parts.append(f"Tone: {tone}")
        
        if guidance_analysis.get('forward_outlook'):
            summary_parts.append(guidance_analysis['forward_outlook'][:100])
        
        return '; '.join(summary_parts) if summary_parts else "Limited guidance information"

# Test function
def test_ai_analyzer():
    """Test the AI analyzer with sample data"""
    from .ai_data_retriever import AIDataRetriever
    
    # Get data for a test stock
    retriever = AIDataRetriever()
    data = retriever.get_comprehensive_data("AAPL")
    
    # Analyze with AI
    analyzer = AIAnalyzer()
    insights = analyzer.generate_ai_insights(data)
    
    print(f"\n=== AI ANALYSIS FOR {insights['ticker']} ===")
    print(f"Company: {insights['company_name']}")
    print(f"Overall Assessment: {insights['overall_assessment']['summary']}")
    print(f"Confidence: {insights['overall_assessment']['confidence_level']}")
    
    print(f"\nEarnings Analysis:")
    print(f"  Revenue Assessment: {insights['earnings_analysis']['revenue_assessment']}")
    print(f"  Key Insights: {insights['earnings_analysis']['key_insights']}")
    
    print(f"\nNews Sentiment:")
    print(f"  Overall Sentiment: {insights['news_sentiment']['overall_sentiment']}")
    print(f"  Sentiment Score: {insights['news_sentiment']['sentiment_score']:.2f}")
    
    if insights['risk_flags']:
        print(f"\nRisk Flags: {', '.join(insights['risk_flags'])}")
    
    # Save results
    with open('test_ai_analysis.json', 'w') as f:
        json.dump(insights, f, indent=2, default=str)
    
    print(f"\nAI analysis saved to test_ai_analysis.json")
    return insights

if __name__ == "__main__":
    test_ai_analyzer()