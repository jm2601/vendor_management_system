# view_data.py (updated)
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

def view_data_page():
    st.title("View Vendor Data")
    
    # Create SQLAlchemy engine
    engine = create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
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