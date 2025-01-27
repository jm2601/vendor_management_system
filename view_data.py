# view_data.py (updated)
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

def view_data_page():
    st.title("View Vendor Data")
    
    # Create SQLAlchemy engine
    engine = create_engine(
        f"postgresql://{st.secrets['DB_USER']}:{st.secrets['DB_PASSWORD']}@"
        f"{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}"
        "?sslmode=require"
    )
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql("SELECT * FROM vendors", conn)
            
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No data found! Please upload data through the Upload page.")
            
    except Exception as e:
        st.error(f"Error accessing database: {str(e)}")