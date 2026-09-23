# Database initialization

Run commands from the existing project root. Install dependencies first:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create a local `.env` (ignored by Git), using the database server credentials:

```dotenv
DB_HOST=localhost
DB_PORT=3307
DB_NAME=VehicleSalesDB
DB_USER=root
DB_PASSWORD=
SECRET_KEY=replace-with-a-long-random-value
```

An empty password is accepted for a locally configured development server. Do not use shared/root development credentials in production. Explicit process environment variables override `.env` values.

Initialize the database, all ten tables, and development data:

```powershell
.\.venv\Scripts\python.exe database/setup.py
```

**The database does not need to exist.** Setup connects without a database, then executes the `CREATE DATABASE IF NOT EXISTS`, `USE`, and table statements in `schema.sql`. The configured account needs database/table creation privileges. `DB_NAME` is validated before replacing the default identifier in the project-owned SQL file. MySQL 8.0.16+ is the target. This project uses the local MySQL 8 server on port 3307, not XAMPP MariaDB on 3306.

Optional separate steps:

```powershell
.\.venv\Scripts\python.exe database/setup.py --schema-only
.\.venv\Scripts\python.exe database/seed.py
```

Tables use InnoDB and utf8mb4. Money uses DECIMAL. Unique constraints cover usernames, vehicle codes, non-null VIN/plates, sale codes/vehicles, invoice numbers/sales. Foreign keys restrict deletion of history. Stock quantities preserve the existing signed-delta UI (+1/-1/0).

`schema.sql` is additive initialization, not an automatic migration engine. Existing incompatible tables need a deliberate migration; setup does not drop or silently rewrite them. MySQL DDL commits implicitly: a failed schema import may leave earlier tables created, and it can be rerun. Seed records are committed together or rolled back together.

## Editable sample records

Edit the clearly marked lists at the top of `seed.py`. It supplies three roles/users, 20 vehicles, 12 fictional customers, eight completed sales with derived invoices and stock-out records, plus stock-in history and adjustments. Existing SVG placeholders need no manual upload. Relative date offsets apply at first insertion; reruns do not move dates.

Development logins: `katsrieng` (Admin), `sopanha` (Manager), `sovanara` (Sales Staff). Development-only password: `Ignite1234`. Passwords are hashed with Werkzeug before insertion.

Normal seeding skips existing users/customers/vehicles/sales by stable unique codes and usernames. It preserves existing passwords and grandonets; deleting a role's permission in the application will not be undone by rerunning the seed. Foreign key IDs are looked up, not assumed. A conflict rolls back the seed rather than replacing business history. Import `seed.sql` only into the selected application database; the Python commands select it automatically.

To intentionally rebuild development records after editing the sample definitions:

```powershell
.\.venv\Scripts\python.exe database/seed.py --reset
```

**Destructive:** this deletes ALL records in the configured database, not only sample records. It asks you to type the exact database name before proceeding. Run it only against a disposable development database. It does not delete runtime image files and does not reset numeric ID counters. No reset is executed by normal setup or Flask startup.

## Flask integration

The Flask factory uses `MySQLRepository` exclusively. `.env` is loaded automatically; server environment variables take precedence. Application startup never creates, seeds or resets a database. Run setup explicitly before starting Flask. Database rows and relative photo paths persist across process restarts; back up both MySQL and `app/static/uploads/vehicles/`.

Integration tests opt in with `RUN_MYSQL_TESTS=1`. They connect only to MySQL 8 on port 3307, create randomly named `autovault_test_*` databases and drop only those databases. The account needs CREATE/DROP database privileges for this test strategy. Never point tests at a production server.
