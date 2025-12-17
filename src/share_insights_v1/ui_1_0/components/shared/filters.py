import streamlit as st
import pandas as pd
from typing import List, Dict, Any

class FilterComponent:
    """Reusable filter components for the dashboard"""
    
    @staticmethod
    def exchange_selector(exchanges: List[str], key: str = "exchange_filter") -> List[str]:
        """Multi-select for exchanges"""
        return st.multiselect(
            "📊 Select Exchanges",
            exchanges,
            default=exchanges,
            key=key
        )
    
    @staticmethod
    def recommendation_filter(recommendations: List[str], key: str = "rec_filter") -> List[str]:
        """Multi-select for recommendations"""
        return st.multiselect(
            "🎯 Recommendations",
            recommendations,
            default=recommendations,
            key=key
        )
    
    @staticmethod
    def sector_filter(sectors: List[str], key: str = "sector_filter") -> List[str]:
        """Multi-select for sectors"""
        return st.multiselect(
            "🏭 Sectors",
            sectors,
            default=sectors[:10] if len(sectors) > 10 else sectors,  # Limit default selection
            key=key
        )
    
    @staticmethod
    def quality_grade_filter(grades: List[str], key: str = "quality_filter") -> List[str]:
        """Multi-select for quality grades"""
        return st.multiselect(
            "⭐ Quality Grades",
            grades,
            default=grades,
            key=key
        )
    
    @staticmethod
    def company_type_filter(types: List[str], key: str = "type_filter") -> List[str]:
        """Multi-select for company types"""
        return st.multiselect(
            "🏢 Company Types",
            types,
            default=types,
            key=key
        )
    
    @staticmethod
    def price_range_filter(min_price: float, max_price: float, key: str = "price_filter") -> tuple:
        """Price range slider"""
        return st.slider(
            "💰 Price Range ($)",
            min_value=min_price,
            max_value=max_price,
            value=(min_price, max_price),
            key=key
        )
    
    @staticmethod
    def analyst_count_filter(min_count: int, max_count: int, key: str = "analyst_filter") -> tuple:
        """Analyst count range slider"""
        return st.slider(
            "👥 Analyst Count",
            min_value=min_count,
            max_value=max_count,
            value=(min_count, max_count),
            key=key
        )

class DataFilter:
    """Class for applying filters to dataframes"""
    
    @staticmethod
    def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply multiple filters to dataframe"""
        filtered_df = df.copy()
        
        # Exchange filter
        if 'exchanges' in filters and filters['exchanges']:
            filtered_df = filtered_df[filtered_df['Exchange'].isin(filters['exchanges'])]
        
        # Recommendation filter
        if 'recommendations' in filters and filters['recommendations']:
            filtered_df = filtered_df[filtered_df['Final_Recommendation'].isin(filters['recommendations'])]
        
        # Sector filter
        if 'sectors' in filters and filters['sectors']:
            filtered_df = filtered_df[filtered_df['Sector'].isin(filters['sectors'])]
        
        # Quality grade filter
        if 'quality_grades' in filters and filters['quality_grades']:
            filtered_df = filtered_df[filtered_df['Quality_Grade'].isin(filters['quality_grades'])]
        
        # Company type filter
        if 'company_types' in filters and filters['company_types']:
            filtered_df = filtered_df[filtered_df['Company_Type'].isin(filters['company_types'])]
        
        # Price range filter
        if 'price_range' in filters:
            min_price, max_price = filters['price_range']
            filtered_df = filtered_df[
                (filtered_df['Current_Price'] >= min_price) & 
                (filtered_df['Current_Price'] <= max_price)
            ]
        
        # Analyst count filter
        if 'analyst_count' in filters:
            min_count, max_count = filters['analyst_count']
            filtered_df = filtered_df[
                (filtered_df['Analyst_Count'] >= min_count) & 
                (filtered_df['Analyst_Count'] <= max_count)
            ]
        
        return filtered_df