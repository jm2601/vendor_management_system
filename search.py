import streamlit as st
import psycopg2
from datetime import date
import re

# --- Helper Functions ---
def get_db_connection():
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode="require"
    )

# ADD THIS NEW FUNCTION
def create_normalize_function(conn):
    """Create the normalize_company SQL function if it doesn't exist"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE OR REPLACE FUNCTION normalize_company(name TEXT)
            RETURNS TEXT AS $$
            BEGIN
                RETURN 
                    replace(replace(replace(replace(replace(replace(replace(replace(replace(
                        regexp_replace(upper(trim(name)), '[,. -]', '', 'g'),
                        ' INC', ''),
                        ' LLC', ''),
                        ' LIMITED', ''),
                        ' CORP', ''),
                        ' CORPORATION', ''),
                        ' COMPANY', ''),
                        ' LP', ''),
                        ' PARTNERS', ''),
                        ' PLC', '');
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;
        """)
        conn.commit()
    except Exception as e:
        if "already exists" not in str(e):
            raise e
        
def flatten_list(nested):
    """Flatten a list one level."""
    flat = []
    for item in nested:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    return flat

def merge_vendor_records(vendor_records):
    """Merge multiple database records into a single vendor entry."""
    merged = {}
    for record in vendor_records:
        # Handle None values
        record['certificate'] = record.get('certificate') or []
        record['expirations_all'] = record.get('expirations_all') or []
        record['certs_expired'] = record.get('certs_expired') or []
        # Get the primary key (normalized name)
        name_key = normalize_company(record.get('vendor_name') or record.get('company_dba') or "")
        
        if not name_key:
            continue
            
        if name_key not in merged:
            merged[name_key] = {
                'vendor_name': record.get('vendor_name') or '',
                'company_dba': record.get('company_dba') or '',
                'certificate': flatten_list(record.get('certificate', [])) or [],
                'expirations_all': flatten_list(record.get('expirations_all', [])) or [],
                'certs_expired': flatten_list(record.get('certs_expired', [])),
                'approved': record.get('approved', False),
                'soon_to_expire': record.get('soon_to_expire'),
                'contact': record.get('contact'),
                'phone': record.get('phone'),
                'division': record.get('division'),
                'trade': record.get('trade'),
                'contact_name': record.get('contact_name'),
                'cell_number': record.get('cell_number'),
                'office_number': record.get('office_number'),
                'email': record.get('email'),
                'address': record.get('address'),
                'ca_license': record.get('ca_license'),
                'dir_number': record.get('dir_number'),
                'dvbe': record.get('dvbe')
            }
        else:
            # Merge certificates and expirations
            merged[name_key]['certificate'] = list(set(
                merged[name_key]['certificate'] + 
                flatten_list(record.get('certificate', []))
            ))
            merged[name_key]['expirations_all'] = list(set(
                merged[name_key]['expirations_all'] + 
                flatten_list(record.get('expirations_all', []))
            ))
            merged[name_key]['certs_expired'] = list(set(
                merged[name_key]['certs_expired'] + 
                flatten_list(record.get('certs_expired', []))
            ))
            
            # Merge approval status
            merged[name_key]['approved'] = merged[name_key]['approved'] or record.get('approved', False)
            
            # Prefer non-empty values from vendor_details
            for field in ['contact', 'phone', 'division', 'trade', 
                         'contact_name', 'cell_number', 'office_number',
                         'email', 'address', 'ca_license', 'dir_number', 'dvbe']:
                if not merged[name_key].get(field) and record.get(field):
                    merged[name_key][field] = record.get(field)
                    
    return list(merged.values())

def normalize_company(name):
    """Normalize company names for matching."""
    if not name:
        return ""
    norm = str(name).strip().upper()
    norm = re.sub(r'[,\.\-]', '', norm)
    for suffix in [" INC", " LLC", " LIMITED", " CORP", " CORPORATION", 
                  " COMPANY", " LP", " PARTNERS", " PLC"]:
        if norm.endswith(suffix):
            norm = norm[:-len(suffix)]
    return norm.strip()

