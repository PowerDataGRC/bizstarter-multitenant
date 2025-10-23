# Application Architecture

This document outlines the architecture of the Flask web application.

## 1. Core Technologies

- **Backend:** Python 3 with the Flask micro-framework.
- **Database:** PostgreSQL is used for the database, with SQLAlchemy acting as the Object-Relational Mapper (ORM).
- **Frontend:** Server-side rendered HTML using the Jinja2 templating engine.
- **Environment:** The application is designed to run in a Nix-based environment, with dependencies managed by `requirements.txt` and a Python virtual environment.

## 2. Project Structure

The application follows a modular structure, leveraging Flask Blueprints to organize features into distinct components.

```
/
|-- app/
|   |-- __init__.py             # Application factory
|   |-- auth.py                 # Authentication routes (login, register)
|   |-- main_routes.py          # Core application routes
|   |-- models.py               # SQLAlchemy database models
|   |-- services.py             # Business logic
|   |-- database.py             # Database utility functions
|   |-- extensions.py           # Flask extension initializations
|   |-- db/
|   |   |-- *.json              # JSON files for initial data seeding
|-- logic/
|   |-- financial_ratios.py     # Financial calculation logic
|   |-- loan.py                 # Loan calculation logic
|-- migrations/                 # Alembic database migration scripts
|-- static/                     # Static assets (CSS, JS, images)
|-- templates/                  # Jinja2 HTML templates
|-- utils/
|   |-- export.py               # Utilities for data export (e.g., Excel)
|-- .env                        # Environment variables (for secrets)
|-- requirements.txt            # Python dependencies
|-- devserver.sh                # Script to run the development server
```

### Key Architectural Patterns

- **Application Factory:** The `app/__init__.py` file uses the application factory pattern (`create_app`) to instantiate the Flask application. This is crucial for creating different app instances for testing, development, and production with varied configurations.
- **Blueprints:** The application is divided into Blueprints (`auth`, `main`) to keep the codebase organized, modular, and scalable. Each blueprint encapsulates a specific feature set with its own routes and views.
- **Secrets Management:** Following security best practices, sensitive information like the `SECRET_KEY` and database URI are managed via environment variables loaded from a `.env` file using `python-dotenv`.

## 3. Database Architecture

The application employs a **Multi-Tenant Architecture** using a **Schema per Tenant** model.

- **Shared Schema:** A `shared` schema contains data common to the entire application.
  - `tenants`: A master table that acts as a directory for all tenants, storing metadata like `company_name` and the unique `schema_name` for each tenant.
  - `tenant_owners`: Stores users who have administrative privileges over tenants.

- **Tenant-Specific Schemas:** For each tenant record in `shared.tenants`, a dedicated schema (e.g., `tenant_1`, `tenant_2`) is created. This schema contains a complete set of tables (`user`, `asset`, `expense`, etc.) that are isolated to that specific tenant.

- **Data Isolation:** This model ensures strong data isolation, as queries only run against the tables within the current tenant's schema. The application logic switches the active PostgreSQL schema based on the logged-in user's tenant.

- **ORM:** SQLAlchemy is used to map Python model classes in `app/models.py` to database tables. Database schema changes are managed via Alembic in the `migrations/` directory.

## 4. Reporting and Data Access

For reporting that spans multiple tenants, the application logic performs the following steps:
1.  Queries the `shared.tenants` table to get a list of schema names.
2.  Dynamically constructs SQL queries (often using `UNION ALL`) to fetch and aggregate data from the same table across different tenant schemas.
