
import os
import json
import logging
from dotenv import load_dotenv, find_dotenv
from flask import Flask, current_app
from flask_migrate import Migrate
import click
from alembic.config import Config
from alembic import command
import psycopg2

from .extensions import db, login_manager
from .database import get_assessment_messages


def create_app():
    load_dotenv(find_dotenv(".env"))
    load_dotenv(find_dotenv(".env.development.local"), override=True)
    
    """Create and configure an instance of the Flask application."""
    # The root path of the app is the 'app' directory. The templates are one level up.
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=template_dir,
        static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    )
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Database Configuration ---
    
    is_development = os.environ.get('FLASK_DEBUG') == '1'
    
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://")
        if 'sslmode' not in db_url and not is_development:
            db_url += "?sslmode=require"
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "pool_size": 5,
            "max_overflow": 10,
            "connect_args": {
                "connect_timeout": 30
            }
        }
    else:
        # Local development with SQLite
        db_path = os.path.join(app.instance_path, 'bizstarter.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
    # --- Multi-tenancy Setup ---
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Create the shared schema
        cursor.execute("CREATE SCHEMA IF NOT EXISTS shared;")
        print("Schema 'shared' created successfully or already exists.")

        # Create the tenants table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shared.tenants (
            tenant_id SERIAL PRIMARY KEY,
            tenant_key VARCHAR(255) UNIQUE NOT NULL,
            schema_name VARCHAR(255) UNIQUE NOT NULL,
            company_name VARCHAR(255),
            industry VARCHAR(255),
            locations TEXT,
            plan_type VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            use_multilocations BOOLEAN DEFAULT FALSE
        );
        """)
        print("Table 'shared.tenants' created successfully or already exists.")

        # Create the tenant_owners table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shared.tenant_owners (
            owner_id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES shared.tenants(tenant_id),
            email VARCHAR(255) UNIQUE NOT NULL,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            role VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            is_verified BOOLEAN DEFAULT FALSE
        );
        """)
        print("Table 'shared.tenant_owners' created successfully or already exists.")

        # Commit the changes
        conn.commit()

    except Exception as e:
        print(f"An error occurred during multi-tenancy setup: {e}")

    finally:
        # Close the connection
        if conn is not None:
            conn.close()


    # --- Logging Configuration ---
    if not app.debug and not app.testing:
        # In production, log to stderr.
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Remove the database session at the end of the request or app context."""
        db.session.remove()

    @app.after_request
    def after_request_func(response):
        """Ensure responses aren't cached, useful for development."""
        if app.debug:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers['Cache-Control'] = 'public, max-age=0'
        return response

    # Register custom template filter
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        return json.loads(value)

    # Register Blueprints
    from . import auth
    from . import main_routes
    from . import registration
    from . import locations

    # --- Configure Flask-Login ---
    login_manager.init_app(app)
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth.bp)
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(registration.bp)
    app.register_blueprint(locations.locations_bp)

    # Register CLI commands
    app.cli.add_command(init_db_command)

    return app

def seed_initial_data():
    """Seeds the database with initial data."""
    from .models import AssessmentMessage
    print("Seeding assessment_messages table...")
    try:
        with current_app.open_resource('../assessment_messages.json') as f:
            messages_data = json.load(f)
            for risk_level, data in messages_data.items():
                # Check if a message for this risk level already exists
                existing_message = AssessmentMessage.query.filter_by(risk_level=risk_level).first()
                if not existing_message:
                    print(f"  - Adding message for '{risk_level}'...")
                    message = AssessmentMessage(
                        risk_level=risk_level,
                        status=data['status'],
                        caption=data['caption'],
                        status_class=data['status_class'],
                        dscr_status=data['dscr_status']
                    )
                    db.session.add(message)
            db.session.commit()
            print("Assessment messages seeding complete.")
    except Exception as e:
        print(f"Error seeding assessment messages: {e}")
        db.session.rollback()

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    with current_app.app_context():
        click.echo("Applying database migrations...")
        try:
            migrations_dir = os.path.join(os.path.dirname(current_app.root_path), 'migrations')
            alembic_cfg = Config(os.path.join(migrations_dir, "alembic.ini"))
            alembic_cfg.set_main_option("script_location", migrations_dir)
            alembic_cfg.set_main_option('sqlalchemy.url', current_app.config['SQLALCHEMY_DATABASE_URI'])
            command.upgrade(alembic_cfg, 'head')
            click.echo("Database migrations applied successfully.")
            seed_initial_data()
        except Exception as e:
            click.echo(f"Error applying migrations: {e}", err=True)
