import streamlit as st
from search import search_page
from upload import upload_page
from view_data import view_data_page

# Configure page
st.set_page_config(
    page_title="Vendor Management System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"  # sidebar expanded for demo
)

# Horizontal navigation buttons
def create_horizontal_nav():
    col1, col2, col3, _ = st.columns([1,1,1,6])
    with col1:
        if st.button("🔍 Search Vendors"):
            st.session_state.current_page = "search"
    with col2:
        if st.button("📤 Upload Data"):
            st.session_state.current_page = "upload"
    with col3:
        if st.button("📊 View All Data"):
            st.session_state.current_page = "view_data"

# Initialize session state if not already set
if "current_page" not in st.session_state:
    st.session_state.current_page = "search"

# Create navigation and display selected page
create_horizontal_nav()
st.write("---")
if st.session_state.current_page == "search":
    search_page()
elif st.session_state.current_page == "upload":
    upload_page()
elif st.session_state.current_page == "view_data":
    view_data_page()
