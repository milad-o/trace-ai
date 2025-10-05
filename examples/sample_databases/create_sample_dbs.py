"""Create sample SQLite databases for enterprise testing.

This script creates realistic enterprise databases that integrate with
the COBOL/JCL workflow, simulating a mainframe-to-relational migration.
"""

import sqlite3
from pathlib import Path

# Database directory
DB_DIR = Path(__file__).parent


def create_customer_db():
    """Create customer database matching COBOL CUSTOMER-RECORD structure."""
    db_path = DB_DIR / "customer.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create customers table (matches COBOL data layout)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_addr TEXT,
            customer_city TEXT,
            customer_state TEXT,
            customer_zip TEXT,
            customer_phone TEXT,
            account_balance REAL DEFAULT 0.0,
            credit_limit REAL DEFAULT 5000.0,
            last_purchase_date TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_name ON customers(customer_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_state ON customers(customer_state)")

    # Insert sample data
    customers = [
        (1001, "ACME Corporation", "123 Main St", "New York", "NY", "10001", "212-555-0100", 15000.50, 50000.0, "2024-01-15"),
        (1002, "Global Industries", "456 Oak Ave", "Chicago", "IL", "60601", "312-555-0200", 8500.75, 25000.0, "2024-02-20"),
        (1003, "Tech Solutions Inc", "789 Pine Rd", "San Francisco", "CA", "94102", "415-555-0300", 22000.00, 75000.0, "2024-03-10"),
        (1004, "Enterprise Systems", "321 Elm St", "Boston", "MA", "02101", "617-555-0400", 12500.25, 40000.0, "2024-01-25"),
        (1005, "Data Services LLC", "654 Maple Dr", "Seattle", "WA", "98101", "206-555-0500", 18900.60, 60000.0, "2024-02-15"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO customers
        (customer_id, customer_name, customer_addr, customer_city, customer_state,
         customer_zip, customer_phone, account_balance, credit_limit, last_purchase_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, customers)

    conn.commit()
    conn.close()
    print(f"✓ Created {db_path} with {len(customers)} customers")


def create_sales_db():
    """Create sales/transactions database."""
    db_path = DB_DIR / "sales.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT CHECK(transaction_type IN ('SALE', 'PAYMENT', 'REFUND')),
            amount REAL NOT NULL,
            description TEXT,
            processed_by TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    # Create sales summary table (matching COBOL report output)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_summary (
            summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL,
            total_sales REAL DEFAULT 0.0,
            total_payments REAL DEFAULT 0.0,
            total_refunds REAL DEFAULT 0.0,
            transaction_count INTEGER DEFAULT 0,
            created_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_customer ON transactions(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(transaction_date)")

    # Insert sample transactions
    transactions = [
        (1001, "2024-01-15", "SALE", 5000.00, "Q1 Equipment Purchase", "SYSTEM"),
        (1001, "2024-02-01", "PAYMENT", 2500.00, "Payment Received", "SYSTEM"),
        (1002, "2024-02-20", "SALE", 3500.00, "Software Licenses", "SYSTEM"),
        (1003, "2024-03-10", "SALE", 12000.00, "Annual Service Contract", "SYSTEM"),
        (1003, "2024-03-15", "REFUND", 1000.00, "Partial Refund - Service Credit", "SYSTEM"),
        (1004, "2024-01-25", "SALE", 7500.00, "Hardware Upgrade", "SYSTEM"),
        (1004, "2024-02-10", "PAYMENT", 7500.00, "Full Payment", "SYSTEM"),
        (1005, "2024-02-15", "SALE", 9500.00, "Consulting Services", "SYSTEM"),
    ]

    cursor.executemany("""
        INSERT INTO transactions
        (customer_id, transaction_date, transaction_type, amount, description, processed_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, transactions)

    # Create summary record
    cursor.execute("""
        INSERT INTO sales_summary (report_date, total_sales, total_payments, total_refunds, transaction_count)
        VALUES ('2024-03-31', 37500.00, 10000.00, 1000.00, 8)
    """)

    conn.commit()
    conn.close()
    print(f"✓ Created {db_path} with {len(transactions)} transactions")


def create_inventory_db():
    """Create product inventory database."""
    db_path = DB_DIR / "inventory.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            product_category TEXT,
            unit_price REAL NOT NULL,
            quantity_on_hand INTEGER DEFAULT 0,
            reorder_level INTEGER DEFAULT 10,
            supplier_id INTEGER,
            last_restock_date TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create suppliers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id INTEGER PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            contact_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT
        )
    """)

    # Create inventory movements table (matches JCL job processing)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_movements (
            movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT CHECK(movement_type IN ('IN', 'OUT', 'ADJUST')),
            quantity INTEGER NOT NULL,
            movement_date TEXT NOT NULL,
            reference_doc TEXT,
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_category ON products(product_category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_movement_date ON inventory_movements(movement_date)")

    # Insert suppliers
    suppliers = [
        (1, "Tech Supplies Inc", "John Smith", "555-0100", "john@techsupplies.com", "100 Tech Pkwy"),
        (2, "Global Hardware", "Jane Doe", "555-0200", "jane@globalhw.com", "200 Industrial Blvd"),
        (3, "Software Distributors", "Bob Johnson", "555-0300", "bob@softdist.com", "300 Digital Ave"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO suppliers
        (supplier_id, supplier_name, contact_name, phone, email, address)
        VALUES (?, ?, ?, ?, ?, ?)
    """, suppliers)

    # Insert products
    products = [
        (2001, "Desktop Computer", "HARDWARE", 1200.00, 50, 10, 2, "2024-01-10"),
        (2002, "Laptop Computer", "HARDWARE", 1500.00, 30, 8, 2, "2024-01-15"),
        (2003, "Office Suite License", "SOFTWARE", 300.00, 100, 20, 3, "2024-02-01"),
        (2004, "Database License", "SOFTWARE", 5000.00, 10, 5, 3, "2024-02-10"),
        (2005, "Network Switch", "HARDWARE", 800.00, 15, 5, 2, "2024-03-01"),
        (2006, "Backup Storage", "HARDWARE", 2000.00, 20, 8, 1, "2024-03-05"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO products
        (product_id, product_name, product_category, unit_price, quantity_on_hand,
         reorder_level, supplier_id, last_restock_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, products)

    # Insert inventory movements
    movements = [
        (2001, "IN", 50, "2024-01-10", "PO-1001", "Initial stock"),
        (2001, "OUT", 15, "2024-02-15", "SO-5001", "Sold to ACME Corp"),
        (2002, "IN", 30, "2024-01-15", "PO-1002", "Initial stock"),
        (2003, "IN", 100, "2024-02-01", "PO-1003", "License purchase"),
        (2003, "OUT", 25, "2024-02-20", "SO-5002", "Global Industries order"),
        (2005, "IN", 15, "2024-03-01", "PO-1004", "Network upgrade stock"),
    ]

    cursor.executemany("""
        INSERT INTO inventory_movements
        (product_id, movement_type, quantity, movement_date, reference_doc, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, movements)

    conn.commit()
    conn.close()
    print(f"✓ Created {db_path} with {len(products)} products, {len(suppliers)} suppliers, {len(movements)} movements")


def create_employee_db():
    """Create employee/payroll database (matches COBOL EMPPAY.CBL)."""
    db_path = DB_DIR / "employee.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create employees table (matches COBOL employee record)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            emp_id INTEGER PRIMARY KEY,
            emp_name TEXT NOT NULL,
            emp_dept TEXT,
            emp_title TEXT,
            hire_date TEXT,
            salary REAL NOT NULL,
            commission_rate REAL DEFAULT 0.0,
            status TEXT CHECK(status IN ('ACTIVE', 'INACTIVE', 'TERMINATED'))
        )
    """)

    # Create payroll table (matches COBOL payroll processing)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll (
            payroll_id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            pay_period TEXT NOT NULL,
            regular_hours REAL DEFAULT 0.0,
            overtime_hours REAL DEFAULT 0.0,
            gross_pay REAL NOT NULL,
            tax_withheld REAL NOT NULL,
            net_pay REAL NOT NULL,
            processed_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )
    """)

    # Create departments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            dept_code TEXT PRIMARY KEY,
            dept_name TEXT NOT NULL,
            manager_id INTEGER,
            budget REAL DEFAULT 0.0
        )
    """)

    # Insert departments
    departments = [
        ("SALES", "Sales Department", 1001, 500000.0),
        ("IT", "Information Technology", 1002, 750000.0),
        ("HR", "Human Resources", 1003, 300000.0),
        ("FIN", "Finance", 1004, 400000.0),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO departments (dept_code, dept_name, manager_id, budget)
        VALUES (?, ?, ?, ?)
    """, departments)

    # Insert employees
    employees = [
        (1001, "Alice Johnson", "SALES", "Sales Manager", "2020-01-15", 75000.00, 0.05, "ACTIVE"),
        (1002, "Bob Smith", "IT", "IT Director", "2019-03-20", 95000.00, 0.0, "ACTIVE"),
        (1003, "Carol White", "HR", "HR Manager", "2021-05-10", 70000.00, 0.0, "ACTIVE"),
        (1004, "David Brown", "FIN", "Finance Manager", "2018-07-01", 85000.00, 0.0, "ACTIVE"),
        (1005, "Eve Davis", "SALES", "Sales Rep", "2022-02-15", 55000.00, 0.08, "ACTIVE"),
        (1006, "Frank Miller", "IT", "Developer", "2022-06-01", 80000.00, 0.0, "ACTIVE"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO employees
        (emp_id, emp_name, emp_dept, emp_title, hire_date, salary, commission_rate, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, employees)

    # Insert payroll records
    payroll = [
        (1001, "2024-01", 160.0, 5.0, 6500.00, 1300.00, 5200.00),
        (1002, "2024-01", 160.0, 0.0, 7916.67, 1583.33, 6333.34),
        (1003, "2024-01", 160.0, 0.0, 5833.33, 1166.67, 4666.66),
        (1004, "2024-01", 160.0, 2.0, 7291.67, 1458.33, 5833.34),
        (1005, "2024-01", 160.0, 0.0, 4583.33, 916.67, 3666.66),
        (1006, "2024-01", 160.0, 8.0, 7000.00, 1400.00, 5600.00),
    ]

    cursor.executemany("""
        INSERT INTO payroll
        (emp_id, pay_period, regular_hours, overtime_hours, gross_pay, tax_withheld, net_pay)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, payroll)

    conn.commit()
    conn.close()
    print(f"✓ Created {db_path} with {len(employees)} employees, {len(departments)} departments, {len(payroll)} payroll records")


if __name__ == "__main__":
    print("\n🗄️  Creating Sample Enterprise Databases...\n")

    create_customer_db()
    create_sales_db()
    create_inventory_db()
    create_employee_db()

    print("\n✅ All databases created successfully!")
    print(f"\nDatabases location: {DB_DIR}")
    print("\nDatabases created:")
    print("  • customer.db   - Customer records (COBOL CUSTOMER-RECORD)")
    print("  • sales.db      - Transactions and sales summary")
    print("  • inventory.db  - Products, suppliers, movements")
    print("  • employee.db   - Employees, departments, payroll (COBOL EMPPAY)")
