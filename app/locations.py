from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app.models import db, Tenant, Location

locations_bp = Blueprint('locations', __name__, url_prefix='/locations')

@locations_bp.route('/')
@login_required
def list_locations():
    tenant = Tenant.query.filter_by(tenant_key=current_user.username).first()
    if not tenant or not tenant.use_multilocations:
        flash('Multi-location feature is not enabled for your account.', 'warning')
        return redirect(url_for('main.index'))
    locations = Location.query.filter_by(tenant_id=tenant.tenant_id).all()
    return render_template('locations.html', locations=locations)

@locations_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_location():
    tenant = Tenant.query.filter_by(tenant_key=current_user.username).first()
    if not tenant or not tenant.use_multilocations:
        flash('Multi-location feature is not enabled for your account.', 'warning')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        
        new_location = Location(
            tenant_id=tenant.tenant_id,
            name=name,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code
        )
        db.session.add(new_location)
        db.session.commit()
        flash('Location added successfully!', 'success')
        return redirect(url_for('locations.list_locations'))
    
    return render_template('location_form.html', title='Add Location', form_url=url_for('locations.add_location'))

@locations_bp.route('/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    tenant = Tenant.query.filter_by(tenant_key=current_user.username).first()

    if location.tenant_id != tenant.tenant_id:
        flash('You are not authorized to edit this location.', 'danger')
        return redirect(url_for('locations.list_locations'))

    if request.method == 'POST':
        location.name = request.form['name']
        location.address = request.form['address']
        location.city = request.form['city']
        location.state = request.form['state']
        location.zip_code = request.form['zip_code']
        db.session.commit()
        flash('Location updated successfully!', 'success')
        return redirect(url_for('locations.list_locations'))

    return render_template('location_form.html', title='Edit Location', location=location, form_url=url_for('locations.edit_location', location_id=location.id))

@locations_bp.route('/<int:location_id>/delete', methods=['POST'])
@login_required
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    tenant = Tenant.query.filter_by(tenant_key=current_user.username).first()

    if location.tenant_id != tenant.tenant_id:
        flash('You are not authorized to delete this location.', 'danger')
        return redirect(url_for('locations.list_locations'))

    db.session.delete(location)
    db.session.commit()
    flash('Location deleted successfully!', 'success')
    return redirect(url_for('locations.list_locations'))
