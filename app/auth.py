import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user

from .models import Tenant, User, Expense, Asset, Liability, FinancialParams, BusinessStartupActivity, Product
from .extensions import db
from . import oauth

bp = Blueprint('auth', __name__, url_prefix='/')

@bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.intro'))
    return render_template('login.html')

@bp.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@bp.route('/login/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token)

    user = User.query.filter_by(username=user_info['email']).first()

    if not user:
        # Create a new tenant for the new user
        new_tenant = Tenant(name=f"{user_info['name']}'s Team")
        db.session.add(new_tenant)
        db.session.commit()

        new_user = User(
            username=user_info['email'],
            password_hash=generate_password_hash(user_info['sub'], method='pbkdf2:sha256'),
            tenant_id=new_tenant.id
        )
        db.session.add(new_user)
        db.session.commit()

        _seed_initial_user_data(new_user.id, new_tenant.id)

        user = new_user

    login_user(user, remember=True)
    return redirect(url_for('main.intro'))


def _seed_initial_user_data(user_id, tenant_id):
    """Seeds the database with a default set of data for a new user."""
    try:
        with current_app.open_resource('../startup_activities.json') as f:
            initial_activities_data = json.load(f)
        
        initial_activities = [BusinessStartupActivity(**item, user_id=user_id, tenant_id=tenant_id) for item in initial_activities_data]

        initial_expenses = [
            Expense(item='Rent/Lease', amount=1200.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id),
            Expense(item='Salaries and Wages', amount=5000.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id),
            Expense(item='Utilities (Electricity, Water, Internet)', amount=400.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id),
            Expense(item='Marketing and Advertising', amount=600.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id),
            Expense(item='Software & Subscriptions', amount=150.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id),
            Expense(item='Insurance', amount=200.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id),
            Expense(item='Legal & Accounting', amount=250.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id),
            Expense(item='Office Supplies', amount=100.0, frequency='monthly', user_id=user_id, tenant_id=tenant_id)
        ]
        initial_products = [Product(description='', price=0.0, sales_volume=0, sales_volume_unit='monthly', user_id=user_id, tenant_id=tenant_id) for _ in range(4)]
        initial_assets = [
            Asset(description='Cash & Equivalents', amount=10000.0, user_id=user_id, tenant_id=tenant_id),
            Asset(description='Inventory', amount=5000.0, user_id=user_id, tenant_id=tenant_id),
            Asset(description='Equipment', amount=35000.0, user_id=user_id, tenant_id=tenant_id)
        ]
        initial_liabilities = [
            Liability(description='Credit Card Debt', amount=5000.0, user_id=user_id, tenant_id=tenant_id),
            Liability(description='Bank Loan', amount=20000.0, user_id=user_id, tenant_id=tenant_id)
        ]

        db.session.add(FinancialParams(user_id=user_id, tenant_id=tenant_id))
        db.session.add_all(initial_activities)
        db.session.add_all(initial_expenses)
        db.session.add_all(initial_products)
        db.session.add_all(initial_assets)
        db.session.add_all(initial_liabilities)
        db.session.commit()
        current_app.logger.info(f"Successfully seeded initial data for new user {user_id}.")
    except Exception as e:
        current_app.logger.error(f"Failed to seed initial data for new user {user_id}: {e}")
        db.session.rollback()

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
