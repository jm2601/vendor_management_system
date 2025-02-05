import streamlit as st
import psycopg2
from fuzzywuzzy import process
from datetime import date

# Helper function to flatten a list one level
def flatten_list(nested):
    flat = []
    for item in nested:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    return flat

# Get a database connection using credentials from st.secrets
def get_db_connection():
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode="require"
    )

# Define the drop-down options for Division and Trade filtering
division_options = [
    "All",
    "01 - General Conditions",
    "02 - Existing Conditions",
    "03 - Concrete",
    "04 - Masonry",
    "05 - Metals",
    "06 - Wood, Plastics, Composites",
    "07 - Thermal & Moisture Protection",
    "08 - Openings",
    "09 - Finishes",
    "10 - Specialties",
    "11 - Equipment",
    "12 - Furnishings",
    "13 - Special Construction",
    "14 - Conveying Equipment",
    "21 - Fire Suppression",
    "22 - Plumbing",
    "23 - HVAC",
    "26 - Electrical",
    "27 - Communications / 28 - Electronic Safety & Security",
    "31 - Earthwork",
    "32 - Exterior Improvements",
    "33 - Utilities"
]

# Full list of trade options (if no division-specific mapping applies)
full_trade_list = [
    "Surveying/Staking",
    "Energy Design",
    "Temporary Site Services",
    "SWPPP",
    "Pest Control",
    "Cleaning",
    "Scaffolding",
    "Demolition",
    "Abatement",
    "Sawcutting & Drilling",
    "Concrete",
    "Gypcrete",
    "Masonry",
    "Structural Steel/Fab",
    "Metal Decking",
    "Rough Framing",
    "Finish Carpentry/Casework",
    "Insulation/Gutters",
    "Insulation",
    "Waterproofing",
    "Gutters",
    "Sheet Metal/Panels",
    "Roofing",
    "Windows/Storefront",
    "Automatic Entrance Doors",
    "Doors, Frames, Hardware",
    "Overhead/Specialty Doors",
    "Doors, Cabinets, Millwork",
    "Stucco/Plastering",
    "Drywall/Metal Stud Framing",
    "Tiling",
    "Carpet/LVP/Wood Flooring",
    "Epoxy/Sealed Flooring",
    "Acoustical Ceilings",
    "Wall Coverings",
    "Painting",
    "Signage",
    "Toilet Partitions/Accessories",
    "Fireplaces",
    "Food Service Equipment",
    "Walk In Coolers/Freezers",
    "Park Recreation Equipment",
    "Window Coverings",
    "Solid Surface Countertops",
    "Pool Construction",
    "Elevators",
    "Fire Sprinklers",
    "Plumbing",
    "HVAC",
    "Electrical",
    "Low Voltage/Security/Fire Alarm",
    "Grading/Paving",
    "Striping",
    "Fencing",
    "Landscaping",
    "Playground Surfacing",
    "Court Surfacing",
    "Underground Utilities"
]

# Mapping for Division-specific Trade options.
trade_mapping = {
    "01 - General Conditions": [
        "Surveying/Staking",
        "Energy Design",
        "Temporary Site Services",
        "SWPPP",
        "Pest Control",
        "Cleaning",
        "Scaffolding"
    ],
    "02 - Existing Conditions": [
        "Demolition",
        "Abatement",
        "Sawcutting & Drilling"
    ],
    "03 - Concrete": [
        "Concrete",
        "Gypcrete"
    ],
    "04 - Masonry": [
        "Masonry"
    ],
    "05 - Metals": [
        "Structural Steel/Fab",
        "Metal Decking"
    ],
    "06 - Wood, Plastics,  Composites": [
        "Rough Framing",
        "Finish Carpentry/Casework"
    ],
    "07 - Thermal & Moisture Protection": [
        "Insulation",
        "Insulation/Gutters",
        "Waterproofing",
        "Gutters",
        "Sheet Metal/Panels",
        "Roofing"
    ],
    "08 - Openings": [
        "Windows/Storefront",
        "Automatic Entrance Doors",
        "Doors, Frames, Hardware",
        "Overhead/Specialty Doors",
        "Doors, Cabinets, Millwork"
    ],
    "09 - Finishes": [
        "Stucco/Plastering",
        "Drywall/Metal Stud Framing",
        "Tiling",
        "Carpet/LVP/Wood Flooring",
        "Epoxy/Sealed Flooring",
        "Acoustical Ceilings",
        "Wall Coverings",
        "Painting"
    ],
    "10 - Specialties": [
        "Signage",
        "Toilet Partitions/Accessories",
        "Fireplaces"
    ],
    "11 - Equipment": [
        "Food Service Equipment",
        "Walk In Coolers/Freezers",
        "Park Recreation Equipment"
    ],
    "12 - Furnishings": [
        "Window Coverings",
        "Solid Surface Countertops"
    ],
    "13 - Special Construction": [
        "Pool Construction"
    ],
    "14 - Conveying Equipment": [
        "Elevators"
    ],
    "21 - Fire Suppression": [
        "Fire Sprinklers"
    ],
    "22 - Plumbing": [
        "Plumbing"
    ],
    "23 - HVAC": [
        "HVAC"
    ],
    "26 - Electrical": [
        "Electrical"
    ],
    "27 - Communications / 28 - Electronic Safety & Security": [
        "Low Voltage/Security/Fire Alarm"
    ],
    "31 - Earthwork": [
        "Grading/Paving"
    ],
    "32 - Exterior Improvements": [
        "Striping",
        "Fencing",
        "Landscaping",
        "Playground Surfacing",
        "Court Surfacing"
    ],
    "33 - Utilities": [
        "Underground Utilities"
    ]
}

