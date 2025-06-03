from flask import Blueprint, request, redirect, url_for, render_template, flash, session
import sqlite3
import os
from datetime import datetime

# Create a Blueprint for expense-related routes
expense_routes = Blueprint('expense_routes', __name__)

# Database configuration
DB_NAME = 'spending_tracker.db'
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DB_NAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_recurring_expenses_for_month(conn, month_id, month, year):
    """
    Get recurring expenses that should appear in the specified month.
    This checks all active recurring expenses and determines which ones should appear
    in the given month based on their recurring_interval.
    
    Args:
        conn: Database connection
        month_id: ID of the month record
        month: Month number (1-12)
        year: Year (e.g., 2025)
        
    Returns:
        List of recurring expense dictionaries that should appear in this month
    """
    # Get all active recurring expenses that are templates
    recurring_expenses = conn.execute("""
        SELECT id, amount, description, date, expense_type_id, recurring_interval, recurring_day
        FROM expenses
        WHERE is_active = 1 AND recurring_interval != 'none' AND is_recurring_template = TRUE
    """).fetchall()
    
    # List to store recurring expenses for this month
    month_recurring_expenses = []
    
    # Calculate the target date for the month
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    # Calculate start and end dates for the current month
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    for expense in recurring_expenses:
        # Get the original expense date
        original_date = datetime.strptime(expense['date'], '%Y-%m-%d').date()
        expense_id = expense['id']
        recurring_interval = expense['recurring_interval']
        recurring_day = expense['recurring_day']
        
        # Skip if the original expense was created in the current month
        # This prevents duplicate entries in the month the recurring expense was created
        original_date_str = original_date.strftime('%Y-%m-%d')
        if original_date_str >= start_date and original_date_str < end_date:
            continue
        
        # Determine if this recurring expense should be included in this month
        should_include = False
        new_expense_date = None
        
        if recurring_interval == 'monthly':
            # Monthly expenses recur every month on the specified day
            should_include = True
            
            # Use the recurring_day if specified, otherwise use the day from the original date
            day_to_use = int(recurring_day) if recurring_day is not None else original_date.day
            
            # Make sure the day is valid for the month (e.g., no February 30)
            last_day_of_month = (date(year, month, 1) + relativedelta(months=1, days=-1)).day
            day_to_use = min(day_to_use, last_day_of_month)
            
            new_expense_date = date(year, month, day_to_use)
            
        elif recurring_interval == 'biannual':
            # Biannual expenses recur every 6 months
            # Calculate months difference between original date and target date
            months_diff = (year - original_date.year) * 12 + (month - original_date.month)
            should_include = months_diff % 6 == 0
            
            if should_include:
                # Use the same day of the month if possible
                day_to_use = min(original_date.day, (date(year, month, 1) + relativedelta(months=1, days=-1)).day)
                new_expense_date = date(year, month, day_to_use)
            
        elif recurring_interval == 'yearly':
            # Yearly expenses recur every 12 months
            # Check if month and day match (same month every year)
            should_include = month == original_date.month
            
            if should_include:
                # Use the same day of the month if possible
                day_to_use = min(original_date.day, (date(year, month, 1) + relativedelta(months=1, days=-1)).day)
                new_expense_date = date(year, month, day_to_use)
        
        # If this expense should be included in this month, add it to the list
        if should_include and new_expense_date:
            # Format the date as string
            new_date_str = new_expense_date.strftime('%Y-%m-%d')
            
            # Get expense type name
            expense_type = conn.execute('SELECT name FROM expense_types WHERE id = ?', (expense['expense_type_id'],)).fetchone()
            expense_type_name = expense_type['name'] if expense_type else 'Unknown'
            
            # Create a dictionary with expense details
            recurring_expense = {
                'id': expense['id'],
                'amount': expense['amount'],
                'description': expense['description'],
                'date': new_date_str,
                'expense_type_id': expense['expense_type_id'],
                'expense_type_name': expense_type_name,
                'recurring_interval': recurring_interval,
                'recurring_day': recurring_day,
                'is_recurring_instance': True  # Flag to indicate this is a recurring instance
            }
            
            month_recurring_expenses.append(recurring_expense)
    
    return month_recurring_expenses

