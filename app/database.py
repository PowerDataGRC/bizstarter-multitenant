import json
import os
from .extensions import db
from .models import AssessmentMessage, Tenant, TenantOwner

def get_assessment_messages():
    """Retrieves all assessment messages from the database using SQLAlchemy."""
    messages = {}
    rows = AssessmentMessage.query.all()
    for row in rows:
        messages[row.risk_level] = {
            'status': row.status,
            'caption': row.caption,
            'status_class': row.status_class,
            'dscr_status': row.dscr_status
        }
    return messages

def create_tenant(tenant_key, schema_name, company_name, industry, locations, plan_type, use_multilocations):
    """Creates a new tenant."""
    tenant = Tenant(
        tenant_key=tenant_key,
        schema_name=schema_name,
        company_name=company_name,
        industry=industry,
        locations=locations,
        plan_type=plan_type,
        use_multilocations=use_multilocations
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant

def get_tenant_by_key(tenant_key):
    """Retrieves a tenant by their key."""
    return Tenant.query.filter_by(tenant_key=tenant_key).first()

def create_tenant_owner(tenant, email, first_name, last_name, role):
    """Creates a new tenant owner."""
    owner = TenantOwner(
        tenant=tenant,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role
    )
    db.session.add(owner)
    db.session.commit()
    return owner

def get_tenant_owner_by_email(email):
    """Retrievis a tenant owner by their email."""
    return TenantOwner.query.filter_by(email=email).first()
