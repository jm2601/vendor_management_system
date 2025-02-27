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

def normalize_company(name):
    """Normalize company names for consistent matching"""
    if not name:
        return ""
    norm = str(name).strip().upper()
    norm = re.sub(r'[,\.\-]', '', norm)
    for suffix in [" INC", " LLC", " LIMITED", " CORP", " CORPORATION", 
                  " COMPANY", " LP", " PARTNERS", " PLC"]:
        if norm.endswith(suffix):
            norm = norm[:-len(suffix)]
    return norm.strip()

# -------------------- Sage Vendors Processing --------------------
def process_raw_data(raw_df):
    formatted_data = pd.DataFrame(columns=headers)
    current_vendor = None
    current_type = None
    current_contact = None
    current_phone = None

    for index, row in raw_df.iterrows():
        row_values = row.dropna().values
        if len(row_values) > 0:
            # Extract vendor type
            vendor_type = extract_vendor_type(' '.join(map(str, row_values)))
            if vendor_type is not None:
                current_type = vendor_type
                continue
            
            # Vendor row detection
            if re.match(r'\d+', str(row_values[0])) and len(row_values) > 1:
                current_vendor = normalize_company(row_values[1])  # Normalize here
                current_contact = row_values[2] if len(row_values) > 2 else None
                current_phone = row_values[3] if len(row_values) > 3 else None
                continue
            
            # Certificate detection
            if is_certificate(row_values[0]):
                certificate = row_values[0]
                project = row_values[1] if len(row_values) > 1 else '0'
                expires = row_values[2] if len(row_values) > 2 else None
                formatted_data = pd.concat([formatted_data, pd.DataFrame({
                    'vendor_type': [current_type],
                    'vendor_name': [current_vendor],  # Already normalized
                    'certificate': [certificate],
                    'blanket_project': [project],
                    'expires': [expires],
                    'contact': [current_contact],
                    'phone': [current_phone]
                })], ignore_index=True)
    return formatted_data

def upload_vendors_page():
    st.title("Upload Sage Vendors Data")
    uploaded_file = st.file_uploader("Upload Sage CSV", type=["csv"], key="vendors_upload")
    
    if uploaded_file:
        with st.spinner("Processing Sage data..."):
            try:
                raw_df = pd.read_csv(uploaded_file, header=None)
                formatted_data = process_raw_data(raw_df)
                filtered_data = filter_no_project_certificates(formatted_data)
                processed_data = collate_certificates_and_approve(filtered_data)
                
                # Convert lists to PostgreSQL arrays
                processed_data['certificate'] = processed_data['certificate'].apply(
                    lambda x: "{" + ", ".join(map(str, x)) + "}" if x else "{}"
                )
                processed_data['certs_expired'] = processed_data['certs_expired'].apply(
                    lambda x: "{" + ", ".join(map(str, x)) + "}" if x else "{}"
                )
                processed_data['expirations_all'] = processed_data['expirations_all'].apply(
                    lambda x: "{" + ", ".join([d.strftime("%Y-%m-%d") for d in x]) + "}" if x else "{}"
                )
                processed_data['soon_to_expire'] = processed_data['soon_to_expire'].apply(
                    lambda x: None if x is None else max(min(int(x), 2147483647), -2147483648)
                )

                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Upsert logic for vendors table
                for _, row in processed_data.iterrows():
                    cursor.execute("""
                        INSERT INTO vendors 
                        (vendor_name, certificate, expires, vendor_type, contact, phone, 
                         certs_expired, approved, soon_to_expire, expirations_all)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (vendor_name) DO UPDATE SET
                            certificate = EXCLUDED.certificate,
                            expires = EXCLUDED.expires,
                            vendor_type = EXCLUDED.vendor_type,
                            contact = EXCLUDED.contact,
                            phone = EXCLUDED.phone,
                            certs_expired = EXCLUDED.certs_expired,
                            approved = EXCLUDED.approved,
                            soon_to_expire = EXCLUDED.soon_to_expire,
                            expirations_all = EXCLUDED.expirations_all
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
                st.success("✅ Sage vendors data processed successfully!")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error processing Sage file: {str(e)}")
            finally:
                if 'conn' in locals():
                    conn.close()

# -------------------- Vendor Details Processing --------------------
def upload_vendor_details_page():
    st.title("Upload Vendor Details")
    st.write("Upload file with columns: Division, Trade, Company, Contact Name, Cell, Office, Email, Address, CA Lic., DIR No., DVBE")
    
    uploaded_file = st.file_uploader("Choose file", type=["csv", "xlsx"], key="vendor_details_upload")
    if uploaded_file:
        with st.spinner("Processing details..."):
            try:
                # Read file
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Clean and normalize
                df = df.rename(columns={
                    'Company': 'company_dba',
                    'CA Lic.': 'ca_license',
                    'DIR No.': 'dir_number'
                }).dropna(how='all')
                
                df['company_dba'] = df['company_dba'].astype(str).apply(normalize_company)
                
                # Clean phone numbers
                phone_cols = ['Cell', 'Office']
                for col in phone_cols:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.replace(r'\D', '', regex=True)
                        df[col] = df[col].apply(lambda x: x if x.isdigit() and len(x) == 10 else None)
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Add before the upsert loop
                df = df.drop_duplicates(subset=['company_dba'], keep='first')

                # Upsert logic for vendor_details
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT INTO vendor_details 
                        (division, trade, company_dba, contact_name, cell_number, 
                        office_number, email, address, ca_license, dir_number, dvbe)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (company_dba) DO UPDATE SET
                            division = EXCLUDED.division,
                            trade = EXCLUDED.trade,
                            contact_name = EXCLUDED.contact_name,
                            cell_number = EXCLUDED.cell_number,
                            office_number = EXCLUDED.office_number,
                            email = EXCLUDED.email,
                            address = EXCLUDED.address,
                            ca_license = EXCLUDED.ca_license,
                            dir_number = EXCLUDED.dir_number,
                            dvbe = EXCLUDED.dvbe
                    """)
                # Add validation check
                st.write(f"Found {len(df)} unique vendor details to process")
                if len(df) == 0:
                    st.warning("No valid records found after deduplication")
                    return
                conn.commit()
                st.success("✅ Vendor details updated successfully!")
            except Exception as e:
                st.error(f"❌ Error processing details: {str(e)}")
            finally:
                if 'conn' in locals():
                    conn.close()

def upload_page():
    st.title("Data Upload Portal")
    option = st.radio("Select data type:", 
                     ("Sage Vendor Data", "Vendor Details"))
    
    if option == "Sage Vendor Data":
        upload_vendors_page()
    else:
        upload_vendor_details_page()

if __name__ == "__main__":
    upload_page()