# -------------------- Filter Options --------------------

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
    "06 - Wood, Plastics, Composites": [
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

# -------------------- Main Search Page --------------------
def search_page():
    # Initialize normalization function ONCE
    if 'normalize_created' not in st.session_state:
        conn = get_db_connection()
        create_normalize_function(conn)
        conn.close()
        st.session_state.normalize_created = True

    # After normalization
   # duplicates = df[df.duplicated(subset=['company_dba'])]
  #  if not duplicates.empty:
   #     st.warning(f"Found {len(duplicates)} duplicates - keeping first occurrence")
   #     df = df.drop_duplicates(subset=['company_dba'], keep='first')
    
    st.title("Vendor Search")
    
    # --- Sidebar Filters ---
    st.sidebar.header("Filter Vendor Details")
    division_filter = st.sidebar.selectbox("Division", options=division_options, index=0, key="division_filter")
    if division_filter in trade_mapping:
        trade_options = ["All"] + trade_mapping[division_filter]
    else:
        trade_options = ["All"] + full_trade_list
    trade_filter = st.sidebar.selectbox("Trade", options=trade_options, index=0, key="trade_filter")
    filter_dir = st.sidebar.checkbox("Only show vendors with DIR number", key="filter_dir")
    filter_ca = st.sidebar.checkbox("Only show vendors with CA license", key="filter_ca")
    
    # --- Search Input ---
    raw_search = st.text_input("Search Vendor Name (Legal or DBA)", 
                              placeholder="Type vendor name...", 
                              key="raw_search")
    
    # Normalize search term
    normalized_search = normalize_company(raw_search)
    effective_search = f"%{normalized_search}%" if normalized_search else "%"
    
    # Build query
    query = """
        SELECT 
            v.vendor_name,
            v.certificate,
            v.expires,
            v.vendor_type,
            v.contact,
            v.phone,
            v.certs_expired,
            v.approved,
            v.soon_to_expire,
            v.expirations_all,
            vd.division,
            vd.trade,
            vd.company_dba,
            vd.contact_name,
            vd.cell_number,
            vd.office_number,
            vd.email,
            vd.address,
            vd.ca_license,
            vd.dir_number,
            vd.dvbe
        FROM vendors v
        FULL JOIN vendor_details vd 
            ON normalize_company(v.vendor_name) = normalize_company(vd.company_dba)
        WHERE 
            (normalize_company(v.vendor_name) ILIKE %s OR
            normalize_company(vd.company_dba) ILIKE %s)
    """
    params = [effective_search, effective_search]
    
    # Add filters
    if division_filter != "All":
        query += " AND vd.division ILIKE %s"
        params.append(f"%{division_filter}%")
    if trade_filter != "All":
        query += " AND vd.trade ILIKE %s"
        params.append(f"%{trade_filter}%")
    if filter_dir:
        query += " AND (vd.dir_number IS NOT NULL AND vd.dir_number <> '')"
    if filter_ca:
        query += " AND (vd.ca_license IS NOT NULL AND vd.ca_license <> '')"
    
    if st.button("Search") or normalized_search:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            
            if results:
                cols = [desc[0] for desc in cursor.description]
                vendor_records = [dict(zip(cols, row)) for row in results]
                
                # Merge records from both tables
                merged_vendors = merge_vendor_records(vendor_records)
                
                # Display results
                for vendor in merged_vendors:
                    # Calculate expiration info
                    cert_exp_pairs = sorted(
                        zip(vendor['certificate'], vendor['expirations_all']),
                        key=lambda x: x[1]
                    ) if vendor.get('expirations_all') else []
                    
                    with st.expander(f"{vendor.get('vendor_name') or vendor.get('company_dba')}", expanded=False):
                        # Approval status
                        if vendor.get('approved'):
                            st.success("✅ Approved Vendor")
                        else:
                            st.error("❌ Not Approved - Missing Certificates")
                        
                        # Contact Information
                        st.subheader("Contact Details")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Primary Contact:** {vendor.get('contact') or 'N/A'}")
                            st.write(f"**Phone:** {vendor.get('phone') or 'N/A'}")
                            st.write(f"**Email:** {vendor.get('email') or 'N/A'}")
                        with col2:
                            st.write(f"**Secondary Contact:** {vendor.get('contact_name') or 'N/A'}")
                            st.write(f"**Cell:** {vendor.get('cell_number') or 'N/A'}")
                            st.write(f"**Office:** {vendor.get('office_number') or 'N/A'}")
                        
                        # Company Info
                        st.subheader("Company Information")
                        st.write(f"**Address:** {vendor.get('address') or 'N/A'}")
                        st.write(f"**CA License:** {vendor.get('ca_license') or 'N/A'}")
                        st.write(f"**DIR Number:** {vendor.get('dir_number') or 'N/A'}")
                        
                        # Certificates
                        st.subheader("Certificates")
                        if vendor['certificate']:
                            cols = st.columns(2)
                            with cols[0]:
                                st.write("**Valid Certificates:**")
                                st.write("\n".join([f"- {cert}" for cert in vendor['certificate']]))
                            with cols[1]:
                                # MODIFY THIS SECTION
                                cert_exp_pairs = sorted(
                                    zip(vendor['certificate'], vendor['expirations_all']),
                                    key=lambda x: x[1]
                                ) if vendor.get('expirations_all') and vendor['certificate'] else []  # ← Changed line

                                if cert_exp_pairs:
                                    soonest_date = cert_exp_pairs[0][1]
                                    st.write(f"**Earliest Expiration:** {soonest_date.strftime('%Y-%m-%d')}")
                                    days_left = (soonest_date - date.today()).days
                                    if days_left <= 30:
                                        st.warning(f"Expires in {days_left} days")
                        else:
                            st.write("No valid certificates found")
                        
                        # Expired Certificates
                        if vendor['certs_expired']:
                            st.write("**Expired Certificates:**")
                            st.write("\n".join([f"- {cert}" for cert in vendor['certs_expired']]))
            else:
                st.warning("No vendors found matching the search criteria")
                
        except Exception as e:
            st.error(f"Database error: {str(e)}")
        finally:
            conn.close()

if __name__ == "__main__":
    search_page()
