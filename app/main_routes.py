import json
from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash, g, current_app
from typing import Any, Dict
from sqlalchemy import update, delete
from flask_login import login_required, current_user

from .extensions import db
from .models import FinancialParams, Asset, Liability, BusinessStartupActivity, Product, Expense
from logic.loan import calculate_loan_schedule
from logic.financial_ratios import calculate_dscr
from utils.export import create_forecast_spreadsheet
from .database import get_assessment_messages
from . import services

bp = Blueprint('main', __name__, url_prefix='/')

_assessment_messages_cache = None

@bp.before_app_request
def before_request():
    global _assessment_messages_cache
    if _assessment_messages_cache is None:
        try:
            current_app.logger.info("Populating assessment messages cache...")
            _assessment_messages_cache = get_assessment_messages() or {}
        except Exception as e:
            current_app.logger.error(f"Failed to load assessment messages from DB: {e}")
            db.session.rollback()
            _assessment_messages_cache = {}
    g.assessment_messages = _assessment_messages_cache

@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.intro'))
    return redirect(url_for('auth.login'))

@bp.route("/intro")
@login_required
def intro():
    return render_template('intro.html')

@bp.route("/library")
@login_required
def library():
    return render_template('library.html')

@bp.route('/startup-activities', methods=['GET', 'POST'])
@login_required
def startup_activities():
    tenant_id = current_user.tenant_id
    if request.method == 'POST':
        form_ids = request.form.getlist('id')
        form_activities = request.form.getlist('activity')
        form_descriptions = request.form.getlist('description')
        form_weights = request.form.getlist('weight')
        form_progresses = request.form.getlist('progress')

        total_weight = sum(int(w) for w in form_weights if w.isdigit())
        if total_weight > 100:
            flash(f'Total weight cannot exceed 100%. Current: {total_weight}%.', 'danger')
            activities_for_template = [{
                'id': form_ids[i], 'activity': form_activities[i], 'description': form_descriptions[i],
                'weight': form_weights[i], 'progress': form_progresses[i]
            } for i in range(len(form_activities))]
            return render_template('startup_activities.html', activities=activities_for_template, total_weight=total_weight), 400

        existing_activities = {str(act.id): act for act in BusinessStartupActivity.query.filter_by(tenant_id=tenant_id).all()}
        
        for i in range(len(form_activities)):
            activity_id = form_ids[i]
            activity_data = {
                'activity': form_activities[i].strip(), 'description': form_descriptions[i].strip(),
                'weight': int(form_weights[i]), 'progress': int(form_progresses[i]),
                'user_id': current_user.id, 'tenant_id': tenant_id
            }
            if activity_id in existing_activities:
                stmt = update(BusinessStartupActivity).where(BusinessStartupActivity.id == activity_id).values(**activity_data)
                db.session.execute(stmt)
            elif activity_data['activity']:
                db.session.add(BusinessStartupActivity(**activity_data))

        db.session.commit()
        flash('Startup activities updated!', 'success')
        return redirect(url_for('main.product_detail'))

    activities = BusinessStartupActivity.query.filter_by(tenant_id=tenant_id).order_by(BusinessStartupActivity.id).all()
    
    try:
        with current_app.open_resource('../startup_activities.json') as f:
            default_activities_count = len(json.load(f))
    except Exception:
        default_activities_count = 10

    if 0 < len(activities) < default_activities_count:
        current_app.logger.info(f"Tenant {tenant_id} has an incomplete activity list. Re-seeding.")
        BusinessStartupActivity.query.filter_by(tenant_id=tenant_id).delete()
        activities = []

    if not activities:
        try:
            with current_app.open_resource('../startup_activities.json') as f:
                initial_activities_data = json.load(f)
            new_activities = [BusinessStartupActivity(**item, user_id=current_user.id, tenant_id=tenant_id) for item in initial_activities_data]
            db.session.add_all(new_activities)
            db.session.commit()
            flash('We\'ve added a default list of startup activities to get you started.', 'info')
            activities = new_activities
        except Exception as e:
            current_app.logger.error(f"Failed to seed startup activities for tenant {tenant_id}: {e}")
            flash('Could not load default startup activities.', 'danger')

    total_weight = sum(act.weight for act in activities)
    return render_template('startup_activities.html', activities=activities, total_weight=total_weight)

@bp.route("/product-detail", methods=["GET"])
@login_required
def product_detail():
    products, expenses, company_name = services.get_product_and_expense_data(current_user.tenant_id)
    page_data = {
        "products": products, "expenses": expenses, "company_name": company_name,
        "save_url": url_for('main.save_product_details'),
        "continue_url": url_for('main.financial_forecast')
    }
    return render_template('product-detail.html', page_data=page_data)

@bp.route("/save-product-details", methods=["POST"])
@login_required
def save_product_details():
    data = request.get_json()
    services.save_product_and_expense_data(current_user.id, current_user.tenant_id, data)
    return jsonify({'status': 'success'})

@bp.route("/financial-forecast", methods=["GET"])
@login_required
def financial_forecast():
    tenant_id = current_user.tenant_id
    financial_params = FinancialParams.query.filter_by(tenant_id=tenant_id).first()
    if not financial_params:
        flash('Financial parameters not found. Please visit Product Detail page first.', 'warning')
        return redirect(url_for('main.product_detail'))

    assets = [a.to_dict() for a in Asset.query.filter_by(tenant_id=tenant_id).all()]
    liabilities = [l.to_dict() for l in Liability.query.filter_by(tenant_id=tenant_id).all()]
    operating_expenses = [e.to_dict() for e in Expense.query.filter_by(tenant_id=tenant_id).all()]
    financial_params.annual_operating_expenses = sum((e['amount'] * 12 if e['frequency'] == 'monthly' else e['amount'] * 4) for e in operating_expenses)

    forecast = services.get_or_recalculate_forecast(current_user, tenant_id)

    return render_template('financial-forecast.html', forecast=forecast, assets=assets, liabilities=liabilities, financial_params=financial_params)

