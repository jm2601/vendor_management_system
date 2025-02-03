import pandas as pd
import re
from datetime import datetime

# Example headers and mappings – adjust as needed
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

certificate_keywords = [
    'WORKERS COMP INSURANCE', 
    'GENERAL LIABILITY INSURANCE',
    'AUTO LIABILITY INSURANCE',
    'UMBRELLA LIABILITY',
    'CONTRACTORS LICENSE'
]

# Certificates required for approval (example set)
approval_certificates = {
    'WORKERS COMP INSURANCE',
    'GENERAL LIABILITY INSURANCE',
    'AUTO LIABILITY INSURANCE',
    'UMBRELLA LIABILITY'
}

def extract_vendor_type(value):
    for key, num in vendor_type_mapping.items():
        if key in str(value):
            return num
    return None

def is_certificate(value):
    return any(keyword.lower() in str(value).lower() for keyword in certificate_keywords)

def filter_no_project_certificates(data):
    return data[(data['blanket_project'] == '0') | (data['blanket_project'].isnull())]

def collate_certificates_and_approve(data):
    today = datetime.now()
    # Group by vendor_name and aggregate values
    grouped = data.groupby('vendor_name').agg({
        'certificate': lambda x: list(x),
        'expires': lambda x: list(x),
        'vendor_type': 'first',
        'contact': 'first',
        'phone': 'first'
    }).reset_index()

    def process_certificates(row):
        certificates = row['certificate']
        expirations = row['expires']
        valid_certificates = []
        valid_expirations = []  # NEW: store each certificate's expiration date
        expired_certificates = []
        soonest_expiration = None

        for cert, exp in zip(certificates, expirations):
            try:
                exp_str = str(exp).strip()
                # Convert dates like "01/09/25" to "MM/DD/YYYY"
                if len(exp_str) == 8 and exp_str.count('/') == 2:
                    day, month, year = exp_str.split('/')
                    exp_str = f"{month}/{day}/{2000 + int(year)}"
                expiration_date = datetime.strptime(exp_str, "%m/%d/%Y")
                if expiration_date >= today:
                    valid_certificates.append(cert)
                    valid_expirations.append(expiration_date)
                    if soonest_expiration is None or expiration_date < soonest_expiration:
                        soonest_expiration = expiration_date
                else:
                    expired_certificates.append(cert)
            except ValueError:
                expired_certificates.append(cert)
        row['certificate'] = valid_certificates
        row['expirations_all'] = valid_expirations  # NEW column with full pairing
        row['certs_expired'] = expired_certificates
        row['expires'] = soonest_expiration.strftime("%Y-%m-%d") if soonest_expiration else None

        # Determine approval status using the required set
        certs_set = set(map(str.strip, map(str.upper, valid_certificates)))
        row['approved'] = approval_certificates.issubset(certs_set)
        return row

    grouped = grouped.apply(process_certificates, axis=1)

    # Add soon_to_expire column (if certificate expires within 30 days)
    soon_to_expire = []
    for expires in grouped['expires']:
        try:
            expiration_date = datetime.strptime(str(expires).strip(), "%Y-%m-%d")
            days_until_expire = (expiration_date - today).days
            soon_to_expire.append(days_until_expire if 0 <= days_until_expire <= 30 else None)
        except Exception:
            soon_to_expire.append(None)
    grouped['soon_to_expire'] = soon_to_expire

    return grouped
