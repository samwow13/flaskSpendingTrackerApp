from flask import Blueprint, request, redirect, url_for, render_template, flash, session
import sqlite3
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

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
        
        # Process recurring expenses for the new month
        process_recurring_expenses(conn, int(month), int(year), new_month_id)
        
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

def process_recurring_expenses(conn, new_month, new_year, new_month_id):
    """Process recurring expenses for a newly created month
    
    This function checks all active recurring expenses and creates instances for the new month
    based on their recurring_interval:
    - 'monthly': Creates an instance every month on the specified day
    - 'biannual': Creates an instance every 6 months
    - 'yearly': Creates an instance every 12 months
    """
    print(f"\n\n==== Processing recurring expenses for {new_month}/{new_year} (Month ID: {new_month_id}) ====")
    try:
        # Get all active recurring expenses
        cursor = conn.cursor()
        recurring_expenses = cursor.execute("""
            SELECT id, amount, description, date, expense_type_id, recurring_interval, recurring_day
            FROM expenses
            WHERE is_active = 1 AND recurring_interval != 'none'
        """).fetchall()
        
        print(f"Found {len(recurring_expenses)} active recurring expenses")
        for idx, expense in enumerate(recurring_expenses):
            print(f"\nExpense #{idx+1}:")
            print(f"  ID: {expense['id']}")
            print(f"  Description: {expense['description']}")
            print(f"  Amount: ${expense['amount']}")
            print(f"  Date: {expense['date']}")
            print(f"  Recurring Interval: {expense['recurring_interval']}")
            print(f"  Recurring Day: {expense['recurring_day']}")
        
        # Calculate the target date for the new month
        target_date = date(new_year, new_month, 1)
        
        for expense in recurring_expenses:
            # Get the original expense date
            original_date = datetime.strptime(expense['date'], '%Y-%m-%d').date()
            expense_id = expense['id']
            recurring_interval = expense['recurring_interval']
            recurring_day = expense['recurring_day']
            
            # Determine if this recurring expense should be included in the new month
            should_include = False
            new_expense_date = None
            
            if recurring_interval == 'monthly':
                # Monthly expenses recur every month on the specified day
                should_include = True
                
                # Use the recurring_day if specified, otherwise use the day from the original date
                day_to_use = int(recurring_day) if recurring_day is not None else original_date.day
                print(f"  Monthly expense - using day: {day_to_use} (from recurring_day: {recurring_day}, type: {type(recurring_day)})")
                print(f"  Original date: {original_date}, day: {original_date.day}")
                
                # Make sure the day is valid for the month (e.g., no February 30)
                last_day_of_month = (date(new_year, new_month, 1) + relativedelta(months=1, days=-1)).day
                day_to_use = min(day_to_use, last_day_of_month)
                print(f"  Adjusted day for month length: {day_to_use}")
                
                new_expense_date = date(new_year, new_month, day_to_use)
                print(f"  New expense date: {new_expense_date}")
                
            elif recurring_interval == 'biannual':
                # Biannual expenses recur every 6 months
                # Calculate months difference between original date and target date
                months_diff = (new_year - original_date.year) * 12 + (new_month - original_date.month)
                should_include = months_diff % 6 == 0
                
                if should_include:
                    # Use the same day of the month if possible
                    day_to_use = min(original_date.day, (date(new_year, new_month, 1) + relativedelta(months=1, days=-1)).day)
                    new_expense_date = date(new_year, new_month, day_to_use)
                
            elif recurring_interval == 'yearly':
                # Yearly expenses recur every 12 months
                # Check if month and day match (same month every year)
                should_include = new_month == original_date.month
                
                if should_include:
                    # Use the same day of the month if possible
                    day_to_use = min(original_date.day, (date(new_year, new_month, 1) + relativedelta(months=1, days=-1)).day)
                    new_expense_date = date(new_year, new_month, day_to_use)
            
            # If this expense should be included in the new month, create a recurring instance
            if should_include and new_expense_date:
                # Format the date as string for database
                new_date_str = new_expense_date.strftime('%Y-%m-%d')
                
                print(f"  Creating recurring instance for {new_date_str}")
                
                # Create a new recurring expense instance
                cursor.execute("""
                    INSERT INTO recurring_expense_instances 
                    (expense_id, month_id, instance_date, amount, description, expense_type_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    expense_id, 
                    new_month_id, 
                    new_date_str,
                    expense['amount'],
                    expense['description'],
                    expense['expense_type_id']
                ))
        
        # Commit all changes
        conn.commit()
        print("\n==== Successfully processed recurring expenses ====\n")
        
    except Exception as e:
        # Log the error but don't fail the month creation
        print(f"\n==== ERROR processing recurring expenses: {e} ====\n")
        import traceback
        traceback.print_exc()
        # Roll back any changes made
        conn.rollback()

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
