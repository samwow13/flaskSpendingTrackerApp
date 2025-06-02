from flask import Blueprint, request, redirect, url_for, render_template, flash
import sqlite3
import os

# Create a Blueprint for expense-type-related routes
expense_type_routes = Blueprint('expense_type_routes', __name__)

# Database configuration
DB_NAME = 'spending_tracker.db'
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DB_NAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@expense_type_routes.route('/', methods=['GET'])
def manage_expense_types():
    """Display the expense types management page"""
    conn = get_db_connection()
    expense_types = conn.execute('SELECT * FROM expense_types ORDER BY name').fetchall()
    conn.close()
    
    return render_template('manage_expense_types.html', expense_types=expense_types, error=None)

@expense_type_routes.route('/add', methods=['POST'])
def add_expense_type():
    """Add a new expense type"""
    conn = get_db_connection()
    
    try:
        # Get form data
        name = request.form.get('name')
        
        # Basic validation
        if not name or name.strip() == '':
            raise ValueError("Expense type name is required")
            
        # Check if name already exists
        existing = conn.execute('SELECT id FROM expense_types WHERE name = ?', (name,)).fetchone()
        if existing:
            raise ValueError(f"Expense type '{name}' already exists")
        
        # Add the new expense type
        conn.execute('INSERT INTO expense_types (name) VALUES (?)', (name,))
        conn.commit()
        
        # Success - redirect back to manage page
        return redirect(url_for('expense_type_routes.manage_expense_types'))
        
    except ValueError as e:
        # Handle validation errors
        expense_types = conn.execute('SELECT * FROM expense_types ORDER BY name').fetchall()
        return render_template('manage_expense_types.html', expense_types=expense_types, error=str(e))
    
    except sqlite3.Error as e:
        # Handle database errors
        expense_types = conn.execute('SELECT * FROM expense_types ORDER BY name').fetchall()
        return render_template('manage_expense_types.html', expense_types=expense_types, error=f"Database error: {e}")
    
    finally:
        conn.close()

@expense_type_routes.route('/delete/<int:type_id>', methods=['POST'])
def delete_expense_type(type_id):
    """Delete an expense type (always hard delete from DB, regardless of usage)"""
    conn = get_db_connection()
    try:
        # Always perform a hard delete, even if there are expenses referencing this type
        conn.execute('DELETE FROM expense_types WHERE id = ?', (type_id,))
        conn.commit()
        return redirect(url_for('expense_type_routes.manage_expense_types'))
    except sqlite3.Error as e:
        # Handle database errors
        expense_types = conn.execute('SELECT * FROM expense_types ORDER BY name').fetchall()
        return render_template('manage_expense_types.html', expense_types=expense_types, error=f"Database error: {e}")
    finally:
        conn.close()
