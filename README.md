# AutoVault

**Vehicle Inventory and Sales Management System for SMEs** — a university Advanced Object-Oriented Programming project.

A responsive, dark-first dealership workspace built with Python, Flask, Jinja2, CSS custom properties, and vanilla JavaScript. No frontend framework, build process, external fonts, CDN, or chart dependency is required.

## Run locally

From this directory in PowerShell:

```powershell
# The existing virtual environment already contains Flask.
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. On a fresh machine, install Python 3.11+ and run `python -m venv .venv` first. The server binds only to the local machine and does not enable the debugger.

| Username | Role | Password |
| --- | --- | --- |
| `alex` | Admin | `autovault-demo` |
| `jordan` | Manager | `autovault-demo` |
| `sam` | Sales Staff | `autovault-demo` |

**This is a development demo.** All records, new accounts, and permission edits are held in server memory and reset when the server restarts. The shared password and default secret are for local demonstrations only. `.env.example` documents configuration; `.env` is not automatically loaded. Set `SECRET_KEY` in the environment for a non-default secret.

## Pages and behavior

- **Dashboard:** live demo totals, six-month SVG revenue chart with keyboard-accessible values, available featured vehicle, recent sales, inventory breakdown.
- **Vehicles:** search, brand/status/year filters, pagination, create/edit, details, stock history. Change status through Edit; sold status is assigned by Sales.
- **Customers:** contact search, create/edit, customer profile, purchase history.
- **Sales:** searchable history, customer → available vehicle → review workflow, discount validation, confirmation dialog, success page and sale details.
- **Invoices:** searchable list, white invoice document, Print Invoice with A4 print CSS that removes application navigation.
- **Inventory:** movement history, search/type/date filters, stock in/out and adjustment form.
- **Reports:** Today/7 Days/30 Days/Custom filters, period totals, monthly sales, current inventory and stock movement summary. Inventory is a current snapshot; the chart displays the last six calendar months of selected-period sales.
- **Users:** create/edit, assign a role, activate/deactivate. Historical users are retained. Newly created demo accounts use the shared demo password.
- **Roles & Permissions:** data-driven role selection and editable grouped permissions. Admin permissions and self-demotion are protected in the demo.
- **Login and errors:** password visibility, inline login errors, reusable 403/404/500 screens.

The topbar search currently searches vehicles by name, VIN or code. Notifications show an empty state; there is no notification backend. Amounts are illustrative USD values. The two bundled SVG vehicle illustrations are generic local placeholders, not photographs of the named models. Missing vehicle images fall back to a generic illustration.

## Vehicle photos

Create or edit a vehicle to choose an optional JPG/JPEG, PNG or WebP photo (maximum 5 MB and 20 million pixels). The form previews the selected image before saving; canceling the selection restores the current preview. Saving without a new file preserves the existing photo. **Remove Photo** asks for confirmation and removes only the photo, retaining the vehicle; it requires JavaScript.

Images are decoded and checked against their extension, oriented, resized to fit 1920 � 1920, and re-encoded without metadata. Animated images are rejected. Files use generated UUID names under `app/static/uploads/vehicles/`; only a relative path is stored in the existing `image` field. Uploaded files are ignored by Git; `.gitkeep` retains the directory. These static files are publicly accessible to anyone who can reach the server.

A replacement is saved before the record changes, and the old file is deleted only after a successful save and when no other vehicle references it. Failed saves clean up the newly created file. Cleanup accepts only generated paths inside the vehicle upload directory; bundled SVG illustrations are preserved. Missing photos use the generic illustration across lists, details, dashboard and sale selection.

**Demo persistence:** image files survive server restarts, but the in-memory vehicle records reset, leaving unreferenced uploads. No automatic orphan sweep deletes them. For MySQL, persist the relative image path, commit the record change before deleting the old file, roll back new files on failure, and back up both database and upload storage. Failed filesystem cleanup is logged and may require later maintenance.

## Structure

```text
app.py                         Local development entry point
config.py                      Branding and Flask configuration
app/
  __init__.py                  Application factory, template globals, errors
  models/entities.py           Framework-independent Vehicle dataclass
  repositories/demo.py         Seed data and process-local persistence adapter
  services/vehicle_photos.py   Validated upload, image resolution and safe cleanup
  services/sales.py            Sale invariants and coordinated record creation
  routes/web.py                Routes, validation, authentication and RBAC hooks
  templates/
    base.html                  Shared application shell
    components/                Icons, cards, badges, shell, alerts, pagination
    shared/                    Data-driven list and record form templates
    auth/, dashboard/, vehicles/, customers/, sales/
    invoices/, reports/, roles/, errors/
  static/
    css/                       Tokens, base, shell, components, forms, tables,
                               dashboard and responsive/print rules
    js/                        Theme, shared UI, SVG chart and sale stepper
    images/                    Local brand, line-icon sprite, vehicle illustrations
