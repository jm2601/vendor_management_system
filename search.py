import streamlit as st
import psycopg2
from fuzzywuzzy import process

def get_db_connection():
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode="require"
    )

def search_page():
    st.title("Vendor Search")
    
    # Search input
    search_term = st.text_input("Search Vendor Name", placeholder="Start typing vendor name...")
    
    if search_term:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all vendor names for fuzzy matching
        cursor.execute("SELECT DISTINCT vendor_name FROM vendors")
        all_vendors = [row[0] for row in cursor.fetchall()]
        
        # Fuzzy match with threshold
        matched_vendors = process.extractBests(search_term, all_vendors, score_cutoff=60)
        
        if matched_vendors:
            selected_vendor = st.selectbox("Select vendor:", [v[0] for v in matched_vendors])
            
            # Get vendor details
            cursor.execute("""
                SELECT vendor_name, array_agg(certificate) AS certificates, 
                       array_agg(expires ORDER BY expires ASC) AS expirations, 
                       approved, contact, phone, soon_to_expire
                FROM vendors 
                WHERE vendor_name = %s
                GROUP BY vendor_name, approved, contact, phone, soon_to_expire
            """, (selected_vendor,))
            vendor_data = cursor.fetchone()
            
            # Display results
            if vendor_data:
                cols = [desc[0] for desc in cursor.description]
                vendor_dict = dict(zip(cols, vendor_data))
                
                # Extract soonest expiring certificate
                certificates = vendor_dict.get('certificates', [])
                expiration_dates = vendor_dict.get('expirations', [])
                
                if certificates and expiration_dates:
                    # Flatten any nested lists
                    certificates = [item for sublist in certificates for item in (sublist if isinstance(sublist, list) else [sublist])]
                    expiration_dates = [item for sublist in expiration_dates for item in (sublist if isinstance(sublist, list) else [sublist])]
                    
                    cert_expirations = list(zip(certificates, expiration_dates))
                    cert_expirations = [(cert, exp) for cert, exp in cert_expirations if exp is not None]
                    cert_expirations.sort(key=lambda x: x[1])  # Sort by expiration date
                    
                    if cert_expirations:
                        soonest_date = cert_expirations[0][1]
                        soonest_certs = [cert for cert, exp in cert_expirations if exp == soonest_date]
                    else:
                        soonest_date, soonest_certs = None, []
                else:
                    soonest_date, soonest_certs = None, []
                
                # Main expandable section for the vendor
                with st.expander(f"{vendor_dict['vendor_name']}", expanded=True):
                    # Approval Status
                    if vendor_dict['approved']:
                        st.success("Vendor is Approved ✅")
                    else:
                        st.error("Vendor is Not Approved ❌")
                    
                    # Contact Details Section
                    st.subheader("Contact Details")
                    st.write(f"Contact: {vendor_dict.get('contact', 'N/A')}")
                    st.write(f"Phone: {vendor_dict.get('phone', 'N/A')}")
                    
                    # Certificates Section
                    st.subheader("Certificates")
                    st.write("Current Certificates:")
                    
                    # Display current certificates
                    if certificates:
                        st.code(certificates)
                    else:
                        st.write("No valid certificates.")
                    
                    # Expiration Section
                    st.subheader("Expiration")
                    if soonest_date:
                        st.write(f"**Earliest Expiring Certificate(s) on {soonest_date}:**")
                        st.write("\n".join(map(str, soonest_certs)))
                    else:
                        st.write("No certificates nearing expiration.")
        else:
            st.warning("No matching vendors found")
        
        conn.close()

if __name__ == "__main__":
    search_page()
