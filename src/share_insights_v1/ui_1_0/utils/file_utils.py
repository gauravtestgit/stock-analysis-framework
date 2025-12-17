import pandas as pd
import glob
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class AnalysisFileLoader:
    """Utility class for loading analysis files from different exchanges"""
    
    def __init__(self, resources_path: str = None):
        self.resources_path = resources_path
    
    def set_resources_path(self, path: str):
        """Set the resources path"""
        self.resources_path = path
    
    def get_available_exchanges(self) -> List[str]:
        """Get list of available exchanges with analysis files"""
        if not self.resources_path:
            return []
        
        exchanges = []
        pattern = f"{self.resources_path}*_*_analysis.csv"
        files = glob.glob(pattern)
        
        for file in files:
            filename = os.path.basename(file)
            exchange = filename.split('_')[0].upper()
            if exchange not in exchanges:
                exchanges.append(exchange)
        
        return sorted(exchanges)
    
    def get_latest_analysis_file(self, exchange: str) -> Optional[str]:
        """Get the latest analysis file for a specific exchange"""
        pattern = f"{self.resources_path}{exchange.lower()}_*_analysis.csv"
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        # Sort by modification time, get latest
        latest_file = max(files, key=os.path.getctime)
        return latest_file
    
    def load_exchange_data(self, exchange: str) -> Optional[pd.DataFrame]:
        """Load analysis data for a specific exchange"""
        file_path = self.get_latest_analysis_file(exchange)
        
        if not file_path:
            return None
        
        try:
            df = pd.read_csv(file_path)
            
            # Add exchange column
            df['Exchange'] = exchange.upper()
            
            # Clean and standardize columns
            df = self._clean_dataframe(df)
            
            return df
        except Exception as e:
            print(f"Error loading {exchange} data: {e}")
            return None
    
    def load_all_exchanges(self) -> Dict[str, pd.DataFrame]:
        """Load data for all available exchanges"""
        exchanges = self.get_available_exchanges()
        data = {}
        
        for exchange in exchanges:
            df = self.load_exchange_data(exchange)
            if df is not None:
                data[exchange] = df
        
        return data
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize the dataframe"""
        # Convert price columns to numeric
        price_columns = ['Current_Price', 'DCF_Price', 'Technical_Price', 
                        'Comparable_Price', 'Startup_Price', 'Analyst_Price']
        
        for col in price_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', ''), errors='coerce')
        
        # Convert Analyst_Count to numeric
        if 'Analyst_Count' in df.columns:
            df['Analyst_Count'] = pd.to_numeric(df['Analyst_Count'], errors='coerce')
        
        # Fill NaN values
        df = df.fillna('')
        
        return df
    
    def get_file_info(self, exchange: str) -> Optional[Dict]:
        """Get information about the analysis file"""
        file_path = self.get_latest_analysis_file(exchange)
        
        if not file_path:
            return None
        
        filename = os.path.basename(file_path)
        parts = filename.replace('.csv', '').split('_')
        
        if len(parts) >= 3:
            date_str = parts[1]
            time_str = parts[2]
            
            try:
                file_date = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except:
                file_date = datetime.fromtimestamp(os.path.getctime(file_path))
        else:
            file_date = datetime.fromtimestamp(os.path.getctime(file_path))
        
        return {
            'filename': filename,
            'date': file_date,
            'path': file_path,
            'size': os.path.getsize(file_path)
        }