@expense_routes.route('/view', methods=['GET'])
def view_expenses():
    """View expenses for a specific month"""
    conn = get_db_connection()
    
    # Get month_id from query parameters, session, or default to most recent month
    month_id = request.args.get('month_id', None)
    
    # If month_id is provided in the request, update the session
    if month_id:
        session['current_month_id'] = month_id
    # Otherwise try to get it from the session
    elif 'current_month_id' in session:
        month_id = session['current_month_id']
    
    # If still no month_id, get the most recent month
    if not month_id:
        current_month = conn.execute('SELECT id FROM months ORDER BY year DESC, month DESC LIMIT 1').fetchone()
        if current_month:
            month_id = current_month['id']
            # Store in session
            session['current_month_id'] = month_id
    
    # Get month details
    month_data = None
    if month_id:
        month_data = conn.execute('SELECT * FROM months WHERE id = ?', (month_id,)).fetchone()
    
    # If no month found, redirect to index
    if not month_data:
        conn.close()
        return redirect(url_for('index'))
    
    # Get all expense types for filtering
    expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
    
    # Get filter parameters
    expense_type_filter = request.args.get('expense_type_id', 'all')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Show 10 expenses per page
    
    # Build the query based on filters
    query = '''
        SELECT e.id, e.amount, e.description, e.date, e.recurring_interval, e.recurring_day,
               et.name as expense_type_name, et.id as expense_type_id
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_active = TRUE
    '''
    
    # Build the count query to get total number of expenses
    count_query = '''
        SELECT COUNT(*) as total
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_active = TRUE
    '''
    
    query_params = []
    
    # Add date range filter for the selected month
    start_date = f"{month_data['year']}-{month_data['month']:02d}-01"
    
    # Calculate end date based on month/year
    if month_data['month'] == 12:
        end_date = f"{month_data['year'] + 1}-01-01"
    else:
        end_date = f"{month_data['year']}-{month_data['month'] + 1:02d}-01"
    
    query += " AND e.date >= ? AND e.date < ?"
    count_query += " AND e.date >= ? AND e.date < ?"
    query_params.extend([start_date, end_date])
    
    # Add expense type filter if specified
    if expense_type_filter != 'all':
        query += " AND e.expense_type_id = ?"
        count_query += " AND e.expense_type_id = ?"
        query_params.append(expense_type_filter)
    
    # Add sorting
    if sort_by == 'amount':
        query += f" ORDER BY e.amount {sort_order}"
    elif sort_by == 'expense_type':
        query += f" ORDER BY et.name {sort_order}"
    else:  # Default to date
        query += f" ORDER BY e.date {sort_order}"
    
    # Get total count of expenses matching the filter
    total_count_result = conn.execute(count_query, query_params).fetchone()
    total_count = total_count_result['total'] if total_count_result else 0
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
    
    # Ensure page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Add pagination
    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    
    # Execute the query
    expenses = conn.execute(query, query_params).fetchall()
    
    # Get all expenses for chart data and total amount calculation
    # We need all expenses for the chart, not just the paginated ones
    chart_query = query.replace(f" LIMIT {per_page} OFFSET {offset}", "")
    all_expenses = conn.execute(chart_query, query_params).fetchall()
    
    # Get recurring expenses for this month
    recurring_expenses = get_recurring_expenses_for_month(
        conn, 
        month_id, 
        month_data['month'], 
        month_data['year']
    )
    
    # Add recurring expenses to the list of expenses
    # Note: These are not stored in the database yet, just calculated on-the-fly
    all_expenses = list(all_expenses) + recurring_expenses
    
    # For pagination, we need to handle the combined list
    # Sort the combined list according to the sort criteria
    if sort_by == 'amount':
        all_expenses.sort(key=lambda x: x['amount'], reverse=(sort_order == 'desc'))
    elif sort_by == 'expense_type':
        all_expenses.sort(key=lambda x: x['expense_type_name'], reverse=(sort_order == 'desc'))
    else:  # Default to date
        all_expenses.sort(key=lambda x: x['date'], reverse=(sort_order == 'desc'))
    
    # Apply expense type filter to the combined list if needed
    if expense_type_filter != 'all':
        all_expenses = [e for e in all_expenses if str(e['expense_type_id']) == str(expense_type_filter)]
    
    # Update total count for pagination
    total_count = len(all_expenses)
    
    # Calculate total pages based on the new count
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
    
    # Ensure page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Apply pagination to the combined list
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    expenses = all_expenses[start_idx:end_idx] if start_idx < len(all_expenses) else []
    
    # Calculate total amount for filtered expenses (using all expenses, not just paginated ones)
    total_amount = sum(expense['amount'] for expense in all_expenses)
    
    # Get all available months for the month selector
    all_months = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC').fetchall()
    
    conn.close()
    
    return render_template('view_expenses.html', 
                          expenses=expenses,
                          all_expenses=all_expenses,  # For chart data
                          month_data=month_data,
                          expense_types=expense_types,
                          all_months=all_months,
                          expense_type_filter=expense_type_filter,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          total_amount=total_amount,
                          page=page,
                          per_page=per_page,
                          total_pages=total_pages)

