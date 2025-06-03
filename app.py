from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime
from utils import calculate_total_expenses

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
    
    # Calculate total expenses for the current month using the consistent calculation function
    total_amount = 0.0
    if current_month_data:
        total_amount = calculate_total_expenses(current_month_data['month'], current_month_data['year'], conn)

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
        recurring_interval = request.form.get('recurring_interval', 'none')
        
        # Only use recurring_day for monthly recurrences
        recurring_day = None
        if recurring_interval == 'monthly':
            recurring_day = request.form.get('recurring_day')
            
            # If recurring_day is not provided, extract it from the date
            if not recurring_day and date:
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    recurring_day = date_obj.day
                except ValueError:
                    pass

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
            
            # For recurring expenses, we only create the recurring expense template
            # The actual instances will be generated by the get_recurring_expenses_for_month function
            # when viewing a specific month
            
            # Check if this is a recurring expense
            if recurring_interval != 'none':
                # This is a recurring expense - create it as a template only
                print(f"Creating recurring expense template with interval: {recurring_interval}")
                
                # Set is_recurring_template flag to TRUE for recurring expenses
                # This will help distinguish between the template and actual instances
                cursor.execute('''
                    INSERT INTO expenses (amount, description, expense_type_id, date, 
                                         recurring_interval, recurring_day, is_recurring_template)
                    VALUES (?, ?, ?, ?, ?, ?, TRUE)
                ''', (amount, description, expense_type_id, date, recurring_interval, recurring_day))
            else:
                # This is a regular non-recurring expense
                print("Creating regular non-recurring expense")
                cursor.execute('''
                    INSERT INTO expenses (amount, description, expense_type_id, date, 
                                         recurring_interval, recurring_day, is_recurring_template)
                    VALUES (?, ?, ?, ?, ?, ?, FALSE)
                ''', (amount, description, expense_type_id, date, recurring_interval, recurring_day))
            
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

@app.route('/reset_data', methods=['POST'])
def reset_data():
    """Reset all data in the database except for expense types"""
    from flask import jsonify
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete data from tables in order to respect foreign key constraints
        cursor.execute('DELETE FROM recurring_expense_instances')
        cursor.execute('DELETE FROM expenses')
        
        # For months table, we'll keep the current month but reset its values
        current_date = datetime.now()
        cursor.execute('DELETE FROM months')
        cursor.execute('''
            INSERT INTO months (month, year, starting_bank_value, monthly_income)
            VALUES (?, ?, 0.00, 0.00)
        ''', (current_date.month, current_date.year))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'All data has been reset successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error resetting data: {str(e)}'}), 500

