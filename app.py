from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Set a secret key for session management
app.secret_key = 'spending_tracker_secret_key'

# Import and register blueprints
from templateLogic.month_routes import month_routes
from templateLogic.expense_type_routes import expense_type_routes
from templateLogic.expense_routes import expense_routes
app.register_blueprint(month_routes, url_prefix='/month')
app.register_blueprint(expense_type_routes, url_prefix='/expense-types')
app.register_blueprint(expense_routes, url_prefix='/expenses')

# Database configuration
DB_NAME = 'spending_tracker.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    # Fetch expense types to display
    expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
    
    # Get current_month_id from request args or session
    current_month_id = request.args.get('current_month_id', None)
    
    # If current_month_id is provided in the URL, update the session
    if current_month_id:
        session['current_month_id'] = current_month_id
    # Otherwise, try to get it from the session
    elif 'current_month_id' in session:
        current_month_id = session['current_month_id']
    
    # Fetch current month's details based on current_month_id if provided
    if current_month_id:
        current_month_data = conn.execute('SELECT * FROM months WHERE id = ?', (current_month_id,)).fetchone()
        # If month not found, fall back to default behavior
        if not current_month_data:
            current_month_data = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
            # Update session with the fallback month id
            if current_month_data:
                session['current_month_id'] = current_month_data['id']
    else:
        # Default behavior - get most recent month
        current_month_data = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
        # Store the default month id in session
        if current_month_data:
            session['current_month_id'] = current_month_data['id']
    
    # Fetch 10 most recent expenses with expense type names
    recent_expenses = conn.execute('''
        SELECT e.id, e.amount, e.description, e.date, et.name as expense_type_name, e.created_at
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_active = TRUE
        ORDER BY e.created_at DESC
        LIMIT 10
    ''').fetchall()
    
    # Calculate total expenses for the current month
    total_amount = 0.0
    if current_month_data:
        total_amount_row = conn.execute(
            'SELECT SUM(amount) as total FROM expenses WHERE is_active = TRUE AND strftime("%Y", date) = ? AND strftime("%m", date) = ?',
            (str(current_month_data['year']), f"{int(current_month_data['month']):02d}")
        ).fetchone()
        total_amount = total_amount_row['total'] if total_amount_row['total'] is not None else 0.0

    conn.close()
    return render_template('index.html', expense_types=expense_types, current_month=current_month_data, 
                           recent_expenses=recent_expenses, month_error=None, show_month_modal=False, total_amount=total_amount)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    print("--- Accessing /add_expense route ---") # New log
    conn = get_db_connection()
    if request.method == 'POST':
        print("--- /add_expense: POST request received ---") # New log
        print(f"Form data: {request.form}") # New log
        amount = request.form.get('amount') # Use .get() to avoid KeyError if field is missing
        description = request.form.get('description')
        expense_type_id = request.form.get('expense_type_id')
        date = request.form.get('date')
        is_recurring = 'is_recurring' in request.form
        recurring_day = request.form.get('recurring_day') if is_recurring else None

        # Basic validation (can be expanded)
        if not amount or not expense_type_id or not date:
            # Handle error - return to index with error message to display in modal
            expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
            current_month_data = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
            # Fetch recent expenses for the template
            recent_expenses = conn.execute('''
                SELECT e.id, e.amount, e.description, e.date, et.name as expense_type_name, e.created_at
                FROM expenses e
                JOIN expense_types et ON e.expense_type_id = et.id
                WHERE e.is_active = TRUE
                ORDER BY e.created_at DESC
                LIMIT 10
            ''').fetchall()
            conn.close()
            return render_template('index.html', expense_types=expense_types, current_month=current_month_data, 
                                   recent_expenses=recent_expenses, error='Missing required fields', show_modal=True)

        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO expenses (amount, description, expense_type_id, date, is_recurring, recurring_day)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (amount, description, expense_type_id, date, is_recurring, recurring_day))
            conn.commit()
        except sqlite3.Error as e:
            # Handle error - return to index with error message to display in modal
            expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
            current_month_data = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
            # Fetch recent expenses for the template
            recent_expenses = conn.execute('''
                SELECT e.id, e.amount, e.description, e.date, et.name as expense_type_name, e.created_at
                FROM expenses e
                JOIN expense_types et ON e.expense_type_id = et.id
                WHERE e.is_active = TRUE
                ORDER BY e.created_at DESC
                LIMIT 10
            ''').fetchall()
            conn.close()
            return render_template('index.html', expense_types=expense_types, current_month=current_month_data, 
                                   recent_expenses=recent_expenses, error=f'Database error: {e}', show_modal=True)
        finally:
            conn.close()
        
        return redirect(url_for('index')) # Redirect to homepage after adding

    # GET request: we no longer need this since we're using a modal
    # Just redirect to index
    conn.close()
    return redirect(url_for('index'))

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}

if __name__ == '__main__':
    # Create templates folder if it doesn't exist
    # This check might be redundant if app.py is run after setup_db.py or directory structure is managed by version control
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        css_dir = os.path.join(static_dir, 'css')
        if not os.path.exists(css_dir):
            os.makedirs(css_dir)
            # Optionally create an empty style.css if it doesn't exist
            # with open(os.path.join(css_dir, 'style.css'), 'a') as f:
            #     pass 

    app.run(debug=True)
