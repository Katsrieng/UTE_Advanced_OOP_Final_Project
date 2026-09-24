# IGNITE branding

Visible application branding uses IGNITE. The logo is stored at
`app/static/images/branding/ignite-logo.png` and used by the sidebar, login,
invoices and favicon.

Internal identifiers use `ignite-theme`, `ignite-sidebar`, `igniteStorage`,
`ignite_connection`, the `ignite_test_*` database prefix and the `ignite_` seed-lock
prefix. Browser preferences stored under previous keys are not read; users can
save their theme and sidebar preferences again. Accounts and database records
are unaffected by these internal renames.

Legacy sample identifier patterns remain in the migration utility and its tests
because older databases may still need conversion. They are not branding for
new records. See the [database instructions](../database/README.md).

For current test commands, see the [project README](../README.md). Test results
and counts should come from a fresh run rather than this branding document.
