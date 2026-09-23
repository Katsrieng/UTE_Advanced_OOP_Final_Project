"""Domain money rules shared by record and sales services."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def money(value):
    try:
        amount=Decimal(str(value))
        if not amount.is_finite() or amount<0 or amount>Decimal('100000000'):
            raise ValueError()
        return amount.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError('Enter a valid non-negative amount within range.')

@dataclass(frozen=True)
class SaleAmounts:
    price: Decimal
    discount: Decimal
    @classmethod
    def calculate(cls,price,discount):
        result=cls(money(price),money(discount))
        if result.discount>result.price:
            raise ValueError('Discount must be between zero and the selling price.')
        return result
    @property
    def total(self): return self.price-self.discount
