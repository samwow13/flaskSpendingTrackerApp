from flask import Blueprint, request, redirect, url_for, render_template, flash, session
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
        monthly_income = request.form.get('monthly_income')
        
        # Basic validation
        if not month or not year or not monthly_income:
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
            SET month = ?, year = ?, monthly_income = ? 
            WHERE id = ?
        ''', (month, year, monthly_income, month_id))
        
        conn.commit()
        
        # Success - redirect to index
        return redirect(url_for('index'))
        
    except ValueError as e:
        # Handle validation errors
        expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
        current_month_data = conn.execute('SELECT * FROM months WHERE id = ?', (month_id,)).fetchone()
        
        # Calculate total expenses for the current month
        total_amount = 0.0
        if current_month_data:
            total_amount_row = conn.execute(
                'SELECT SUM(amount) as total FROM expenses WHERE is_active = TRUE AND strftime("%Y", date) = ? AND strftime("%m", date) = ?',
                (str(current_month_data['year']), f"{int(current_month_data['month']):02d}")
            ).fetchone()
            total_amount = total_amount_row['total'] if total_amount_row['total'] is not None else 0.0
        
        # Fetch recent expenses for the template
        recent_expenses = conn.execute('''
            SELECT e.id, e.amount, e.description, e.date, et.name as expense_type_name, e.created_at
            FROM expenses e
            JOIN expense_types et ON e.expense_type_id = et.id
            WHERE e.is_active = TRUE
            ORDER BY e.created_at DESC
            LIMIT 10
        ''').fetchall()
        
        # Return to index with error in the month modal
        return render_template('index.html', 
                              expense_types=expense_types, 
                              current_month=current_month_data, 
                              month_error=str(e),
                              show_month_modal=True,
                              total_amount=total_amount,
                              recent_expenses=recent_expenses)
    
    except sqlite3.Error as e:
        # Handle database errors
        expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
        current_month_data = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
        
        # Calculate total expenses for the current month
        total_amount = 0.0
        if current_month_data:
            total_amount_row = conn.execute(
                'SELECT SUM(amount) as total FROM expenses WHERE is_active = TRUE AND strftime("%Y", date) = ? AND strftime("%m", date) = ?',
                (str(current_month_data['year']), f"{int(current_month_data['month']):02d}")
            ).fetchone()
            total_amount = total_amount_row['total'] if total_amount_row['total'] is not None else 0.0
        
        # Fetch recent expenses for the template
        recent_expenses = conn.execute('''
            SELECT e.id, e.amount, e.description, e.date, et.name as expense_type_name, e.created_at
            FROM expenses e
            JOIN expense_types et ON e.expense_type_id = et.id
            WHERE e.is_active = TRUE
            ORDER BY e.created_at DESC
            LIMIT 10
        ''').fetchall()
        
        return render_template('index.html', 
                              expense_types=expense_types, 
                              current_month=current_month_data, 
                              month_error=f"Database error: {e}",
                              show_month_modal=True,
                              total_amount=total_amount,
                              recent_expenses=recent_expenses)
    
    finally:
        conn.close()

@month_routes.route('/months', methods=['GET'])
def list_months():
    """List all months"""
    conn = get_db_connection()
    months = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC').fetchall()
    # For each month, calculate total expenses
    months_with_expenses = []
    for month in months:
        total_expenses = conn.execute('SELECT IFNULL(SUM(amount), 0) as total FROM expenses WHERE strftime("%Y", date) = ? AND strftime("%m", date) = ?', (str(month['year']), str(month['month']).zfill(2))).fetchone()['total']
        month_dict = dict(month)
        month_dict['total_expenses'] = total_expenses
        months_with_expenses.append(month_dict)
    
    # Get current month from session or default to most recent
    current_month_id = None
    if 'current_month_id' in session:
        current_month_id = session['current_month_id']
    else:
        # Get the most recent month if no session data
        current_month = conn.execute('SELECT id FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
        if current_month:
            current_month_id = current_month['id']
            # Store in session
            session['current_month_id'] = current_month_id
    
    # Get latest monthly income for pre-filling the form
    latest_monthly_income = None
    latest_month = conn.execute('SELECT monthly_income FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
    if latest_month:
        latest_monthly_income = latest_month['monthly_income']
    
    conn.close()
    
    # Return a dedicated months selection page
    return render_template('select_month.html', months=months_with_expenses, current_month_id=current_month_id, latest_monthly_income=latest_monthly_income)

@month_routes.route('/add_month', methods=['POST'])
def add_month():
    """Add a new month to track"""
    conn = get_db_connection()
    
    try:
        # Get form data
        month = request.form.get('month')
        year = request.form.get('year')
        monthly_income = request.form.get('monthly_income')
        
        # Basic validation
        if not month or not year or not monthly_income:
            raise ValueError("All fields are required")
            
        # Check if month/year combination already exists
        existing = conn.execute(
            'SELECT id FROM months WHERE month = ? AND year = ?', 
            (month, year)
        ).fetchone()
        
        if existing:
            raise ValueError(f"A record for this month/year combination already exists")
        
        # Insert the new month record
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO months (month, year, monthly_income)
            VALUES (?, ?, ?)
        ''', (month, year, monthly_income))
        
        conn.commit()
        new_month_id = cursor.lastrowid
        
        # Store the new month in session and redirect to index
        session['current_month_id'] = new_month_id
        conn.close()
        return redirect(url_for('index', current_month_id=new_month_id))
        
    except ValueError as e:
        # Handle validation errors
        months = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC').fetchall()
        current_month = conn.execute('SELECT id FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
        current_month_id = current_month['id'] if current_month else None
        
        conn.close()
        # Return to select_month with error
        return render_template('select_month.html', 
                              months=months, 
                              current_month_id=current_month_id,
                              month_error=str(e))
    
    except sqlite3.Error as e:
        # Handle database errors
        months = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC').fetchall()
        current_month = conn.execute('SELECT id FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
        current_month_id = current_month['id'] if current_month else None
        
        conn.close()
        return render_template('select_month.html', 
                              months=months, 
                              current_month_id=current_month_id,
                              month_error=f"Database error: {e}")

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
    
    # Store the selected month in the session
    session['current_month_id'] = month_id
    
    conn.close()
    
    # Redirect back to the index page, which will now show the selected month as current
    return redirect(url_for('index', current_month_id=month_id))
