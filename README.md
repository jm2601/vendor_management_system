# Vendor Management System

A Streamlit application for managing vendor approvals and certifications.

## Setup

1. Clone the repository
2. Install requirements:
   ```bash
   pip install -r requirements.txt
3. Create a `.env` file with PostgreSQL credentials:

```
DB_NAME=vendor_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```
4. Set up PostgreSQL database:
    ```bash
   CREATE DATABASE vendor_db;
5. Run the app:
    ```bash
    streamlit run app.py

**Features**
- 🔍 Fuzzy search for vendors

- 📤 CSV upload with processing

- 📊 Data visualization

- PostgreSQL database integration


**Key Implementation Notes:**

1. **Database Setup:**
- Create PostgreSQL database named `vendor_db`
- Table structure matches the processed CSV format

2. **Fuzzy Search:**
- Uses `fuzzywuzzy` for approximate string matching
- Threshold set to 70% match score

3. **Security:**
- Database credentials stored in `.env` file
- Uses parameterized SQL queries to prevent injection

4. **Error Handling:**
- Graceful handling of missing data
- Database connection cleanup

5. **Preprocessing:**
- Modified `approved_vendors.py` needs to return processed DataFrame
- Ensure date formatting matches PostgreSQL requirements
