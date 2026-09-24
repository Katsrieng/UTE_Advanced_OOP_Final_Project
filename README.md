# IGNITE

**Vehicle Inventory and Sales Management System for SMEs** — Advanced Object-Oriented Programming university project.

Flask, Jinja, responsive CSS and vanilla JavaScript with **MySQL persistence**. Vehicles, photo paths, customers, users, permissions, stock movements, sales and invoices survive application restarts. No ORM, frontend framework or build process is required.

## Windows setup

Prerequisites: Python 3.11+ and MySQL 8.0.16+ (verified with MySQL 8.0.46). This computer uses **localhost:3307**, database **VehicleSalesDB**, user **root**. Do not use XAMPP MariaDB on port 3306.

Run from the project directory containing `app.py`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Fresh clone only: do not overwrite an existing .env.
Copy-Item .env.example .env
```

Edit local `.env`: set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` and a random `SECRET_KEY`. The password belongs only in this ignored file. Generate a session secret with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Paste that generated value into `SECRET_KEY`, then initialize and run:

```powershell
.\.venv\Scripts\python.exe database/setup.py
.\.venv\Scripts\python.exe app.py
```

Open [IGNITE](http://127.0.0.1:5000). The local server binds to loopback with debug disabled. To use the verification port instead:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5002
```

**The database does not need to exist.** Setup connects to MySQL without selecting a database and applies `database/schema.sql`, including `CREATE DATABASE IF NOT EXISTS`, before seeding. The setup account needs CREATE/table privileges. `.env` loads automatically; explicit process environment variables take precedence. Startup never creates, seeds or resets records.

`SECRET_KEY` is required. `SESSION_COOKIE_SECURE=1` enables HTTPS-only cookies when deployed behind HTTPS; leave it unset for local HTTP. Cookies are HttpOnly and SameSite=Lax. See [database setup](database/README.md) for schema-only, seed-only and guarded development reset commands.

## Development data and accounts

Fresh seeding creates 20 vehicles, 12 fictional customers, three users/roles, eight completed sales, eight invoices and 31 stock movements. Records include available/reserved/sold/inactive vehicles and sales across several months. Generic local SVG illustrations require no uploads.

| Username | Role | Development-only password |
| --- | --- | --- |
| `katsrieng` | Admin | `autovault-demo` |
| `sopanha` | Manager | `autovault-demo` |
| `sovanara` | Sales Staff | `autovault-demo` |

Passwords are hashed before database insertion. New accounts require their own password. Sample definitions are centralized in the clearly marked lists at the top of `database/seed.py`; role/permission lookup data is in `database/seed.sql`. Rerunning setup preserves existing records, passwords and edited grants. Inconsistent existing sample sales cause a clear conflict error and roll back the seed. No automatic startup reset exists. The local verification also leaves clearly named `VERIFY-*` vehicle/customer records and their completed sale.

## Application behavior

- Dashboard and reports use SQL counts, sums, status breakdowns and monthly aggregation. Reports support Today, 7 Days, 30 Days and Custom. Inventory is a current snapshot; the chart shows the last six calendar months within the selected period.
- Vehicles and customers support creation, details, editing, search, filtering, pagination and deactivation. Historical records are retained. Vehicle registration establishes its initial status; explicit Inventory movements record later stock transitions and notes. Sold vehicle identity/price/status are protected.
- Inventory supports STOCK_IN (inactive to available), STOCK_OUT (to inactive) and ADJUSTMENT (note without status change). Signed quantities remain +1, -1 and 0 to preserve the existing UI.
- Sales lock the active user, customer and available vehicle inside one MySQL transaction. Sale creation, SOLD status, STOCK_OUT and exactly one invoice commit together. Failure rolls back all writes; row locks and unique constraints prevent double sales.
- Invoices retain Decimal amounts and the existing printable layout. The invoice remains a development document, without configured taxes or dealership legal details.
- Users support password hashing, role assignment and activation. Authorization joins active users, roles and permissions on every request. The schema supports multiple roles and combines their permissions; the existing account editor assigns one role. Admin grants, self-demotion and removal of the last active administrator are protected.
- Forms keep submitted values on validation errors. CSRF, server-side permission checks, parameterized SQL, constrained fields and database uniqueness/FKs provide validation boundaries. Database outages return a friendly 503 without raw SQL or credentials.

The topbar search searches vehicles. Notifications retain their empty state. New sales complete immediately; pending/cancelled filters are present but no cancellation workflow is implemented.

## Vehicle photos

Create/edit supports optional JPEG, PNG and WebP up to 5 MB and 20 million pixels. Images are decoded, checked against their extensions, oriented, resized to fit 1920 × 1920 and re-encoded without metadata; animated files are rejected. Preview, cancel selection, replacement, confirmed removal and fallback illustrations retain their existing UI.

Generated UUID filenames live under `app/static/uploads/vehicles/`; MySQL stores only the relative `image_path`. No-upload edits preserve the old photo. Old files are removed only **after database commit**, if no other vehicle references them. Failed writes clean up new files when safe. Uncertain/failed cleanup is logged and may require maintenance. Bundled illustrations and paths outside the upload directory cannot be deleted by photo cleanup.

Uploads are publicly served static assets and excluded from Git. Back up both the database and upload directory. A process crash between filesystem and database operations can leave an orphan file; no automatic orphan sweep is provided.

## Architecture

```text
app.py                              Local entry point
config.py                           Environment/session/photo configuration
app/database.py                     Connections and shared transactions
app/models/                         User, Role, Permission, Vehicle, Customer,
                                    Sale, StockMovement, Invoice, money rules
app/repositories/base.py            Shared SQL CRUD and record mapping
app/repositories/*_repository.py    Entity queries and report aggregation
app/repositories/mysql.py           Repository collection, joins and pagination
app/services/*_service.py           Authentication, users, vehicles, customers,
                                    inventory, sales, reports and photo lifecycle
app/routes/__init__.py              Register the existing web blueprint
app/routes/*_routes.py              Feature request handlers
app/routes/shared_routes.py         Existing resource URL dispatch
app/routes/form_helpers.py          Shared form parsing and validation
app/routes/resource_config.py       Existing form fields and table metadata
app/routes/common.py                Request access checks, CSRF and navigation
app/templates/                      Existing Jinja templates (unchanged)
app/static/                         Existing CSS, JS and assets (unchanged)
database/                           Explicit schema and seed commands
tests/                              Application, photo and MySQL regression tests
```

Routes parse requests and call services; services coordinate business operations
through repositories. Repositories own SQL and map results through explicit domain
dataclasses back to the existing template dictionaries. The `MySQLRepository`
collection shares one `Database` transaction across participating repositories.

The shared listing, form and details routes preserve all `web.*` endpoint names,
URL paths, template fields and error messages. Feature modules handle their own
save operations and detail context without duplicating the common forms. No image
entity or association class is needed: photos remain paths on vehicles, and role
associations remain repository-managed joins.

Sales retain the same row locks and atomic sale/stock/invoice transaction. Vehicle
photo cleanup still happens after commit. Authentication, permissions and all
frontend files are unchanged. Compatibility names used in browser storage, demo
passwords, test database prefixes and seed locks are deliberately retained.

## Tests

Run the complete suite against the local MySQL 8 server on port 3307:

```powershell
$env:RUN_MYSQL_TESTS='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Each database test creates a unique `autovault_test_*` database and drops only that database. The account needs CREATE/DROP database privileges. Tests refuse other ports and non-MySQL-8 servers. Without the opt-in flag, live database tests are **skipped**, not verified.

Coverage includes routes/assets, login/CSRF/RBAC, CRUD, filtering/pagination, inactive records, unique fields, SQL-injection-shaped input, exact Decimal totals, stock transitions, concurrent double-sale attempts, transaction rollback, seed repeat/conflicts, photo validation/lifecycle/commit failure and fresh-app persistence.

See [implementation and verification report](docs/mysql-integration-report.md) for actual results and remaining limitations. This is a university development application: production deployment would additionally require a WSGI server, HTTPS, restricted database account, login rate limiting, backup/restore procedures and immutable invoice identity snapshots.

## IGNITE branding

The supplied transparent logo is `app/static/images/branding/ignite-logo.png`. It appears in the sidebar, login, invoice and favicon. The collapsed/tablet navigation rail uses a compact I; mobile login has its own small wordmark.

Internal `autovault-theme`/`autovault-sidebar` keys and their JavaScript helper remain for saved-preference compatibility. The development password, database-test prefix, connection context/seed-lock names and existing repository folder also retain their old internal names; changing branding does not reset accounts, preferences or database records. See [branding verification](docs/ignite-branding.md).
