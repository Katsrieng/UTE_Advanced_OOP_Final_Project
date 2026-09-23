# IGNITE MySQL migration: audit and proposed design

Date: 2026-09-23
Status: proposed; application code unchanged.

## Scope and working copy

Work in the existing autovault-github-upload repository at its current root layout. Preserve the existing frontend, URLs, form names, theme, responsive styles, and vehicle-photo implementation. GitHub currently uses a vehicle_sales_system subdirectory; publication must preserve that layout and remote history. Preserve the existing local README edit.

Deliver all ten requested database tables, persistent application workflows, hashed authentication, database RBAC, deterministic editable development seeds, automated tests, browser verification, and teammate setup instructions. No Assistant role, ORM, second application, or automatic startup seeding.

## Audit findings

- app.py runs create_app; config.py supplies a development secret and no database configuration. .env.example contains only SECRET_KEY and dotenv is not loaded.
- The application factory always constructs DemoRepository. Its all/get/save methods expose mutable dictionary references, and its RLock only protects one Python process.
- web.py owns authentication, authorization, validation, list filtering, joins, report calculations, inventory state changes, and role updates. All pages consume dictionaries, not domain model methods.
- Authentication compares against one shared plaintext password. Authorization uses a single role string and an in-memory role-to-permission dictionary.
- SalesService uses Decimal briefly but converts persisted amounts to float. It generates numbers from list length, directly mutates vehicle status, and cannot roll back a partially completed operation.
- Inventory form handling also mutates vehicle dictionaries directly. Staff references are display names rather than foreign keys.
- VehiclePhotoService already validates and re-encodes images, generates safe relative paths, preserves placeholders, handles partial write failures, and removes files only after repository.save returns. A SQL adapter must make that return mean the database commit succeeded, or move cleanup explicitly outside the transaction.
- Template fields include id/code/name/date/price/image, nested customer/vehicle dictionaries, and signed movement quantities (+1/-1/0). Retain these display contracts while mapping SQL column names.
- Existing vehicle details require mileage and fuel; retain these columns alongside the requested vehicle fields.
- List pages currently fetch and filter everything in Python; details enrichment causes repeated lookups. Reports need SQL counts, sums, grouped months, and movement counts.
- User forms lack email and password inputs. Add these within the existing form design, never repopulate password values, and never expose password_hash in template context.
- The dashboard chart consumes JSON values; serialize Decimal deliberately at the display boundary without using binary floats for business calculations.
- There are 30 existing tests. Several mutate repo.data or returned dictionary references and assume seeded numeric IDs. Adapt fixtures and assertions to persistent repositories and resolve IDs through stable keys.
- The uploads directory currently contains only .gitkeep. Runtime upload exclusion is already configured.
- No project .env, running database on port 3306, or registered MySQL service was found. MySQL Workbench is installed; XAMPP provides MariaDB 10.4.32, which is not MySQL 8. Exact MySQL verification needs a MySQL server or a separately configured test instance.

## Approach choices

1. Recommended: lightweight MySQL driver, explicit SQL repositories, and a shared transaction context. This fits the current layered project and makes transaction rules visible for the OOP presentation.
2. ORM migration: reduces mapping boilerplate but adds a new persistence abstraction and a larger rewrite than this project needs.
3. Generic SQL adapter behind unchanged routes: smaller initial diff, but leaves business logic, full-table scans, and mutable-record assumptions in routes. Do not use this as the final architecture.

## Proposed architecture

Use mysql-connector-python and python-dotenv. A Database abstraction owns connections, cursor lifetime, and explicit transaction contexts. Repositories participating in a service operation share the same transaction connection; they must not commit independently. Reads release their resources, and failed writes roll back. Database errors are translated into safe domain errors and logged without secrets.

Implement meaningful UserRepository, RoleRepository, PermissionRepository, VehicleRepository, CustomerRepository, StockMovementRepository, SaleRepository, and InvoiceRepository classes. Keep small domain objects for money-bearing records, identity, and authorization. Map database rows into the existing template field contracts at repository/service boundaries. Avoid empty classes or redundant forwarding services.

AuthService handles password verification and safe session identity. UserService coordinates user and role assignment, required password on creation, optional password change on edit, unique username/email checks, self-access protection, and last-active-admin protection. Permission checks union active permissions from every active role through the two join tables. Fetch current authorization per request so administrative changes affect later requests.

VehicleService and CustomerService own validation and history-preserving updates. InventoryService validates actor and vehicle and updates status plus movement atomically. ReportService uses repository SQL aggregation. Routes retain HTTP concerns and existing contexts.

## Schema rules

