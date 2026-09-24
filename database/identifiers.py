"""Unbranded fictional identifiers for local sample records."""


def fictional_vin(number):
    """Return 17 VIN-like characters, excluding I, O and Q; not a registered VIN."""
    if not 1 <= number <= 999999999:
        raise ValueError("Fictional VIN sequence is out of range.")
    return f"9ZZ1K8R2{number:09}"
