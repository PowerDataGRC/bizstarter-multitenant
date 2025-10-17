import json
from flask import current_app
from .extensions import db
from .models import User, Product, Expense, Asset, Liability, FinancialParams

from logic.profitability import calculate_profitability
from logic.financial_ratios import calculate_key_ratios

def get_product_and_expense_data(tenant_id):
    """
    Fetches product and expense data for a tenant.
    """
    products = Product.query.filter_by(tenant_id=tenant_id).all()
    expenses = Expense.query.filter_by(tenant_id=tenant_id).all()
    financial_params = FinancialParams.query.filter_by(tenant_id=tenant_id).first()

    products_dict = [p.to_dict() for p in products]
    expenses_dict = [e.to_dict() for e in expenses]
    company_name = financial_params.company_name if financial_params else ''
    return products_dict, expenses_dict, company_name

def save_product_and_expense_data(user_id, tenant_id, data):
    """Saves product, expense, and company name data for a tenant."""
    # Sets of submitted descriptions and items
    submitted_product_descriptions = {p_data.get('description') for p_data in data.get('products', []) if p_data.get('description')}
    submitted_expense_items = {e_data.get('item') for e_data in data.get('expenses', []) if e_data.get('item')}

    # Delete products no longer in the submitted data for the whole tenant
    Product.query.filter(
        Product.tenant_id == tenant_id,
        ~Product.description.in_(submitted_product_descriptions)
    ).delete(synchronize_session=False)

    # Delete expenses no longer in the submitted data for the whole tenant
    Expense.query.filter(
        Expense.tenant_id == tenant_id,
        ~Expense.item.in_(submitted_expense_items)
    ).delete(synchronize_session=False)

    # Get existing products and expenses for the tenant
    existing_products = {p.description: p for p in Product.query.filter_by(tenant_id=tenant_id).all()}
    existing_expenses = {e.item: e for e in Expense.query.filter_by(tenant_id=tenant_id).all()}

    # Process products
    for p_data in data.get('products', []):
        description = p_data.get('description')
        if not description:
            continue
        try:
            price = float(p_data.get('price', 0) or 0)
            sales_volume = int(p_data.get('sales_volume', 0) or 0)
            sales_volume_unit = p_data.get('sales_volume_unit', 'monthly')

            if description in existing_products:
                product = existing_products[description]
                product.price = price
                product.sales_volume = sales_volume
                product.sales_volume_unit = sales_volume_unit
            else:
                product = Product(
                    description=description, price=price, sales_volume=sales_volume,
                    sales_volume_unit=sales_volume_unit, user_id=user_id, tenant_id=tenant_id
                )
                db.session.add(product)
        except (ValueError, TypeError):
            continue

    # Process expenses
    for e_data in data.get('expenses', []):
        item = e_data.get('item')
        if not item:
            continue
        try:
            amount = float(e_data.get('amount', 0) or 0)
            frequency = e_data.get('frequency', 'monthly')

            if item in existing_expenses:
                expense = existing_expenses[item]
                expense.amount = amount
                expense.frequency = frequency
            else:
                expense = Expense(
                    item=item, amount=amount, frequency=frequency, user_id=user_id, tenant_id=tenant_id
                )
                db.session.add(expense)
        except (ValueError, TypeError):
            continue

    financial_params = FinancialParams.query.filter_by(tenant_id=tenant_id).first()
    if not financial_params:
        financial_params = FinancialParams(user_id=user_id, tenant_id=tenant_id)
        db.session.add(financial_params)
    
    financial_params.company_name = data.get('company_name', '')
    db.session.commit()

def get_or_recalculate_forecast(user, tenant_id, data=None):
    """
    Calculates a financial forecast for a tenant. If data is provided, it updates 
    parameters before recalculating. Otherwise, it uses existing parameters.
    """
    params = FinancialParams.query.filter_by(tenant_id=tenant_id).first()
    if not params:
        params = FinancialParams(user_id=user.id, tenant_id=tenant_id)
        db.session.add(params)

    # Fetch all data by tenant_id
    products_q = Product.query.filter_by(tenant_id=tenant_id).all()
    products = [p.to_dict() for p in products_q]
    
    assets_q = Asset.query.filter_by(tenant_id=tenant_id).all()
    liabilities_q = Liability.query.filter_by(tenant_id=tenant_id).all()

    if data:  # Recalculating with new data
        params.cogs_percentage = float(data.get('cogs_percentage'))
        params.tax_rate = float(data.get('tax_rate'))
        params.seasonality = json.dumps([float(v) for v in data.get('seasonality', [1.0] * 12)])
        params.current_assets = float(data.get('current_assets'))
        params.current_liabilities = float(data.get('current_liabilities'))
        params.interest_expense = float(data.get('interest_expense'))
        params.depreciation = float(data.get('depreciation'))
        params.annual_operating_expenses = float(data.get('annual_operating_expenses'))
    
    annual_op_ex = params.annual_operating_expenses or 0

    forecast = calculate_profitability(
        products=products, cogs_percentage=params.cogs_percentage,
        annual_operating_expenses=annual_op_ex, tax_rate=params.tax_rate,
        seasonality_factors=json.loads(params.seasonality)
    )

    total_assets = sum(a.amount for a in assets_q)
    total_debt = sum(l.amount for l in liabilities_q)
    net_operating_income = forecast['annual']['gross_profit'] - annual_op_ex

    annual_ratios = calculate_key_ratios(
        net_profit=forecast['annual']['net_profit'], total_revenue=forecast['annual']['revenue'],
        total_assets=total_assets, current_assets=params.current_assets,
        current_liabilities=params.current_liabilities, total_debt=total_debt,
        net_operating_income=net_operating_income, interest_expense=params.interest_expense,
        depreciation=params.depreciation
    )
    forecast['annual'].update(annual_ratios)
    forecast['quarterly'].update(annual_ratios)

    # Persist key results
    params.total_annual_revenue = forecast['annual']['revenue']
    params.annual_net_profit = forecast['annual']['net_profit']
    params.quarterly_net_profit = forecast['quarterly']['net_profit']
    params.net_operating_income = net_operating_income
    db.session.commit()

    return forecast
