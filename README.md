# Vendor Management System

A robust Streamlit application designed to streamline vendor and subcontractor management, focusing on approval status tracking and certification management.

## 🌟 Features

- **Smart Search**
  - Fuzzy search functionality for vendor lookup
  - Intelligent matching with 70% similarity threshold
  - Real-time results filtering

- **Data Management**
  - Bulk data import via CSV upload
  - Automated certificate validation
  - Expiration date tracking
  - Certificate status monitoring

- **Visual Interface**
  - Clean, intuitive user interface
  - Certificate status indicators
  - Expiration warnings
  - Comprehensive vendor details view

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/vendor-management-system.git
   cd vendor-management-system
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Create PostgreSQL database:

   ```sql
   CREATE DATABASE vendor_db;
   ```

4. For local development, create secrets file:

   ```bash
   mkdir -p .streamlit
   echo "[secrets]" > .streamlit/secrets.toml
   echo 'DB_NAME = "vendor_db"' >> .streamlit/secrets.toml
   echo 'DB_USER = "postgres"' >> .streamlit/secrets.toml
   echo 'DB_PASSWORD = "your_password"' >> .streamlit/secrets.toml
   echo 'DB_HOST = "localhost"' >> .streamlit/secrets.toml
   echo 'DB_PORT = "5432"' >> .streamlit/secrets.toml
   ```

5. Launch the application:

   ```bash
   streamlit run app.py
   ```

## 💻 Technical Details

### Database Schema

The system uses PostgreSQL with the following main table structure:

```sql
CREATE TABLE vendors (
    vendor_name TEXT PRIMARY KEY,
    certificate TEXT[],
    expires DATE,
    vendor_type INTEGER,
    contact TEXT,
    phone TEXT,
    certs_expired TEXT[],
    approved BOOLEAN,
    soon_to_expire INTEGER
);
```

### Certificate Types

The system tracks various certificates including:

- Workers Compensation Insurance
- General Liability Insurance
- Auto Liability Insurance
- Umbrella Liability
- Contractors License
- DIR Registration
- Equipment Floater

### Vendor Types

Vendors are categorized as:

0. None
1. Regular Vendor
2. Subcontractor
3. Architect
4. Lender
5. Supplier
6. Accounting/Legal/Consulting
7. Equipment Rental
8. Insurance
9. Fuel

## 🔒 Security Features

- Environment variable-based configuration
- Parameterized SQL queries for injection prevention
- Secure database connection handling
- Input validation and sanitization

## 🛠 Development

### Project Structure

```
vendor-management-system/
├── app.py              # Main application entry
├── search.py          # Search functionality
├── upload.py          # Data upload handling
├── approved_vendors.py # Vendor processing logic
├── requirements.txt    # Dependencies
└── .env               # Configuration
```

### Error Handling

The application implements comprehensive error handling for:

- Database connection issues
- Invalid data formats
- Missing certificates
- Expired certifications
- Processing failures

### Deployment to Streamlit Cloud

1. Create a `secrets.toml` in Streamlit Cloud through app settings

2. Add your database credentials:

```toml
   DB_NAME = "vendor_db"
   DB_USER = "postgres"
   DB_PASSWORD = "your_password"
   DB_HOST = "your-database-host"
   DB_PORT = "5432"`
```

## 🚨 Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check credentials in `.env`
   - Ensure database exists

2. **CSV Upload Issues**
   - Verify CSV format matches expected structure
   - Check for special characters in headers
   - Ensure dates are in correct format (MM/DD/YYYY)

## 🤝 Support

For support, please open an issue in the GitHub repository or contact the development team.
