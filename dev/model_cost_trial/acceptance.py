"""The acceptance checks of the model-cost trial, written from `requirement.md`
alone, before any run, and run unchanged against every build.

The trial copies this file into a built project and runs it there with
pytest from the project's root, so `src` is the build's own package. Each
check names the requirement sentence it holds. Nothing here is a Purlin test
and nothing marks it: it is the trial's yardstick, not a proof.
"""

import datetime

import pytest

from src.inventory import Inventory, InventoryError
from src.invoicing import InvoiceError, Invoicing
from src.orders import OrderError, Orders

DAY = datetime.date(2026, 11, 12)
PRICES = {'MUG': '19.99', 'TEA': '1.50', 'PEN': '0.25'}


def stocked():
    inventory = Inventory()
    inventory.add_product('MUG', 10, 3)
    inventory.add_product('TEA', 50, 5)
    inventory.add_product('PEN', 100, 10)
    return inventory


def paid_order(lines):
    inventory = stocked()
    orders = Orders(inventory)
    order = orders.place(lines)
    orders.pay(order)
    return inventory, orders, order


# --- inventory ----------------------------------------------------------

def test_inv_a_new_product_has_its_stock_available():
    inventory = stocked()
    assert (inventory.on_hand('MUG'), inventory.reserved('MUG'),
            inventory.available('MUG')) == (10, 0, 10)


def test_inv_a_sku_added_twice_is_refused():
    inventory = stocked()
    with pytest.raises(InventoryError):
        inventory.add_product('MUG', 1, 1)
    assert inventory.on_hand('MUG') == 10


def test_inv_restock_adds_to_stock_on_hand():
    inventory = stocked()
    inventory.restock('MUG', 5)
    assert inventory.on_hand('MUG') == 15


def test_inv_a_restock_of_zero_is_refused():
    inventory = stocked()
    with pytest.raises(InventoryError):
        inventory.restock('MUG', 0)
    assert inventory.on_hand('MUG') == 10


def test_inv_reserve_sets_stock_aside():
    inventory = stocked()
    inventory.reserve('MUG', 4)
    assert (inventory.on_hand('MUG'), inventory.reserved('MUG'),
            inventory.available('MUG')) == (10, 4, 6)


def test_inv_a_reservation_below_zero_is_refused_naming_sku_and_quantity():
    inventory = stocked()
    inventory.reserve('MUG', 8)
    with pytest.raises(InventoryError) as raised:
        inventory.reserve('MUG', 3)
    assert 'MUG' in str(raised.value) and '2' in str(raised.value)
    assert inventory.available('MUG') == 2


def test_inv_release_gives_reserved_stock_back():
    inventory = stocked()
    inventory.reserve('MUG', 4)
    inventory.release('MUG', 4)
    assert (inventory.reserved('MUG'), inventory.available('MUG')) == (0, 10)


def test_inv_low_stock_lists_at_or_below_threshold_sorted():
    inventory = stocked()
    inventory.reserve('MUG', 7)      # 3 available, threshold 3: listed
    inventory.reserve('TEA', 44)     # 6 available, threshold 5: not listed
    inventory.reserve('PEN', 95)     # 5 available, threshold 10: listed
    assert list(inventory.low_stock()) == ['MUG', 'PEN']


def test_inv_a_reservation_of_zero_is_refused():
    inventory = stocked()
    with pytest.raises(InventoryError):
        inventory.reserve('MUG', 0)
    assert inventory.reserved('MUG') == 0


# --- orders -------------------------------------------------------------

def test_ord_placing_reserves_every_line():
    inventory = stocked()
    Orders(inventory).place([('MUG', 2), ('TEA', 3)])
    assert (inventory.reserved('MUG'), inventory.reserved('TEA')) == (2, 3)


def test_ord_a_placed_order_has_a_string_id_and_reads_placed():
    orders = Orders(stocked())
    order = orders.place([('MUG', 1)])
    assert isinstance(order, str)
    assert orders.state(order) == 'placed'


def test_ord_one_line_short_refuses_the_order_naming_it_and_reserves_nothing():
    inventory = stocked()
    with pytest.raises(OrderError) as raised:
        Orders(inventory).place([('TEA', 3), ('MUG', 11)])
    assert 'MUG' in str(raised.value)
    assert (inventory.reserved('TEA'), inventory.reserved('MUG')) == (0, 0)


def test_ord_an_order_with_no_lines_is_refused():
    with pytest.raises(OrderError):
        Orders(stocked()).place([])


def test_ord_placed_paid_shipped_delivered():
    orders = Orders(stocked())
    order = orders.place([('MUG', 1)])
    seen = []
    for move in (orders.pay, orders.ship, orders.deliver):
        move(order)
        seen.append(orders.state(order))
    assert seen == ['paid', 'shipped', 'delivered']


