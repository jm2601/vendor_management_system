import pandas as pd
import re
from datetime import datetime

# Define column headers and mappings
headers = ['vendor_type', 'vendor_name', 'certificate', 'blanket_project', 'expires', 'contact', 'phone']
vendor_type_mapping = {
    'None': 0,
    'REG VENDOR': 1,
    'SUBCONTRACTOR': 2,
    'ARCHITECT': 3,
    'Supplier': 5,
    'ACCTG/LEGAL/CONSULTING': 6,
    'EQUIPMENT RENT': 7
}

# List of allowed certificates (case-insensitive matching)
certificate_keywords = [
    'WORKERS COMP INSURANCE', 
    'GENERAL LIABILITY INSURANCE',
    'AUTO LIABILITY INSURANCE',
    'UMBRELLA LIABILITY',
    'CONTRACTORS LICENSE',
    'DIR REGISTRATION',
    'EQUIPMENT FLOATER'
]

# Certificates required for approval
approval_certificates = {
    'WORKERS COMP INSURANCE',
    'GENERAL LIABILITY INSURANCE',
    'AUTO LIABILITY INSURANCE',
    'UMBRELLA LIABILITY'
}

# Helper function to extract Vendor Type
def extract_vendor_type(value):
    for key, num in vendor_type_mapping.items():
        if key in str(value):
            return num
    return None

# Helper function to detect if a row value is a certificate
def is_certificate(value):
    return any(keyword.lower() in str(value).lower() for keyword in certificate_keywords)

# Function to filter certificates without a project
def filter_no_project_certificates(data):
    return data[(data['blanket_project'] == '0') | (data['blanket_project'].isnull())]

# Function to collate certificates, determine approval, and add expired certificates
def collate_certificates_and_approve(data):
    today = datetime.now()

    # Group by Vendor Name and aggregate certificates and expiration dates
    grouped = data.groupby('vendor_name').agg({
        'certificate': lambda x: list(x),
        'expires': lambda x: list(x),
        'vendor_type': 'first',
        'contact': 'first',
        'phone': 'first'
    }).reset_index()

    # Add columns for approval and expired certificates
    def process_certificates(row):
        certificates = row['certificate']
        expirations = row['expires']
        valid_certificates = []
        expired_certificates = []
        soonest_expiration = None

        for cert, exp in zip(certificates, expirations):
            try:
                # Handle 2-digit years by adding century
                exp_str = str(exp).strip()
                # Handle dates like "01/09/25" -> "01/09/2025"
                if len(exp_str) == 8 and exp_str.count('/') == 2:
                    day, month, year = exp_str.split('/')
                    exp_str = f"{month}/{day}/{2000 + int(year)}"  # Convert to MM/DD/YYYY
                
                expiration_date = datetime.strptime(exp_str, "%m/%d/%Y")
                if expiration_date >= today:
                    valid_certificates.append(cert)
                    if soonest_expiration is None or expiration_date < soonest_expiration:
                        soonest_expiration = expiration_date
                else:
                    expired_certificates.append(cert)
            except ValueError:
                expired_certificates.append(cert)

        row['certificate'] = valid_certificates
        row['certs_expired'] = expired_certificates
        row['expires'] = soonest_expiration.strftime("%Y-%m-%d") if soonest_expiration else None

        # Determine approval status
        certs_set = set(map(str.strip, map(str.upper, valid_certificates)))
        row['approved'] = approval_certificates.issubset(certs_set)
        return row

    # Apply processing
    grouped = grouped.apply(process_certificates, axis=1)
    
    # Add soon_to_expire column
    today = datetime.now()
    soon_to_expire = []
    for expires in grouped['expires']:
        try:
            expiration_date = datetime.strptime(str(expires).strip(), "%Y-%m-%d")
            days_until_expire = (expiration_date - today).days
            soon_to_expire.append(days_until_expire if 0 <= days_until_expire <= 30 else None)
        except:
            soon_to_expire.append(None)
    
    grouped['soon_to_expire'] = soon_to_expire
    
    return grouped