@app.route('/seed_data', methods=['POST'])
def seed_data():
    """Generate random expense data for the currently selected month"""
    from flask import jsonify
    import random
    from datetime import datetime, timedelta
    
    try:
        # Get the current month from session
        if 'current_month_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'No month selected. Please select a month first.'
            }), 400
        
        current_month_id = session['current_month_id']
        
        conn = get_db_connection()
        
        # Get the current month details
        current_month = conn.execute('SELECT * FROM months WHERE id = ?', (current_month_id,)).fetchone()
        if not current_month:
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Selected month not found. Please select a valid month.'
            }), 404
        
        # Get all active expense types
        expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE').fetchall()
        if not expense_types:
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'No expense types found. Please ensure the database is set up correctly.'
            }), 404
        
        # Create realistic descriptions for each expense type
        expense_descriptions = {
            'Rent/Mortgage': ['Monthly rent payment', 'Mortgage payment', 'Housing payment'],
            'Utilities': ['Electric bill', 'Water bill', 'Gas bill', 'Utility payment'],
            'Phone': ['Phone bill', 'Mobile service payment', 'Cell phone bill'],
            'Internet': ['Internet service', 'WiFi bill', 'Broadband payment'],
            'Insurance': ['Car insurance', 'Health insurance', 'Home insurance', 'Life insurance premium'],
            'Groceries': ['Weekly grocery shopping', 'Supermarket run', 'Food shopping', 'Grocery store'],
            'Gas': ['Gas station fill-up', 'Fuel purchase', 'Car fuel'],
            'Shopping': ['Clothing purchase', 'Department store', 'Online shopping', 'Retail purchase'],
            'Entertainment': ['Movie tickets', 'Concert tickets', 'Streaming subscription', 'Game purchase'],
            'Dining Out': ['Restaurant meal', 'Fast food', 'Coffee shop', 'Lunch out', 'Dinner date'],
            'Amazon': ['Amazon order', 'Amazon purchase', 'Online order'],
            'Healthcare': ['Doctor visit', 'Prescription medication', 'Dental appointment', 'Medical bill'],
            'Other': ['Miscellaneous expense', 'General purchase', 'Unexpected cost', 'Service fee']
        }
        
        # Generate realistic expense amounts for each type
        expense_amounts = {
            'Rent/Mortgage': (800, 2500),
            'Utilities': (50, 300),
            'Phone': (40, 150),
            'Internet': (40, 120),
            'Insurance': (80, 500),
            'Groceries': (50, 250),
            'Gas': (25, 80),
            'Shopping': (20, 200),
            'Entertainment': (15, 100),
            'Dining Out': (15, 150),
            'Amazon': (10, 200),
            'Healthcare': (20, 300),
            'Other': (10, 150)
        }
        
        # Get the year and month for date generation
        year = current_month['year']
        month = current_month['month']
        
        # Generate 10 random expenses
        cursor = conn.cursor()
        for _ in range(10):
            # Select a random expense type
            expense_type = random.choice(expense_types)
            expense_type_name = expense_type['name']
            expense_type_id = expense_type['id']
            
            # Generate a random day (1-25 for safety)
            day = random.randint(1, 25)
            
            # Create the date string in YYYY-MM-DD format
            date_str = f"{year}-{month:02d}-{day:02d}"
            
            # Get a random amount based on expense type
            min_amount, max_amount = expense_amounts.get(expense_type_name, (10, 100))
            # Generate a random amount with 2 decimal places
            amount = round(random.uniform(min_amount, max_amount), 2)
            
            # Get a random description based on expense type
            descriptions = expense_descriptions.get(expense_type_name, ['Expense'])
            description = random.choice(descriptions)
            
            # Insert the expense into the database
            cursor.execute('''
                INSERT INTO expenses (amount, description, expense_type_id, date, is_recurring_template, recurring_interval, recurring_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (amount, description, expense_type_id, date_str, False, 'none', None))
        
        # Add specific recurring expenses as requested
        # 1. Internet - $90 monthly
        internet_type_id = None
        for expense_type in expense_types:
            if expense_type['name'] == 'Internet':
                internet_type_id = expense_type['id']
                break
        
        if internet_type_id:
            # Create the date string in YYYY-MM-DD format for the 1st of the month
            date_str = f"{year}-{month:02d}-01"
            cursor.execute('''
                INSERT INTO expenses (amount, description, expense_type_id, date, is_recurring_template, recurring_interval, recurring_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (90.00, 'Internet', internet_type_id, date_str, True, 'monthly', 1))
        
        # 2. Car Insurance - $550 monthly
        insurance_type_id = None
        for expense_type in expense_types:
            if expense_type['name'] == 'Car Insurance':
                insurance_type_id = expense_type['id']
                break
        
        if insurance_type_id:
            # Create the date string in YYYY-MM-DD format for the 5th of the month
            date_str = f"{year}-{month:02d}-05"
            cursor.execute('''
                INSERT INTO expenses (amount, description, expense_type_id, date, is_recurring_template, recurring_interval, recurring_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (550.00, 'Car Insurance', insurance_type_id, date_str, True, 'monthly', 5))
        
        # 3. Amazon - $105 yearly
        amazon_type_id = None
        for expense_type in expense_types:
            if expense_type['name'] == 'Amazon':
                amazon_type_id = expense_type['id']
                break
        
        if amazon_type_id:
            # Create the date string in YYYY-MM-DD format for the 15th of the month
            date_str = f"{year}-{month:02d}-15"
            cursor.execute('''
                INSERT INTO expenses (amount, description, expense_type_id, date, is_recurring_template, recurring_interval, recurring_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (105.00, 'Amazon Prime Subscription', amazon_type_id, date_str, True, 'yearly', 15))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Successfully generated sample expenses and recurring expenses for the selected month!'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error seeding data: {str(e)}'}), 500

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
