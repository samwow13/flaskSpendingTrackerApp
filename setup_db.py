#!/usr/bin/env python3
"""
Database Setup Script for Spending Tracker
Creates and initializes the SQLite database with required tables.
"""

import sqlite3
import os
from datetime import datetime

# Database configuration
DB_NAME = 'spending_tracker.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def create_database():
    """Create the database and tables"""
    
    # Hard delete the old database if it exists
    if os.path.exists(DB_PATH):
        print(f"Removing existing database: {DB_PATH}")
        os.remove(DB_PATH)
    
    # Create new database connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create expense_types table
    cursor.execute('''
        CREATE TABLE expense_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create months table
    cursor.execute('''
        CREATE TABLE months (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
            year INTEGER NOT NULL CHECK (year >= 2020),
            starting_bank_value DECIMAL(10, 2) DEFAULT 0.00,
            monthly_income DECIMAL(10, 2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(month, year)
        )
    ''')
    
    # Create expenses table with updated recurring fields
    cursor.execute('''
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount DECIMAL(10, 2) NOT NULL,
            description TEXT,
            expense_type_id INTEGER NOT NULL,
            date DATE NOT NULL,
            recurring_interval TEXT CHECK (recurring_interval IN ('none', 'monthly', 'biannual', 'yearly') OR recurring_interval IS NULL),
            recurring_day INTEGER CHECK (recurring_day >= 1 AND recurring_day <= 31),
            is_recurring_template BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (expense_type_id) REFERENCES expense_types(id)
        )
    ''')
    
    # Create recurring_expenses table (for tracking instances of recurring expenses)
    cursor.execute('''
        CREATE TABLE recurring_expense_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            month_id INTEGER NOT NULL,
            instance_date DATE NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            description TEXT,
            expense_type_id INTEGER NOT NULL,
            is_paid BOOLEAN DEFAULT FALSE,
            paid_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE,
            FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE,
            FOREIGN KEY (expense_type_id) REFERENCES expense_types(id),
            UNIQUE(expense_id, month_id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX idx_expenses_date ON expenses(date)')
    cursor.execute('CREATE INDEX idx_expenses_type ON expenses(expense_type_id)')
    cursor.execute('CREATE INDEX idx_expenses_recurring ON expenses(recurring_interval)')
    cursor.execute('CREATE INDEX idx_months_date ON months(year, month)')
    
    # Create trigger to update updated_at timestamp
    cursor.execute('''
        CREATE TRIGGER update_expense_timestamp 
        AFTER UPDATE ON expenses
        BEGIN
            UPDATE expenses SET updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END
    ''')
    
    # Insert default expense types
    default_types = [
        'Rent/Mortgage',
        'Utilities',
        'Phone',
        'Internet',
        'Insurance',
        'Groceries',
        'Gas',
        'Shopping',
        'Entertainment',
        'Dining Out',
        'Amazon',
        'Healthcare',
        'Other'
    ]
    
    for expense_type in default_types:
        cursor.execute('INSERT INTO expense_types (name) VALUES (?)', (expense_type,))
    
    # Insert current month record
    current_date = datetime.now()
    cursor.execute('''
        INSERT INTO months (month, year, starting_bank_value, monthly_income)
        VALUES (?, ?, 0.00, 0.00)
    ''', (current_date.month, current_date.year))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Database created successfully at: {DB_PATH}")
    print(f"Created tables: expense_types, months, expenses, recurring_expense_instances")
    print(f"Inserted {len(default_types)} default expense types")
    print(f"Initialized current month: {current_date.strftime('%B %Y')}")

def verify_database():
    """Verify the database was created correctly"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = cursor.fetchall()
    
    print("\nDatabase verification:")
    print("Tables created:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} records")
    
    conn.close()

if __name__ == "__main__":
    print("Setting up Spending Tracker Database...")
    print("=" * 50)
    
    try:
        create_database()
        verify_database()
        print("\nDatabase setup completed successfully!")
    except Exception as e:
        print(f"\nError setting up database: {e}")
        exit(1)