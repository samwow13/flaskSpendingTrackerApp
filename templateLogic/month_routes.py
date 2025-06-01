from flask import Blueprint, request, redirect, url_for, render_template, flash
import sqlite3
import os

# Create a Blueprint for month-related routes
month_routes = Blueprint('month_routes', __name__)

# Database configuration
DB_NAME = 'spending_tracker.db'
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DB_NAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@month_routes.route('/update_month', methods=['POST'])
def update_month():
    """Update month details"""
    conn = get_db_connection()
    
    try:
        # Get form data
        month_id = request.form.get('month_id')
        month = request.form.get('month')
        year = request.form.get('year')
        starting_bank_value = request.form.get('starting_bank_value')
        monthly_income = request.form.get('monthly_income')
        
        # Basic validation
        if not month or not year or not starting_bank_value or not monthly_income:
            raise ValueError("All fields are required")
            
        # Check if month/year combination already exists (for a different month_id)
        existing = conn.execute(
            'SELECT id FROM months WHERE month = ? AND year = ? AND id != ?', 
            (month, year, month_id)
        ).fetchone()
        
        if existing:
            raise ValueError(f"A record for {month}/{year} already exists")
        
        # Update the month record
        conn.execute('''
            UPDATE months 
            SET month = ?, year = ?, starting_bank_value = ?, monthly_income = ? 
            WHERE id = ?
        ''', (month, year, starting_bank_value, monthly_income, month_id))
        
        conn.commit()
        
        # Success - redirect to index
        return redirect(url_for('index'))
        
    except ValueError as e:
        # Handle validation errors
        expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
        current_month_data = conn.execute('SELECT * FROM months WHERE id = ?', (month_id,)).fetchone()
        
        # Return to index with error in the month modal
        return render_template('index.html', 
                              expense_types=expense_types, 
                              current_month=current_month_data, 
                              month_error=str(e),
                              show_month_modal=True)
    
    except sqlite3.Error as e:
        # Handle database errors
        expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
        current_month_data = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
        
        return render_template('index.html', 
                              expense_types=expense_types, 
                              current_month=current_month_data, 
                              month_error=f"Database error: {e}",
                              show_month_modal=True)
    
    finally:
        conn.close()

@month_routes.route('/months', methods=['GET'])
def list_months():
    """List all months"""
    conn = get_db_connection()
    months = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC').fetchall()
    
    # Get current month for highlighting in the UI
    current_month = conn.execute('SELECT id FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
    current_month_id = current_month['id'] if current_month else None
    
    conn.close()
    
    # Return a dedicated months selection page
    return render_template('select_month.html', months=months, current_month_id=current_month_id)

@month_routes.route('/set_current_month/<int:month_id>', methods=['GET'])
def set_current_month(month_id):
    """Set the specified month as the current focus"""
    conn = get_db_connection()
    
    # Verify the month exists
    month = conn.execute('SELECT * FROM months WHERE id = ?', (month_id,)).fetchone()
    
    if not month:
        # Month not found, redirect to index
        conn.close()
        return redirect(url_for('index'))
    
    # In a real application with user accounts, we would store the current month preference
    # in the user's profile or session. For this app, we'll use a simple approach:
    # We'll just reorder the months in the database query to make this month appear first.
    # This is a simplification - in a production app, you might want to store this in a user preferences table.
    
    conn.close()
    
    # Redirect back to the index page, which will now show the selected month as current
    return redirect(url_for('index', current_month_id=month_id))