@bp.route("/recalculate-forecast", methods=["POST"])
@login_required
def recalculate_forecast():
    data = request.get_json()
    tenant_id = current_user.tenant_id
    user_id = current_user.id

    db.session.execute(delete(Asset).where(Asset.tenant_id == tenant_id))
    for item in data.get('assets', []):
        if item.get('description'):
            db.session.add(Asset(description=item['description'], amount=float(item.get('amount', 0) or 0), user_id=user_id, tenant_id=tenant_id))

    db.session.execute(delete(Liability).where(Liability.tenant_id == tenant_id))
    for item in data.get('liabilities', []):
        if item.get('description'):
            db.session.add(Liability(description=item['description'], amount=float(item.get('amount', 0) or 0), user_id=user_id, tenant_id=tenant_id))
    
    db.session.commit()
    forecast = services.get_or_recalculate_forecast(current_user, tenant_id, data)
    return jsonify(forecast)

@bp.route("/loan-calculator", methods=['GET', 'POST'])
@login_required
def loan_calculator():
    tenant_id = current_user.tenant_id
    params = FinancialParams.query.filter_by(tenant_id=tenant_id).first()
    if not params:
        return redirect(url_for('main.financial_forecast'))

    forecast = services.get_or_recalculate_forecast(current_user, tenant_id)
    quarterly_net_profit = params.quarterly_net_profit or 0
    annual_net_profit = params.annual_net_profit or 0
    monthly_net_profit = annual_net_profit / 12 if annual_net_profit else (quarterly_net_profit / 3)
    net_operating_income = params.net_operating_income or 0
    interest_expense = params.interest_expense or 0
    icr = net_operating_income / interest_expense if interest_expense > 0 else 0
    
    assessment, dscr, dscr_status, schedule, monthly_payment = None, 0.0, "", None, None
    form_data = {'loan_amount': params.loan_amount, 'interest_rate': params.loan_interest_rate, 'loan_term': params.loan_term}

    if request.method == 'POST':
        loan_amount = float(request.form.get('loan_amount', '0').replace(',', '') or 0)
        interest_rate = float(request.form.get('interest_rate', 0))
        loan_term = int(request.form.get('loan_term', 0))
        
        form_data = {'loan_amount': loan_amount, 'interest_rate': interest_rate, 'loan_term': loan_term}
        loan_data = calculate_loan_schedule(loan_amount, interest_rate, loan_term)
        monthly_payment = loan_data.get("monthly_payment")
        schedule = loan_data.get("schedule")

        params.loan_amount = loan_amount
        params.loan_interest_rate = interest_rate
        params.loan_term = loan_term
        params.loan_monthly_payment = monthly_payment
        params.loan_schedule = json.dumps(schedule)
        db.session.commit()
        return redirect(url_for('main.loan_calculator'))

    if request.method == 'GET' and params.loan_monthly_payment:
        monthly_payment = params.loan_monthly_payment
        if params.loan_schedule:
            schedule = params.loan_schedule

    if monthly_payment and monthly_payment > 0:
        total_debt_service = monthly_payment * 12
        dscr = calculate_dscr(net_operating_income, total_debt_service)
        risk_level = 'low_risk'
        if dscr < 1.0: risk_level = 'high_risk'
        elif dscr < 1.25: risk_level = 'medium_risk'
        assessment = g.assessment_messages.get(risk_level)
        if assessment:
            dscr_status = assessment.get('dscr_status', '')

    return render_template('loan-calculator.html', 
                           quarterly_net_profit=quarterly_net_profit, annual_net_profit=annual_net_profit,
                           monthly_net_profit=monthly_net_profit, monthly_payment=monthly_payment,
                           form_data=form_data, assessment=assessment, dscr=dscr,
                           dscr_status=dscr_status, schedule=schedule, icr=icr)

@bp.route("/export-forecast")
@login_required
def export_forecast():
    tenant_id = current_user.tenant_id
    params = FinancialParams.query.filter_by(tenant_id=tenant_id).first()
    products = [p.to_dict() for p in Product.query.filter_by(tenant_id=tenant_id).all()]
    operating_expenses = [e.to_dict() for e in Expense.query.filter_by(tenant_id=tenant_id).all()]
    startup_activities = [a.to_dict() for a in BusinessStartupActivity.query.filter_by(tenant_id=tenant_id).all()]
    
    loan_details = {}
    if params:
        loan_details = {
            'loan_amount': params.loan_amount, 'interest_rate': params.loan_interest_rate,
            'loan_term': params.loan_term, 'monthly_payment': params.loan_monthly_payment,
            'schedule': json.loads(params.loan_schedule) if params.loan_schedule else None,
        }

    spreadsheet_file = create_forecast_spreadsheet(
        products, operating_expenses, params.cogs_percentage if params else 0, 
        loan_details, json.loads(params.seasonality) if params and params.seasonality else [1.0]*12, 
        params.company_name if params else '', params.depreciation if params else 0, 
        params.interest_expense if params else 0, startup_activities
    )

    return send_file(
        spreadsheet_file, as_attachment=True, download_name='financial_forecast.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
