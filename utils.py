import sqlite3
import os
from datetime import datetime

# Database configuration
DB_NAME = 'spending_tracker.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def get_db_connection():
    """Get a database connection with row factory enabled"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_total_expenses(month, year, conn=None):
    """Calculate total expenses for a given month and year, including recurring expenses.
    
    Args:
        month: Month number (1-12)
        year: Year (e.g., 2025)
        conn: Optional database connection. If not provided, a new connection will be created.
        
    Returns:
        float: Total amount of expenses for the month
    """
    # Create a connection if not provided
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    
    try:
        # Format month and year for date comparison
        month_str = f"{int(month):02d}"
        year_str = str(year)
        
        # Calculate start and end dates for the month
        start_date = f"{year_str}-{month_str}-01"
        
        # Calculate end date based on month/year
        if int(month) == 12:
            end_date = f"{int(year_str) + 1}-01-01"
        else:
            end_date = f"{year_str}-{int(month_str) + 1:02d}-01"
        
        # Get all regular expenses for the month
        expenses = conn.execute('''
            SELECT e.amount
            FROM expenses e
            WHERE e.is_active = TRUE AND e.date >= ? AND e.date < ?
        ''', (start_date, end_date)).fetchall()
        
        # Calculate total from regular expenses
        total_amount = sum(expense['amount'] for expense in expenses)
        
        # Get recurring expenses for this month from recurring_expense_instances table
        recurring_expenses = conn.execute('''
            SELECT rei.amount
            FROM recurring_expense_instances rei
            JOIN months m ON rei.month_id = m.id
            WHERE m.month = ? AND m.year = ?
        ''', (month, year)).fetchall()
        
        # Add recurring expenses to total
        total_amount += sum(expense['amount'] for expense in recurring_expenses)
        
        return total_amount
    
    finally:
        # Close the connection if we created it
        if close_conn:
            conn.close()
