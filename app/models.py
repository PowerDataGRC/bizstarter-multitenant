from app.extensions import db
from flask_login import UserMixin
from typing import Any, Dict
from sqlalchemy import inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationships
    products: Mapped[list["Product"]] = relationship('Product', backref='user', lazy=True, cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship('Expense', backref='user', lazy=True, cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship('Asset', backref='user', lazy=True, cascade="all, delete-orphan")
    liabilities: Mapped[list["Liability"]] = relationship('Liability', backref='user', lazy=True, cascade="all, delete-orphan")
    financial_params: Mapped["FinancialParams"] = relationship('FinancialParams', backref='user', uselist=False, cascade="all, delete-orphan")

    startup_activities: Mapped[list["BusinessStartupActivity"]] = relationship('BusinessStartupActivity', backref='user', lazy=True, cascade="all, delete-orphan")

    def __init__(self, username: str, password_hash: str):
        self.username = username
        self.password_hash = password_hash

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    sales_volume = db.Column(db.Integer, nullable=False, default=0)
    sales_volume_unit = db.Column(db.String(20), nullable=False, default='monthly')
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'))

    def __init__(self, description, price, sales_volume, sales_volume_unit, user_id):
        self.description = description
        self.price = price
        self.sales_volume = sales_volume
        self.sales_volume_unit = sales_volume_unit
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        insp = inspect(self)
        if insp is None:
            return {} # pragma: no cover
        return {c.key: getattr(self, c.key) for c in insp.mapper.column_attrs}

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    frequency = db.Column(db.String(20), nullable=False, default='monthly')
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'))

    def __init__(self, item, amount, frequency, user_id):
        self.item = item
        self.amount = amount
        self.frequency = frequency
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        insp = inspect(self)
        if insp is None:
            return {} # pragma: no cover
        return {c.key: getattr(self, c.key) for c in insp.mapper.column_attrs}

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'))

    def __init__(self, description, amount, user_id):
        self.description = description
        self.amount = amount
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        insp = inspect(self)
        if insp is None:
            return {} # pragma: no cover
        return {c.key: getattr(self, c.key) for c in insp.mapper.column_attrs}

class Liability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'))

    def __init__(self, description, amount, user_id):
        self.description = description
        self.amount = amount
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        insp = inspect(self)
        if insp is None:
            return {} # pragma: no cover
        return {c.key: getattr(self, c.key) for c in insp.mapper.column_attrs}

class FinancialParams(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'), unique=True)
    
    company_name = db.Column(db.String(100), default='')
    cogs_percentage = db.Column(db.Float, default=35.0)
    tax_rate = db.Column(db.Float, default=8.0)
    seasonality = db.Column(db.Text, default=json.dumps([1.0] * 12))
    
    # Balance Sheet / Ratios
    current_assets = db.Column(db.Float, nullable=False, default=15000.0)
    current_liabilities = db.Column(db.Float, nullable=False, default=8000.0)
    interest_expense = db.Column(db.Float, nullable=False, default=2000.0)
    depreciation = db.Column(db.Float, nullable=False, default=3000.0)

    # Calculated values for loan calculator
    quarterly_net_profit = db.Column(db.Float, default=0.0)
    annual_net_profit = db.Column(db.Float, default=0.0)
    total_annual_revenue = db.Column(db.Float, default=0.0)
    net_operating_income = db.Column(db.Float, default=0.0)
    annual_operating_expenses = db.Column(db.Float, default=0.0)

    # Loan details could also be stored here if it's a one-to-one relationship
    loan_amount = db.Column(db.Float, nullable=True)
    loan_interest_rate = db.Column(db.Float, nullable=True)
    loan_term = db.Column(db.Integer, nullable=True)
    loan_monthly_payment = db.Column(db.Float, nullable=True)
    loan_schedule = db.Column(db.Text, nullable=True)

    def __init__(self, user_id):
        self.user_id = user_id

class AssessmentMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    risk_level = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.Text, nullable=False)
    status_class = db.Column(db.String(50), nullable=False)
    dscr_status = db.Column(db.Text, nullable=False)

    def __init__(self, risk_level, status, caption, status_class, dscr_status):
        self.risk_level = risk_level
        self.status = status
        self.caption = caption
        self.status_class = status_class
        self.dscr_status = dscr_status

class BusinessStartupActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    progress = db.Column(db.Integer, nullable=False, default=0)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('user.id'))

    def __init__(self, activity, description, weight, progress, user_id):
        self.activity = activity
        self.description = description
        self.weight = weight
        self.progress = progress
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        insp = inspect(self)
        if insp is None:
            return {} # pragma: no cover
        return {c.key: getattr(self, c.key) for c in insp.mapper.column_attrs}

    def __repr__(self):
        return f'<Activity {self.activity}>'

class Tenant(db.Model):
    __tablename__ = 'tenants'
    __table_args__ = {'schema': 'shared'}

    tenant_id = db.Column(db.Integer, primary_key=True)
    tenant_key = db.Column(db.String(255), unique=True, nullable=False)
    schema_name = db.Column(db.String(255), unique=True, nullable=False)
    company_name = db.Column(db.String(255))
    industry = db.Column(db.String(255))
    plan_type = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    use_multilocations = db.Column(db.Boolean, default=False)

    owners = relationship("TenantOwner", back_populates="tenant")
    locations = relationship("Location", back_populates="tenant", cascade="all, delete-orphan")

class TenantOwner(db.Model):
    __tablename__ = 'tenant_owners'
    __table_args__ = {'schema': 'shared'}

    owner_id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('shared.tenants.tenant_id'))
    email = db.Column(db.String(255), unique=True, nullable=False)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    role = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    tenant = relationship("Tenant", back_populates="owners")

class Location(db.Model):
    __tablename__ = 'locations'
    __table_args__ = {'schema': 'shared'}

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('shared.tenants.tenant_id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))

    tenant = relationship("Tenant", back_populates="locations")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code
        }
