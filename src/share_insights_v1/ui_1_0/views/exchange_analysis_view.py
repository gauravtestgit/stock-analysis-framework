import streamlit as st
import os
import glob

class ExchangeAnalysisView:
    """Exchange Analysis View for Stock Analysis UI 1.0"""
    
    def __init__(self):
        # Get absolute path to resources directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        self.resources_base = os.path.join(project_root, "resources", "stock_analyses")
    
    def render(self):
        """Render the exchange analysis view"""
        st.title("📊 Exchange Analysis Dashboard")
        
        if not os.path.exists(self.resources_base):
            st.error("Resources directory not found")
            return
        
        # Get all CSV files recursively
        csv_files = []
        for root, dirs, files in os.walk(self.resources_base):
            for file in files:
                if file.endswith('.csv'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.resources_base)
                    csv_files.append(rel_path)
        
        if not csv_files:
            st.warning("No CSV files found in the analysis directory")
            return
        
        # File selector
        selected_file = st.selectbox(
            "Select CSV File:", 
            csv_files,
            format_func=lambda x: f"📄 {x}"
        )
        
        if selected_file:
            full_path = os.path.join(self.resources_base, selected_file)
            st.write(f"**Selected File:** {selected_file}")
            st.write(f"**Full Path:** {full_path}")
            
            # File info
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                st.write(f"**File Size:** {file_size:,} bytes")
                
                # Option to preview file
                if st.button("Preview File (First 10 rows)"):
                    try:
                        import pandas as pd
                        df = pd.read_csv(full_path)
                        st.write(f"**Shape:** {df.shape[0]:,} rows × {df.shape[1]} columns")
                        st.dataframe(df.head(10))
                    except Exception as e:
                        st.error(f"Error reading file: {e}")

def main():
    """Standalone main function for testing"""
    view = ExchangeAnalysisView()
    view.render()

if __name__ == "__main__":
    main()