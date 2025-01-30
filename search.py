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
        cursor.execute("SELECT vendor_name FROM vendors")
        all_vendors = [row[0] for row in cursor.fetchall()]
        
        # Fuzzy match with threshold
        matched_vendors = process.extractBests(search_term, all_vendors, score_cutoff=60)
        
        if matched_vendors:
            selected_vendor = st.selectbox("Select vendor:", [v[0] for v in matched_vendors])
            
            # Get vendor details
            cursor.execute("""
                SELECT * FROM vendors 
                WHERE vendor_name = %s
            """, (selected_vendor,))
            vendor_data = cursor.fetchone()
            
            # Display results
            if vendor_data:
                cols = [desc[0] for desc in cursor.description]
                vendor_dict = dict(zip(cols, vendor_data))
                
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
                    current_certs = vendor_dict.get('certificate', '[]')
                    if current_certs and current_certs != '{}':
                        st.code(current_certs)
                    else:
                        st.write("[]")
                    
                    # Display expired certificates
                    st.error("Expired Certificates:")
                    expired_certs = vendor_dict.get('certs_expired', '[]')
                    if expired_certs and expired_certs != '{}':
                        st.code(expired_certs)
                    
                    # Expiration Section
                    st.subheader("Expiration")
                    expiration = vendor_dict.get('expires')
                    st.write(f"Expires: {expiration if expiration else 'No Expiration Date'}")
                    
                    # Show warning for soon to expire
                    if vendor_dict.get('soon_to_expire'):
                        st.warning(f"Certificate expires in {vendor_dict['soon_to_expire']} days")
        else:
            st.warning("No matching vendors found")
        
        conn.close()

if __name__ == "__main__":
    search_page()