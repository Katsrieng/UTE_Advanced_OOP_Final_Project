"""Resource config for the existing web endpoints."""

RESOURCES = {
    "vehicles": dict(
        title="Vehicles",
        description="",
        singular="Vehicle",
        permission="vehicles.view",
        create="vehicles.create",
        columns=["Vehicle", "VIN", "Year", "Price", "Status", "Actions"],
    ),
    "customers": dict(
        title="Customers",
        description="",
        singular="Customer",
        permission="customers.view",
        create="customers.create",
        columns=["Customer", "Phone", "Email", "Purchases", "Status", "Actions"],
    ),
    "sales": dict(
        title="Sales",
        description="",
        singular="Sale",
        permission="sales.view",
        create="sales.create",
        columns=[
            "Sale ID",
            "Customer",
            "Vehicle",
            "Staff",
            "Date",
            "Total",
            "Status",
            "Actions",
        ],
    ),
    "invoices": dict(
        title="Invoices",
        description="",
        singular="Invoice",
        permission="invoices.view",
        create=None,
        columns=["Invoice number", "Customer", "Vehicle", "Date", "Total", "Actions"],
    ),
    "inventory": dict(
        title="Inventory",
        description="",
        singular="Stock Movement",
        permission="inventory.view",
        create="inventory.create",
        columns=["Date", "Vehicle", "Movement", "Recorded by", "Reason", "Quantity"],
    ),
    "users": dict(
        title="Users",
        description="",
        singular="User",
        permission="users.manage",
        create="users.manage",
        columns=["Name", "Username", "Role", "Status", "Actions"],
    ),
}


TEXT_LIMITS = {
    "code": 80,
    "username": 80,
    "phone": 80,
    "plate": 80,
    "brand": 100,
    "color": 100,
    "model": 150,
    "vin": 17,
}


FIELDS = {
    "vehicles": [
        (
            "Basic information",
            [
                ("code", "Vehicle code", "text", True),
                ("brand", "Brand", "text", True),
                ("model", "Model", "text", True),
                ("year", "Year", "number", True),
                ("color", "Color", "text", True),
            ],
        ),
        (
            "Identification",
            [("vin", "VIN", "text", True), ("plate", "Plate number", "text", False)],
        ),
        (
            "Pricing",
            [
                ("purchase_price", "Purchase price (USD)", "number", True),
                ("price", "Selling price (USD)", "number", True),
            ],
        ),
        ("Inventory", [("status", "Status", "select", True)]),
    ],
    "customers": [
        (
            "Contact information",
            [
                ("code", "Customer code", "text", True),
                ("name", "Full name", "text", True),
                ("phone", "Phone", "tel", True),
                ("email", "Email", "email", True),
            ],
        ),
        (
            "Additional details",
            [
                ("address", "Address", "textarea", False),
                ("status", "Status", "select", True),
            ],
        ),
    ],
    "users": [
        (
            "Team member",
            [
                ("name", "Full name", "text", True),
                ("username", "Username", "text", True),
                ("email", "Email", "email", True),
                ("password", "Password (required for new users)", "password", False),
                ("role", "Role", "select", True),
                ("status", "Status", "select", True),
            ],
        )
    ],
    "inventory": [
        (
            "Movement details",
            [
                ("vehicle_id", "Vehicle", "select", True),
                ("movement", "Movement", "select", True),
                ("reason", "Reason", "textarea", True),
            ],
        )
    ],
}