def test_ord_shipping_a_placed_order_is_refused():
    orders = Orders(stocked())
    order = orders.place([('MUG', 1)])
    with pytest.raises(OrderError):
        orders.ship(order)
    assert orders.state(order) == 'placed'


def test_ord_delivering_a_paid_order_is_refused():
    _inventory, orders, order = paid_order([('MUG', 1)])
    with pytest.raises(OrderError):
        orders.deliver(order)
    assert orders.state(order) == 'paid'


def test_ord_cancelling_a_placed_order_releases_its_stock():
    inventory = stocked()
    orders = Orders(inventory)
    order = orders.place([('MUG', 2)])
    orders.cancel(order)
    assert (orders.state(order), inventory.reserved('MUG')) == ('cancelled', 0)


def test_ord_cancelling_a_paid_order_releases_its_stock():
    inventory, orders, order = paid_order([('MUG', 2)])
    orders.cancel(order)
    assert (orders.state(order), inventory.reserved('MUG')) == ('cancelled', 0)


def test_ord_cancelling_a_shipped_order_is_refused():
    _inventory, orders, order = paid_order([('MUG', 1)])
    orders.ship(order)
    with pytest.raises(OrderError):
        orders.cancel(order)
    assert orders.state(order) == 'shipped'


# --- invoicing ----------------------------------------------------------

def billed(lines, region, code=None, codes=(), today=DAY):
    _inventory, orders, order = paid_order(lines)
    invoicing = Invoicing(orders, dict(PRICES))
    for added in codes:
        invoicing.add_code(*added)
    made = invoicing.invoice(order, region, today, code)
    return made, invoicing, orders, order


def amounts(made):
    return tuple(made[key] for key in ('subtotal', 'discount', 'tax', 'total'))


def test_bill_uk_tax_is_20_percent():
    made, *_ = billed([('MUG', 2)], 'UK')
    assert amounts(made) == ('39.98', '0.00', '8.00', '47.98')


def test_bill_de_tax_is_19_percent():
    made, *_ = billed([('MUG', 1)], 'DE')
    assert amounts(made) == ('19.99', '0.00', '3.80', '23.79')


def test_bill_export_has_no_tax():
    made, *_ = billed([('MUG', 1)], 'export')
    assert amounts(made) == ('19.99', '0.00', '0.00', '19.99')


def test_bill_tax_is_rounded_half_up_to_the_cent():
    made, *_ = billed([('TEA', 1)], 'DE')   # 19% of 1.50 is 0.285
    assert amounts(made) == ('1.50', '0.00', '0.29', '1.79')


def test_bill_an_unknown_region_is_refused():
    _inventory, orders, order = paid_order([('MUG', 1)])
    with pytest.raises(InvoiceError):
        Invoicing(orders, dict(PRICES)).invoice(order, 'FR', DAY)


def test_bill_an_unpaid_order_is_refused():
    orders = Orders(stocked())
    order = orders.place([('MUG', 1)])
    with pytest.raises(InvoiceError):
        Invoicing(orders, dict(PRICES)).invoice(order, 'UK', DAY)


def test_bill_a_percent_code_comes_off_before_tax():
    made, *_ = billed([('MUG', 2)], 'UK', 'TEN',
                      [('TEN', 'percent', '10', DAY)])
    assert amounts(made) == ('39.98', '4.00', '7.20', '43.18')


def test_bill_a_fixed_code_never_takes_more_than_the_subtotal():
    made, *_ = billed([('PEN', 2)], 'UK', 'FIVE',
                      [('FIVE', 'fixed', '5.00', DAY)])
    assert amounts(made) == ('0.50', '0.50', '0.00', '0.00')


def test_bill_an_expired_code_is_refused():
    _inventory, orders, order = paid_order([('MUG', 1)])
    invoicing = Invoicing(orders, dict(PRICES))
    invoicing.add_code('OLD', 'percent', '10', DAY - datetime.timedelta(1))
    with pytest.raises(InvoiceError):
        invoicing.invoice(order, 'UK', DAY, 'OLD')


def test_bill_an_order_is_invoiced_once():
    _made, invoicing, _orders, order = billed([('MUG', 1)], 'UK')
    with pytest.raises(InvoiceError):
        invoicing.invoice(order, 'UK', DAY)


def test_bill_the_csv_export_holds_the_days_invoices_in_order():
    inventory = stocked()
    orders = Orders(inventory)
    first, second = orders.place([('MUG', 1)]), orders.place([('TEA', 1)])
    orders.pay(first)
    orders.pay(second)
    invoicing = Invoicing(orders, dict(PRICES))
    invoicing.invoice(first, 'UK', DAY)
    invoicing.invoice(second, 'export', DAY)
    lines = [line.strip() for line in invoicing.export_csv(DAY).strip()
             .splitlines()]
    assert lines == ['order,region,subtotal,discount,tax,total',
                     '%s,UK,19.99,0.00,4.00,23.99' % first,
                     '%s,export,1.50,0.00,0.00,1.50' % second]
