# IGNITE MySQL integration

The application uses MySQL repositories with separate models, services and routes.
Setup, credentials and full test commands are documented in the [project README](../README.md)
and [database README](../database/README.md).

## Verification

Run the complete suite with `RUN_MYSQL_TESTS=1`. Tests use disposable `ignite_test_*`
databases on MySQL 8, port 3307. Without that flag, integration tests are skipped.
Use the current test output for counts and results rather than historical totals.

Coverage includes authentication, RBAC, persistent CRUD, vehicle photos, stock
transitions, Decimal totals, sale/invoice atomicity, concurrent double-sale
protection, rollback, seed idempotency, identifier migration and restart persistence.

## Remaining limitations

- Physical printing requires verification in the target browser/printer environment.
- Invoices read current related records rather than immutable identity snapshots.
- The single-role editor replaces assignments, although authorization supports multiple roles.
- Schema setup is additive, not a migration engine for incompatible existing tables.
- Back up MySQL and uploaded photos together.
- Production deployment needs a WSGI server, HTTPS, a restricted database account,
  login rate limiting and tested backup/restore procedures.

The legacy identifier migration remains necessary for databases containing old
sample identifiers. Follow the database README before reseeding such databases.
