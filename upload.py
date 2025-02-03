import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import re
from datetime import datetime
from approved_vendors import (
    extract_vendor_type,
    is_certificate,
    filter_no_project_certificates,
    collate_certificates_and_approve,
    headers
)

def get_db_connection():
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode="require"
    )

def process_raw_data(raw_df):
    """Process the raw CSV data into a formatted DataFrame."""
    formatted_data = pd.DataFrame(columns=headers)
    current_vendor = None
    current_type = None
    current_contact = None
    current_phone = None

    for index, row in raw_df.iterrows():
        row_values = row.dropna().values
        if len(row_values) > 0:
            # Detect Vendor Type
            vendor_type = extract_vendor_type(' '.join(map(str, row_values)))
            if vendor_type is not None:
                current_type = vendor_type
                continue

            # Detect Vendor Name and related information
            if re.match(r'\d+', str(row_values[0])) and len(row_values) > 1:
                current_vendor = row_values[1]
                current_contact = row_values[2] if len(row_values) > 2 else None
                current_phone = row_values[3] if len(row_values) > 3 else None
                continue

            # Detect Certificate and associated expiration
            if is_certificate(row_values[0]):
                certificate = row_values[0]
                project = row_values[1] if len(row_values) > 1 else '0'
                expires = row_values[2] if len(row_values) > 2 else None

                formatted_data = pd.concat([formatted_data, pd.DataFrame({
                    'vendor_type': [current_type],
                    'vendor_name': [current_vendor],
                    'certificate': [certificate],
                    'blanket_project': [project],
                    'expires': [expires],
                    'contact': [current_contact],
                    'phone': [current_phone]
                })], ignore_index=True)
    return formatted_data

def upload_page():
    st.title("CSV Upload & Processing")
    
    uploaded_file = st.file_uploader("Upload vendor CSV", type=["csv"])
    
    if uploaded_file:
        with st.spinner("Processing..."):
            try:
                # Step 1: Read raw data
                raw_df = pd.read_csv(uploaded_file, header=None)
                
                # Step 2: Process raw data
                formatted_data = process_raw_data(raw_df)
                
                # Step 3: Filter rows (if necessary)
                filtered_data = filter_no_project_certificates(formatted_data)
                
                # Step 4: Collate certificates, compute approval, and now build expirations_all
                processed_data = collate_certificates_and_approve(filtered_data)
                
                # Remove unneeded columns if desired
                processed_data = processed_data.drop(columns=['blanket_project'], errors='ignore')
                
                # Convert certificate arrays to PostgreSQL array literal strings
                processed_data['certificate'] = processed_data['certificate'].apply(
                    lambda x: "{" + ", ".join(map(str, x)) + "}" if len(x) > 0 else "{}"
                )
                processed_data['certs_expired'] = processed_data['certs_expired'].apply(
                    lambda x: "{" + ", ".join(map(str, x)) + "}" if len(x) > 0 else "{}"
                )
                processed_data['expirations_all'] = processed_data['expirations_all'].apply(
                    lambda x: "{" + ", ".join([d.strftime("%Y-%m-%d") for d in x]) + "}" if len(x) > 0 else "{}"
                )
                
                # Upload to PostgreSQL
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Clear existing data
                cursor.execute("TRUNCATE TABLE vendors")
                
                # Ensure soon_to_expire is numeric and handle NaN
                processed_data['soon_to_expire'] = (
                    processed_data['soon_to_expire']
                    .astype(float)
                    .replace({np.nan: None})
                    .astype(object)
                    .clip(lower=-2147483648, upper=2147483647)
                )
                
                # Insert new data (note the new column added at the end)
                for _, row in processed_data.iterrows():
                    cursor.execute("""
                        INSERT INTO vendors 
                        (vendor_name, certificate, expires, vendor_type, contact, phone, certs_expired, approved, soon_to_expire, expirations_all)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        row['vendor_name'],
                        row['certificate'],
                        row['expires'],
                        row['vendor_type'],
                        row['contact'],
                        row['phone'],
                        row['certs_expired'],
                        row['approved'],
                        row['soon_to_expire'],
                        row['expirations_all']
                    ))
                
                conn.commit()
                st.success("✅ Data uploaded successfully!")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                st.write("**Debug Info:**")
                st.write(f"Processed Data Columns: {list(processed_data.columns)}")
                st.write(f"Sample Data: {processed_data.head(3).to_dict()}")
                raise e
            finally:
                if 'conn' in locals():
                    conn.close()

if __name__ == "__main__":
    upload_page()
