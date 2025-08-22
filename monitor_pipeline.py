import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session

def load_pdf_reviews_flatten_data():
    """
    Load data from PDF_REVIEWS_FLATTEN table.
    Returns a pandas DataFrame.
    """
    try:
        session = get_active_session()
        
        # Query the PDF_REVIEWS_FLATTEN table
        query = """
        SELECT 
            FILE_NAME as FILE_PROCESSED,
            inspector_value as INSPECTOR_NAME,
            inspection_date_value as INSPECTOR_DATE,
            inspection_grade_value as INSPECTION_GRADE,
            list_of_units
        FROM PDF_REVIEWS_FLATTEN
        ORDER BY FILE_NAME DESC
        """
        
        # Execute query and convert to pandas DataFrame
        result = session.sql(query)
        df = result.to_pandas()
        
        return df
        
    except Exception as e:
        st.error(f"⚠️ Database error: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

def truncate_text(text, max_length=30):
    """Truncate text with ellipsis for compact display."""
    if pd.isna(text):
        return "N/A"
    text_str = str(text)
    return text_str[:max_length] + "..." if len(text_str) > max_length else text_str

def main():
    # Compact header with icon
    st.title("📊 PDF Inspection Dashboard")
    
    # Load data from PDF_REVIEWS_FLATTEN
    df = load_pdf_reviews_flatten_data()
    
    if df.empty:
        st.error("❌ No data available from PDF_REVIEWS_FLATTEN table")
        st.info("**Troubleshooting:** Check table existence and permissions")
        return
    
    # Success indicator
    st.success(f"✅ Loaded {len(df)} inspection records")
    
    # Compact inspection records table
    st.subheader("🔍 Inspection Records")
    
    if not df.empty:
        # Prepare display dataframe with truncated text
        display_df = df.copy()
        
        # Truncate long text fields for compact display
        for col in ['FILE_PROCESSED', 'inspector_name', 'list_of_units']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: truncate_text(x, 25))
        
        # Format inspection_date for compact display
        if 'inspection_date' in display_df.columns:
            try:
                display_df['inspection_date'] = pd.to_datetime(display_df['inspection_date']).dt.strftime('%m/%d/%y')
            except:
                pass
        
        # Rename columns for compact headers
        column_mapping = {
            'FILE_PROCESSED': '📄 File',
            'inspector_name': '👤 Inspector',
            'inspection_date': '📅 Date',
            'inspection_grade': '⭐ Grade',
            'list_of_units': '🔧 Units'
        }
        
        # Apply column renaming only for columns that exist
        display_df = display_df.rename(columns={k: v for k, v in column_mapping.items() if k in display_df.columns})
        
        # Display the compact table
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
       
        
        # Tooltip info
        st.info("Tooltip Info: Hover over truncated cells in the table above to see full content")
        
    # Footer with last updated info
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M on %m/%d/%y")
    st.markdown(f"🔄 Last updated: {current_time} | Dashboard optimized for 10-inch screens")

if __name__ == "__main__":
    main()
