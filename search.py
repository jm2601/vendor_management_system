import streamlit as st
import psycopg2
from fuzzywuzzy import process
from datetime import date

def flatten_list(nested):
    """Flattens a list by one level."""
    flat = []
    for item in nested:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    return flat

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
    
    search_term = st.text_input("Search Vendor Name", placeholder="Start typing vendor name...")
    
    if search_term:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all vendor names for fuzzy matching
        cursor.execute("SELECT DISTINCT vendor_name FROM vendors")
        all_vendors = [row[0] for row in cursor.fetchall()]
        
        matched_vendors = process.extractBests(search_term, all_vendors, score_cutoff=60)
        
        if matched_vendors:
            selected_vendor = st.selectbox("Select vendor:", [v[0] for v in matched_vendors])
            
            cursor.execute("""
                SELECT vendor_name, 
                       certificate, 
                       expirations_all,
                       approved, contact, phone, soon_to_expire,
                       certs_expired
                FROM vendors 
                WHERE vendor_name = %s
            """, (selected_vendor,))
            vendor_data = cursor.fetchone()
            
            if vendor_data:
                cols = [desc[0] for desc in cursor.description]
                vendor_dict = dict(zip(cols, vendor_data))
                
                # Flatten the certificate and expiration arrays
                flat_certificates = flatten_list(vendor_dict.get("certificate", []))
                flat_expirations = flatten_list(vendor_dict.get("expirations_all", []))
                
                # Pair each certificate with its corresponding expiration date
                cert_exp_pairs = list(zip(flat_certificates, flat_expirations))
                if cert_exp_pairs:
                    cert_exp_pairs.sort(key=lambda x: x[1])
                    soonest_date = cert_exp_pairs[0][1]
                    # Only include those certificates whose expiration equals the soonest date
                    soonest_certs = [cert for cert, exp in cert_exp_pairs if exp == soonest_date]
                else:
                    soonest_date, soonest_certs = None, []
                
                days_left = (soonest_date - date.today()).days if soonest_date else None
                
                # Flatten expired certificates
                flat_expired = flatten_list(vendor_dict.get("certs_expired", []))
                
                with st.expander(f"{vendor_dict['vendor_name']}", expanded=True):
                    if vendor_dict['approved']:
                        st.success("Vendor is Approved ✅")
                    else:
                        st.error("Vendor is Not Approved ❌")
                    
                    st.subheader("Contact Details")
                    st.write(f"Contact: {vendor_dict.get('contact', 'N/A')}")
                    st.write(f"Phone: {vendor_dict.get('phone', 'N/A')}")
                    
                    st.subheader("Certificates")
                    st.write("Current Certificates:")
                    if flat_certificates:
                        st.code(flat_certificates)
                    else:
                        st.write("No valid certificates.")
                    
                    st.write("Expired Certificates:")
                    if flat_expired:
                        st.code(flat_expired)
                    else:
                        st.write("No expired certificates.")
                    
                    st.subheader("Expiration")
                    if soonest_date:
                        st.write(f"**Earliest Expiring Certificate(s) on {soonest_date}:**")
                        st.write(soonest_certs)
                        if days_left is not None and 0 <= days_left <= 30:
                            st.write(f"Certificate expires in {days_left} days")
                    else:
                        st.write("No certificates nearing expiration.")
        else:
            st.warning("No matching vendors found")
        
        conn.close()

if __name__ == "__main__":
    search_page()