def search_page():
    st.title("Vendor Search")
    
    # --- Sidebar Filters ---
    st.sidebar.header("Filter Vendor Details")
    
    # Division filter drop-down with fixed options
    division_filter = st.sidebar.selectbox("Division", options=division_options, index=0)
    
    # Auto-adjust Trade filter based on Division selection:
    if division_filter in trade_mapping:
        trade_options = ["All"] + trade_mapping[division_filter]
    else:
        trade_options = ["All"] + full_trade_list
    
    trade_filter = st.sidebar.selectbox("Trade", options=trade_options, index=0)
    
    # Text input for company (DBA) filter
    company_filter = st.sidebar.text_input("Company (DBA)")
    
    # Checkboxes for DIR and CA License filters:
    filter_dir = st.sidebar.checkbox("Only show vendors with DIR number")
    filter_ca = st.sidebar.checkbox("Only show vendors with CA license")
    
    # --- Main Search Input ---
    # Fuzzy match on vendor legal name (from the vendors table)
    search_term = st.text_input("Search Vendor Name", placeholder="Start typing vendor name...")
    
    if search_term:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Retrieve vendor names from vendors table for fuzzy matching
        cursor.execute("SELECT DISTINCT vendor_name FROM vendors")
        all_vendors = [row[0] for row in cursor.fetchall()]
        matched_vendors = process.extractBests(search_term, all_vendors, score_cutoff=60)
        
        if matched_vendors:
            selected_vendor = st.selectbox("Select vendor:", [v[0] for v in matched_vendors])
            
            # Build a query that joins vendors with vendor_details.
            # The join condition assumes that vendors.vendor_name matches vendor_details.company_dba.
            query = """
                SELECT v.vendor_name, 
                       v.certificate, 
                       v.expirations_all,
                       v.approved, 
                       v.contact, 
                       v.phone, 
                       v.soon_to_expire,
                       v.certs_expired,
                       d.division,
                       d.trade,
                       d.company_dba,
                       d.contact_name,
                       d.cell_number,
                       d.office_number,
                       d.email,
                       d.address,
                       d.ca_license,
                       d.dir_number
                FROM vendors v
                LEFT JOIN vendor_details d ON v.vendor_name = d.company_dba
                WHERE v.vendor_name = %s
            """
            params = [selected_vendor]
            # Apply additional filters from the sidebar:
            if division_filter != "All":
                query += " AND d.division = %s"
                params.append(division_filter)
            if trade_filter != "All":
                query += " AND d.trade ILIKE %s"
                params.append("%" + trade_filter + "%")
            if company_filter:
                query += " AND d.company_dba ILIKE %s"
                params.append("%" + company_filter + "%")
            if filter_dir:
                query += " AND d.dir_number IS NOT NULL AND d.dir_number <> ''"
            if filter_ca:
                query += " AND d.ca_license IS NOT NULL AND d.ca_license <> ''"
            
            cursor.execute(query, tuple(params))
            vendor_data = cursor.fetchone()
            
            if vendor_data:
                # Map query results to a dictionary using column names
                cols = [desc[0] for desc in cursor.description]
                vendor_dict = dict(zip(cols, vendor_data))
                
                # --- Process Certificate Data ---
                # Flatten the certificate and expirations arrays
                flat_certificates = flatten_list(vendor_dict.get("certificate", []))
                flat_expirations = flatten_list(vendor_dict.get("expirations_all", []))
                # Create pairs of (certificate, expiration)
                cert_exp_pairs = list(zip(flat_certificates, flat_expirations))
                if cert_exp_pairs:
                    # Sort the pairs by expiration date
                    cert_exp_pairs.sort(key=lambda x: x[1])
                    soonest_date = cert_exp_pairs[0][1]
                    # Only include certificates that expire on the soonest date
                    soonest_certs = [cert for cert, exp in cert_exp_pairs if exp == soonest_date]
                else:
                    soonest_date, soonest_certs = None, []
                days_left = (soonest_date - date.today()).days if soonest_date else None
                
                # Flatten expired certificates array
                flat_expired = flatten_list(vendor_dict.get("certs_expired", []))
                
                # --- Display the Vendor Details ---
                with st.expander(f"{vendor_dict['vendor_name']}", expanded=True):
                    # Display approval status
                    if vendor_dict['approved']:
                        st.success("Vendor is Approved ✅")
                    else:
                        st.error("Vendor is Not Approved ❌")
                    
                    # Display contact details (including email from vendor_details)
                    st.subheader("Contact Details")
                    st.write(f"Contact: {vendor_dict.get('contact', 'N/A')}")
                    st.write(f"Phone: {vendor_dict.get('phone', 'N/A')}")
                    st.write(f"E-mail: {vendor_dict.get('email', 'N/A')}")
                    
                    # Display current certificates
                    st.subheader("Certificates")
                    st.write("Current Certificates:")
                    if flat_certificates:
                        st.code(flat_certificates)
                    else:
                        st.write("No valid certificates.")
                    
                    # Display expired certificates
                    st.write("Expired Certificates:")
                    if flat_expired:
                        st.code(flat_expired)
                    else:
                        st.write("No expired certificates.")
                    
                    # Display expiration details (only the certificate(s) expiring on the soonest date)
                    st.subheader("Expiration")
                    if soonest_date:
                        st.write(f"**Earliest Expiring Certificate(s) on {soonest_date}:**")
                        st.write(soonest_certs)
                        if days_left is not None and 0 <= days_left <= 30:
                            st.write(f"Certificate expires in {days_left} days")
                    else:
                        st.write("No certificates nearing expiration.")
            else:
                st.warning("No vendor data found for the selected vendor.")
        else:
            st.warning("No matching vendors found")
        
        conn.close()

if __name__ == "__main__":
    search_page()
