# Database Schema

This document details the database schema for the application, which is built on a multi-tenant architecture using PostgreSQL.

## 1. Multi-Tenant Architecture: Schema per Tenant

The database is structured to support multiple tenants, ensuring that each tenant's data is isolated in its own schema.

- **Shared Schema (`shared`):** Contains tables that are accessible across the entire application and manage the tenants themselves.
- **Tenant-Specific Schemas (e.g., `tenant_1`, `tenant_2`):** Each tenant has a dedicated schema that contains a complete set of application tables. The name of this schema is dynamically generated and linked to the tenant's record in the `shared.tenants` table.

--- 

## 2. Shared Schema (`shared`)

These tables are central to the multi-tenant setup.

### `tenants`

Stores the master record for each tenant.

| Column           | Type        | Description                                                 |
| ---------------- | ----------- | ----------------------------------------------------------- |
| `id`             | `Integer`   | **Primary Key:** Unique identifier for the tenant.          |
| `tenant_key`     | `String`    | A unique key for identifying the tenant.                    |
| `schema_name`    | `String`    | The name of the PostgreSQL schema for this tenant.          |
| `company_name`   | `String`    | The name of the tenant's company.                           |
| `industry`       | `String`    | The industry the tenant operates in.                        |
| `locations`      | `JSON`      | A JSON object storing location data.                        |
| `plan_type`      | `String`    | The subscription plan type for the tenant.                  |
| `use_multilocations` | `Boolean`   | Flag to indicate if the tenant uses multiple locations.   |

### `tenant_owners`

Stores users who have ownership or administrative access to a tenant.

| Column       | Type        | Description                                                       |
| ------------ | ----------- | ----------------------------------------------------------------- |
| `id`         | `Integer`   | **Primary Key:** Unique identifier for the owner record.          |
| `tenant_id`  | `Integer`   | **Foreign Key:** References `shared.tenants.id`.                |
| `email`      | `String`    | The email address of the owner.                                   |
| `first_name` | `String`    | The first name of the owner.                                      |
| `last_name`  | `String`    | The last name of the owner.                                       |
| `role`       | `String`    | The role of the owner within the tenant (e.g., 'admin').          |

--- 

## 3. Tenant-Specific Schema (e.g., `tenant_1`)

These tables exist within *each* tenant's dedicated schema.

### `users`

Stores user accounts for a specific tenant.

| Column          | Type        | Description                                                       |
| --------------- | ----------- | ----------------------------------------------------------------- |
| `id`            | `Integer`   | **Primary Key:** Unique identifier for the user.                  |
| `username`      | `String`    | The user's login username.                                        |
| `password_hash` | `String`    | The hashed password for the user.                                 |

### `assets`

Stores financial assets for the tenant.

| Column        | Type        | Description                                               |
| ------------- | ----------- | --------------------------------------------------------- |
| `id`          | `Integer`   | **Primary Key:** Unique identifier for the asset.         |
| `description` | `String`    | Description of the asset (e.g., 'Cash', 'Equipment').     |
| `amount`      | `Float`     | The value of the asset.                                   |
| `user_id`     | `Integer`   | **Foreign Key:** References `users.id`.                   |

### `liabilities`

Stores financial liabilities for the tenant.

| Column        | Type        | Description                                                  |
| ------------- | ----------- | ------------------------------------------------------------ |
| `id`          | `Integer`   | **Primary Key:** Unique identifier for the liability.        |
| `description` | `String`    | Description of the liability (e.g., 'Bank Loan').            |
| `amount`      | `Float`     | The value of the liability.                                  |
| `user_id`     | `Integer`   | **Foreign Key:** References `users.id`.                      |

### `expenses`

Stores operating expenses for the tenant.

| Column      | Type        | Description                                                    |
| ----------- | ----------- | -------------------------------------------------------------- |
| `id`        | `Integer`   | **Primary Key:** Unique identifier for the expense.          |
| `item`      | `String`    | The name of the expense item (e.g., 'Rent', 'Salaries').     |
| `amount`    | `Float`     | The cost of the expense.                                       |
| `frequency` | `String`    | The frequency of the expense (e.g., 'monthly', 'quarterly'). |
| `user_id`   | `Integer`   | **Foreign Key:** References `users.id`.                        |

### `products`

Stores product or service details for the tenant.

| Column            | Type        | Description                                                    |
| ----------------- | ----------- | -------------------------------------------------------------- |
| `id`              | `Integer`   | **Primary Key:** Unique identifier for the product.          |
| `description`     | `String`    | Description of the product or service.                         |
| `price`           | `Float`     | The selling price of the product.                              |
| `sales_volume`    | `Integer`   | The number of units sold.                                      |
| `sales_volume_unit` | `String`    | The unit of time for the sales volume (e.g., 'monthly').     |
| `user_id`         | `Integer`   | **Foreign Key:** References `users.id`.                        |

### `financial_params`

Stores key financial parameters and assumptions for the tenant's forecasts.

| Column                   | Type        | Description                                                               |
| ------------------------ | ----------- | ------------------------------------------------------------------------- |
| `id`                     | `Integer`   | **Primary Key:** Unique identifier.                                       |
| `cogs_percentage`        | `Float`     | Cost of Goods Sold as a percentage of revenue.                            |
| `loan_amount`            | `Float`     | The principal amount of a potential loan.                                 |
| `loan_interest_rate`     | `Float`     | The annual interest rate for the loan.                                    |
| `loan_term`              | `Integer`   | The term of the loan in years.                                            |
| `seasonality`            | `JSON`      | A JSON object with monthly multipliers to model sales seasonality.        |
| `user_id`                | `Integer`   | **Foreign Key:** References `users.id`.                                   |

### `business_startup_activities`

Tracks the progress of key business startup activities.

| Column        | Type        | Description                                                  |
| ------------- | ----------- | ------------------------------------------------------------ |
| `id`          | `Integer`   | **Primary Key:** Unique identifier for the activity.         |
| `activity`    | `String`    | The name of the startup activity.                            |
| `description` | `String`    | A brief description of the activity.                         |
| `weight`      | `Integer`   | The relative importance of the activity (as a percentage).     |
| `progress`    | `Integer`   | The completion progress of the activity (0-100).             |
| `user_id`     | `Integer`   | **Foreign Key:** References `users.id`.                      |

