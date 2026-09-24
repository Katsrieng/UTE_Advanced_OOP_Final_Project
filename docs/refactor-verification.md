# Refactor verification — 2026-09-24

- Split eight domain records, entity repositories, services, and feature request handlers. Shared resource URLs retain their existing dispatch and endpoint names.
- Removed the combined model/repository `entities.py` files, `routes/web.py`, and old service filenames after updating all imports and test patch targets.
- Full MySQL regression suite: **47 passed, 0 failed, 0 skipped** after the model/repository phase, service phase, route phase, and final cleanup. Final run: 88.035 seconds.
- Ruff import/error checks and formatting check passed for all 64 Python files; `git diff --check` passed. Existing test assertions and database setup/seed executable statements are unchanged apart from import/patch paths.
- Integration verification used fresh `autovault_test_*` databases and temporary photo storage. A temporary loopback forwarding process exposed the local MySQL 8.0.46 server on port 3307 for the unchanged test safety guard. The application remains configured for port 3306. Photo tests ran outside the Windows sandbox because temporary directory access was denied inside it.
- Browser verification used a separate seeded database: login, dashboard, vehicles, customers, inventory, sales wizard, sale completion, SOLD status, stock-out history, invoice, reports, users, roles, dark/light themes, photo selection/preview/save/replacement/removal, mobile navigation, and logout.
- Template/static/schema fingerprints and route paths, methods, and endpoint names match the pre-refactor snapshot exactly.
- Application tables were not written by refactor verification. A concurrent live edit changed user 2 to `sokpanha` and reassigned its role during work; that edit was preserved. Other tables matched the initial snapshot. All ten tables matched a fresh snapshot across the final Flask restart.
- Compatibility storage keys, demo passwords, seed locks, and test database prefixes intentionally retain their existing names. Earlier documents describe historical implementations and may mention old module paths.

Future test runs still require the existing MySQL 8 / port 3307 test environment (or equivalent local forwarding). No application behavior change is intended.