tests/test_vehicle_photos.py    Photo lifecycle, validation and failure tests
tests/test_application.py      Route, service and workflow integration tests
```

Lists and forms deliberately share templates rather than copying table, filter, validation and form markup for each module. `RESOURCES` and `FIELDS` in `routes/web.py` define page-specific data and fields. Filters and pagination use ordinary GET requests and preserve URL query parameters. Forms use POST/redirect/GET after success. Core lists/forms work without JavaScript; the sale stepper requires JavaScript.

## Design and theme system

`variables.css` owns the color, spacing, radius, shadow and layout tokens. The `data-theme` attribute on `<html>` selects dark or light values. `theme.js` runs before CSS, restores `autovault-theme` from localStorage, defaults to dark and updates button labels. It tolerates disabled localStorage. Chart colors inherit CSS tokens, including labels, grid and tooltip.

Sidebar state is saved under `autovault-sidebar`. Tablet widths use a compact rail, mobile uses a drawer with focus containment and Escape dismissal, and tables scroll within their cards. Keyboard focus indicators, skip navigation, semantic labels, native dialog confirmation, reduced-motion rules, text status labels, empty states, server validation, toasts and submit loading states are shared.

Rename `Config.BRAND` and replace the local brand mark for rebranding. Dealer identity text in `components/sidebar.html` and invoice details are intentionally separate from the product name.

## Backend integration

The current adapter is **not MySQL**, is not durable, and must not be run in multiple server processes. `SalesService` holds a process lock while validating an active customer and available vehicle, creating the completed sale, marking the vehicle sold, recording STOCK_OUT and generating one invoice. Duplicate and concurrent attempts to sell the same vehicle are rejected. This models the required transaction, but a database transaction must replace the lock for production.

Recommended next step: implement MySQL repositories behind the same `all/get/save` contract and add migrations for `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `vehicles`, `customers`, `stock_movements`, `sales` and `invoices`.

Then:

1. Wrap sale completion in a MySQL transaction; lock the selected vehicle row, recheck availability, add unique constraints on vehicle VIN/code, sale vehicle and invoice sale ID, and roll back all effects on failure.
2. Replace demo sign-in with hashed passwords, secure account creation/reset, session hardening and login rate limiting. Keep CSRF protection. Configure a real secret, HTTPS cookies and production WSGI server.
3. Replace the single `user.role` demo field with user-role and role-permission joins. `can()` and `require()` are the integration boundaries. Routes already enforce permissions on the server; navigation visibility is an additional UX layer.
4. Store immutable customer/vehicle snapshots on completed invoices, add audit records, database-level monetary decimals, and transaction-safe uniqueness checks. Currently invoice descriptions/contact details are read from demo records; sold vehicle identity and price edits are restricted.
5. Add dealership legal details, currency/tax policy, notification delivery, and any pending/cancelled sale lifecycle the project needs. Current new sales complete immediately; pending/cancelled badge and filter styles are prepared.

No speculative SQL schema or empty architecture directories were added: the frontend foundation is ready for the project's final MySQL design without introducing a competing schema.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover all module routes and their local links/assets, authentication and CSRF, role restrictions, vehicle/customer/user forms, empty/filter/pagination states, date validation, stock transitions, invalid sales, coordinated sale/invoice creation, and concurrent double-sale rejection.

Browser verification covered desktop and mobile layouts, light/dark persistence, sidebar collapse and drawer navigation, customer-step validation, all sale steps, confirmation, success and invoice rendering. Manual print CSS review ensures the white invoice remains separate from the application shell. A physical printer was not exercised.

Photo tests additionally cover all supported formats, disguised content, size limits, path safety, shared images, confirmed removal, replacement, persistence and partial-write failures, filename collisions, and fallback rendering.
