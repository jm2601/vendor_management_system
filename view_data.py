import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

def view_data_page():
    st.title("View Vendor Data")
    
    # Create SQLAlchemy engine using st.secrets
    engine = create_engine(
        f"postgresql://{st.secrets['DB_USER']}:{st.secrets['DB_PASSWORD']}@"
        f"{st.secrets['DB_HOST']}:{st.secrets['DB_PORT']}/{st.secrets['DB_NAME']}"
        "?sslmode=require"
    )
    
    try:
        with engine.connect() as conn:
            # Query vendors table
            df_vendors = pd.read_sql("SELECT * FROM vendors", conn)
            # Query vendor_details table
            df_details = pd.read_sql("SELECT * FROM vendor_details", conn)
            
        st.subheader("Vendors Table")
        if not df_vendors.empty:
            st.dataframe(df_vendors, use_container_width=True)
        else:
            st.warning("No data found in vendors table! Please upload vendors data.")
        
        st.subheader("Vendor Details Table")
        if not df_details.empty:
            st.dataframe(df_details, use_container_width=True)
        else:
            st.warning("No data found in vendor_details table! Please upload vendor details data.")
            
    except Exception as e:
        st.error(f"Error accessing database: {str(e)}")

if __name__ == "__main__":
    view_data_page()
