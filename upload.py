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

# Process raw CSV data for vendors (as before)
def process_raw_data(raw_df):
    formatted_data = pd.DataFrame(columns=headers)
    current_vendor = None
    current_type = None
    current_contact = None
    current_phone = None

    for index, row in raw_df.iterrows():
        row_values = row.dropna().values
        if len(row_values) > 0:
            # Detect vendor type
            vendor_type = extract_vendor_type(' '.join(map(str, row_values)))
            if vendor_type is not None:
                current_type = vendor_type
                continue
            # Detect vendor name and contact info
            if re.match(r'\d+', str(row_values[0])) and len(row_values) > 1:
                current_vendor = row_values[1]
                current_contact = row_values[2] if len(row_values) > 2 else None
                current_phone = row_values[3] if len(row_values) > 3 else None
                continue
            # Detect certificate rows
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

# Upload vendors data section
def upload_vendors_page():
    st.title("Upload Vendors Data")
    uploaded_file = st.file_uploader("Upload vendors CSV", type=["csv"], key="vendors_upload")
    if uploaded_file:
        with st.spinner("Processing vendors data..."):
            try:
                raw_df = pd.read_csv(uploaded_file, header=None)
                formatted_data = process_raw_data(raw_df)
                filtered_data = filter_no_project_certificates(formatted_data)
                processed_data = collate_certificates_and_approve(filtered_data)
                processed_data = processed_data.drop(columns=['blanket_project'], errors='ignore')
                # Convert arrays to PostgreSQL array literal strings
                processed_data['certificate'] = processed_data['certificate'].apply(
                    lambda x: "{" + ", ".join(map(str, x)) + "}" if len(x) > 0 else "{}"
                )
                processed_data['certs_expired'] = processed_data['certs_expired'].apply(
                    lambda x: "{" + ", ".join(map(str, x)) + "}" if len(x) > 0 else "{}"
                )
                processed_data['expirations_all'] = processed_data['expirations_all'].apply(
                    lambda x: "{" + ", ".join([d.strftime("%Y-%m-%d") for d in x]) + "}" if len(x) > 0 else "{}"
                )
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("TRUNCATE TABLE vendors")
                processed_data['soon_to_expire'] = (
                    processed_data['soon_to_expire']
                    .astype(float)
                    .replace({np.nan: None})
                    .astype(object)
                    .clip(lower=-2147483648, upper=2147483647)
                )
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
                st.success("✅ Vendors data uploaded successfully!")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error processing vendors file: {str(e)}")
            finally:
                if 'conn' in locals():
                    conn.close()

# Upload vendor details data section
def upload_vendor_details_page():
    st.title("Upload Vendor Details Data")
    st.write("Upload an Excel or CSV file with the following columns:")
    st.write("Division, Trade, Company, Contact Name, Cell Number, Office Number, E-mail, Address, CA Lic., DIR No.")
    uploaded_file = st.file_uploader("Upload Vendor Details", type=["csv", "xlsx"], key="vendor_details_upload")
    if uploaded_file:
        with st.spinner("Processing vendor details data..."):
            try:
                # Use skiprows=2 to skip the top two rows of the file
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, skiprows=2)
                else:
                    df = pd.read_excel(uploaded_file, skiprows=2)
                # Rename columns to lower-case names matching the vendor_details table
                df = df.rename(columns={
                    'Division': 'division',
                    'Trade': 'trade',
                    'Company': 'company_dba',
                    'Contact Name': 'contact_name',
                    'Cell Number': 'cell_number',
                    'Office Number': 'office_number',
                    'E-mail': 'email',
                    'Address': 'address',
                    'CA Lic.': 'ca_license',
                    'DIR No.': 'dir_number'
                })
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("TRUNCATE TABLE vendor_details")
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT INTO vendor_details 
                        (division, trade, company_dba, contact_name, cell_number, office_number, email, address, ca_license, dir_number)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        row.get('division'),
                        row.get('trade'),
                        row.get('company_dba'),
                        row.get('contact_name'),
                        row.get('cell_number'),
                        row.get('office_number'),
                        row.get('email'),
                        row.get('address'),
                        row.get('ca_license'),
                        row.get('dir_number')
                    ))
                conn.commit()
                st.success("✅ Vendor details uploaded successfully!")
            except Exception as e:
                st.error(f"❌ Error processing vendor details file: {str(e)}")
            finally:
                if 'conn' in locals():
                    conn.close()

# Main upload page that lets the user choose which data to upload
def upload_page():
    st.title("Upload Data")
    st.write("Choose an option below:")
    option = st.radio("Select upload type", ("Vendors Data", "Vendor Details Data"))
    if option == "Vendors Data":
        upload_vendors_page()
    else:
        upload_vendor_details_page()

if __name__ == "__main__":
    upload_page()