Use the ten requested tables, InnoDB, utf8mb4, DECIMAL money, server-managed timestamps, foreign keys that restrict deleting business history, and indexes for relations, dates, filters, and searches. Nullable VIN/plate values normalize empty strings to NULL; enforce unique values when provided. Preserve the current required 17-character VIN in the UI.

Use a unique sale vehicle_id for the current one-sale-per-vehicle workflow and a unique invoice sale_id. Support the requested sale statuses but introduce no new pending/cancellation workflow. Check nonnegative prices, discount <= price, total = price - discount, invoice totals, and valid statuses. Movement quantity stays a signed unit delta to preserve the existing physical-vehicle UI, with a check mapping STOCK_IN to 1, STOCK_OUT to -1, and ADJUSTMENT to 0.

Primary UI role selection may remain single-select; database authorization always uses user_roles. Additional roles require rows and assignments, not schema changes. Protect the existing Admin role's critical permissions and the last active administrator.

## Atomic sale and photo workflows

A completed sale starts one transaction, validates the authenticated active user and active customer, locks the vehicle with SELECT FOR UPDATE, rechecks AVAILABLE, validates Decimal price/discount, inserts the sale, marks SOLD, inserts STOCK_OUT, creates exactly one invoice, and commits. Unique constraints backstop concurrency. Use database-generated IDs for readable unique sale/invoice numbers rather than row counts. Any failure rolls back every database change.

Keep the current image validation, preview, storage path, and URL resolver. Save a validated new file, lock/reload the vehicle, persist its new relative image path, and commit before deleting its old unreferenced generated file. Rollback removes only the new file. Removal commits the fallback path before filesystem cleanup. Do not hold an outer route transaction that delays commit past cleanup. A failed cleanup is logged; do not claim filesystem and SQL commit are one atomic operation.

## Development seed design

Maintain database/schema.sql, database/seed.sql, and database/seed.py. Put editable DEMO_USERS, DEMO_CUSTOMERS, DEMO_VEHICLES, and DEMO_SALES lists near the top of seed.py, clearly labeled EDIT SAMPLE DATA HERE.

Seed 3 roles, active permission relationships matching current capabilities, 3-5 hashed users, 20 distinct vehicles, 12 fictional customers, 8 completed sales, 8 derived invoices, initial stock history and adjustments (20+ movements). Resolve foreign keys by usernames and unique codes. Use fixed names/codes/Decimal values and relative date offsets anchored at first insertion so recent reports remain useful without moving old records on reruns.

Normal seeding inserts missing known records and preserves existing records, passwords, permissions, and business changes. Conflicting existing records must produce a clear error rather than silently rewrite business history. Seed sale/invoice/stock-out groups transactionally and validate consistency. Repeat execution must create no duplicates. Never seed on Flask startup.

Provide an explicit development-only reset command with a typed database-name confirmation and guard against unapproved target databases. Reset deletes database records in dependency order; it does not indiscriminately delete uploaded files. Document remaining uploads and intentional cleanup separately.

## Migration sequence

1. Database config, connection/transaction boundary, schema, and repository mapping tests.
2. Reference seeds, user repositories, hashed authentication, and joined RBAC.
3. Persistent vehicles and customers; preserve photo lifecycle across SQL commit.
4. Transactional inventory and history queries.
5. Atomic sales and invoices with rollback and concurrent double-sale tests.
6. SQL-backed list pagination, details, dashboard, and reports.
7. Persistent user/permission administration and frontend copy cleanup.
8. Complete development dataset, repeat/reset tests, documentation, and removal of obsolete runtime demo imports.
9. Full automated suite, direct database inspection, browser workflow, and process-restart persistence check.

## Verification and completion criteria

Tests use an explicitly isolated database, never the normal application database. Cover credentials, inactive accounts, all roles, protected GET/POST routes, injection-shaped inputs, duplicates, Decimal rounding, valid stock transitions, invalid foreign keys, transaction rollback at invoice insertion, two independent simultaneous sale connections, photo commit failure, and safe file cleanup.

Run seed twice and compare counts and relational consistency. Check all 10 tables, sold status, stock-out, one invoice per sale, matching totals, password hashes, and no orphan references. Exercise every existing page and the create vehicle/photo -> create customer -> inventory -> complete sale -> invoice -> dashboard/report workflow. Restart Flask and verify the same new record IDs and photo paths still load. Record which checks used actual MySQL; MariaDB-only checks cannot be reported as MySQL verification.

Update README with exact PowerShell environment/schema/seed/run/test commands, development-only credentials, seed editing/reset behavior, architecture, upload storage, and limitations. Search for obsolete runtime demo imports, plaintext password comparisons, mutable-record persistence, float money, and demo-reset copy before completion.
