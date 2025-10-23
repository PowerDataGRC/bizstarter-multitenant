from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from .models import Tenant, TenantOwner, User, Location
from .database import create_tenant_owner, get_tenant_by_key, get_tenant_owner_by_email
from .extensions import db

bp = Blueprint('registration', __name__, url_prefix='/register')

@bp.route('/', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        company_name = request.form['company_name']
        email_address = request.form['email_address']
        username = request.form['username']
        password = request.form['password']
        use_multilocations = 'use_multilocations' in request.form
        location_names = request.form.getlist('locations')

        error = None

        if not company_name:
            error = 'Company name is required.'
        elif not email_address:
            error = 'Email address is required.'
        elif not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        
        if get_tenant_owner_by_email(email_address) is not None:
            error = f"Email {email_address} is already registered."

        if error is None:
            try:
                # Create a new tenant
                tenant = Tenant(
                    tenant_key=company_name.lower().replace(' ', '_'),
                    schema_name=company_name.lower().replace(' ', '_'),
                    company_name=company_name,
                    industry='', # Add industry if available in the form
                    plan_type='standard', # Or get from form
                    use_multilocations=use_multilocations
                )
                db.session.add(tenant)
                db.session.flush() # Flush to get the tenant_id

                if use_multilocations and location_names:
                    for name in location_names:
                        if name.strip():
                            location = Location(tenant_id=tenant.tenant_id, name=name.strip())
                            db.session.add(location)

                # Create a new tenant owner
                owner = create_tenant_owner(
                    tenant=tenant,
                    email=email_address,
                    first_name='', # Add first name if available in the form
                    last_name='', # Add last name if available in the form
                    role='admin'
                )

                # Create a new user
                user = User(username=username, password_hash=generate_password_hash(password))
                db.session.add(user)
                db.session.commit()
                
                flash('Registration successful. Please log in.')
                return redirect(url_for('auth.login'))
            except Exception as e:
                error = f"Error during registration: {e}"
                db.session.rollback()

        flash(error)

    return render_template('register.html')
