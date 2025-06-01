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
    
    # Build the query based on filters
    query = '''
        SELECT e.id, e.amount, e.description, e.date, e.is_recurring, e.recurring_day,
               et.name as expense_type_name, et.id as expense_type_id
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
    query_params.extend([start_date, end_date])
    
    # Add expense type filter if specified
    if expense_type_filter != 'all':
        query += " AND e.expense_type_id = ?"
        query_params.append(expense_type_filter)
    
    # Add sorting
    if sort_by == 'amount':
        query += f" ORDER BY e.amount {sort_order}"
    elif sort_by == 'expense_type':
        query += f" ORDER BY et.name {sort_order}"
    else:  # Default to date
        query += f" ORDER BY e.date {sort_order}"
    
    # Execute the query
    expenses = conn.execute(query, query_params).fetchall()
    
    # Calculate total amount for filtered expenses
    total_amount = sum(expense['amount'] for expense in expenses)
    
    # Get all available months for the month selector
    all_months = conn.execute('SELECT * FROM months ORDER BY year DESC, month DESC').fetchall()
    
    conn.close()
    
    return render_template('view_expenses.html', 
                          expenses=expenses,
                          month_data=month_data,
                          expense_types=expense_types,
                          all_months=all_months,
                          expense_type_filter=expense_type_filter,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          total_amount=total_amount)

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
        is_recurring = 'is_recurring' in request.form
        recurring_day = request.form.get('recurring_day') if is_recurring else None
        
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
                SET amount = ?, description = ?, expense_type_id = ?, date = ?, is_recurring = ?, recurring_day = ?
                WHERE id = ?
            ''', (amount, description, expense_type_id, date, is_recurring, recurring_day, expense_id))
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