@expense_routes.route('/edit', methods=['POST'])
def edit_expense():
    """Edit an existing expense"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Get form data
        expense_id = request.form.get('expense_id')
        month_id = request.form.get('month_id')
        amount = request.form.get('amount')
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
        
        # Basic validation
        if not expense_id or not amount or not expense_type_id or not date:
            # Get month details for redirect
            month_data = conn.execute('SELECT * FROM months WHERE id = ?', (month_id,)).fetchone()
            expense_types = conn.execute('SELECT * FROM expense_types WHERE is_active = TRUE ORDER BY name').fetchall()
            all_months = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC').fetchall()
            
            # Get expenses for the current month to redisplay
            start_date = f"{month_data['year']}-{month_data['month']:02d}-01"
            
            # Calculate end date based on month/year
            if month_data['month'] == 12:
                end_date = f"{month_data['year'] + 1}-01-01"
            else:
                end_date = f"{month_data['year']}-{month_data['month'] + 1:02d}-01"
            
            expenses = conn.execute('''
                SELECT e.id, e.amount, e.description, e.date, e.is_recurring, e.recurring_day,
                       et.name as expense_type_name, et.id as expense_type_id
                FROM expenses e
                JOIN expense_types et ON e.expense_type_id = et.id
                WHERE e.is_active = TRUE AND e.date >= ? AND e.date < ?
                ORDER BY e.date DESC
            ''', (start_date, end_date)).fetchall()
            
            total_amount = sum(expense['amount'] for expense in expenses)
            
            conn.close()
            return render_template('view_expenses.html',
                                  expenses=expenses,
                                  month_data=month_data,
                                  expense_types=expense_types,
                                  all_months=all_months,
                                  expense_type_filter='all',
                                  sort_by='date',
                                  sort_order='desc',
                                  total_amount=total_amount,
                                  edit_error='Missing required fields')
        
        try:
            # Update the expense in the database
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE expenses
                SET amount = ?, description = ?, expense_type_id = ?, date = ?, recurring_interval = ?, recurring_day = ?
                WHERE id = ?
            ''', (amount, description, expense_type_id, date, recurring_interval, recurring_day, expense_id))
            conn.commit()
            flash('Expense updated successfully', 'success')
        except sqlite3.Error as e:
            # Handle database error
            conn.rollback()
            flash(f'Error updating expense: {str(e)}', 'danger')
        finally:
            conn.close()
        
        # Redirect back to view expenses page with the same month
        return redirect(url_for('expense_routes.view_expenses', month_id=month_id))
    
    # If not POST, redirect to view expenses
    conn.close()
    return redirect(url_for('expense_routes.view_expenses'))

@expense_routes.route('/delete', methods=['POST'])
def delete_expense():
    """Delete an existing expense"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Get form data
        expense_id = request.form.get('expense_id')
        month_id = request.form.get('month_id')
        
        # Basic validation
        if not expense_id:
            flash('Missing expense ID', 'danger')
            conn.close()
            return redirect(url_for('expense_routes.view_expenses', month_id=month_id))
        
        try:
            # Instead of actually deleting the record, we set is_active to FALSE
            # This is a soft delete approach that preserves data for potential future recovery
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE expenses
                SET is_active = FALSE
                WHERE id = ?
            ''', (expense_id,))
            conn.commit()
            flash('Expense deleted successfully', 'success')
        except sqlite3.Error as e:
            # Handle database error
            conn.rollback()
            flash(f'Error deleting expense: {str(e)}', 'danger')
        finally:
            conn.close()
        
        # Redirect back to view expenses page with the same month
        return redirect(url_for('expense_routes.view_expenses', month_id=month_id))
    
    # If not POST, redirect to view expenses
    conn.close()
    return redirect(url_for('expense_routes.view_expenses'))
