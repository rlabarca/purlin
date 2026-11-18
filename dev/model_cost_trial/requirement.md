# The order system: the requirement each trial run builds

Three parts, one `purlin:spec` each, in this order. The trial hands each part's text to
`purlin:spec <part>` word for word. The interface lines are part of the requirement, so the
acceptance checks in `acceptance.py` can call every build the same way.

## inventory

Build an inventory of products in Python 3 with no third-party packages, in the module
`src/inventory.py` of the package `src` (with an `src/__init__.py`).

- `Inventory()` starts empty. `add_product(sku, on_hand, threshold)` adds a product with its stock
  on hand and its low-stock threshold. Adding a SKU that is already there is refused.
- `restock(sku, quantity)` adds to the stock on hand. A quantity must be a whole number above 0.
- `reserve(sku, quantity)` sets stock aside. Available stock is stock on hand minus reserved stock.
  A reservation that would take available stock below zero is refused, with a reason that names
  the SKU and the quantity available.
- `release(sku, quantity)` gives reserved stock back.
- `on_hand(sku)`, `reserved(sku)` and `available(sku)` read the numbers.
- `low_stock()` returns the SKUs whose available stock is at or below their threshold, sorted.
- Every refusal raises `InventoryError`, defined in `src/inventory.py`, with a message, and changes
  nothing.

## orders

Build orders on top of the inventory, in `src/orders.py`.

- `Orders(inventory)` takes an `Inventory`. `place(lines)` takes a list of `(sku, quantity)` pairs,
  at least one, and returns the new order's id, a string. Placing an order reserves stock for every
  line or for none: where one line cannot be reserved, the order is refused with a reason that
  names that line's SKU, and no stock stays reserved.
- An order moves placed → paid → shipped → delivered, only in that order, with `pay(order_id)`,
  `ship(order_id)` and `deliver(order_id)`. Any other move is refused. `state(order_id)` returns
  `placed`, `paid`, `shipped`, `delivered` or `cancelled`.
- `cancel(order_id)` cancels a placed or a paid order and releases its stock. Cancelling an order
  in any other state is refused.
- Every refusal raises `OrderError`, defined in `src/orders.py`, and changes nothing.

## invoicing

Build invoicing on top of the orders, in `src/invoicing.py`.

- `Invoicing(orders, prices)` takes an `Orders` and a price list: a dict from SKU to a price
  written as a decimal string, such as `"19.99"`.
- `add_code(code, kind, amount, expires)` adds a discount code: `kind` is `percent` or `fixed`,
  `amount` a decimal string, `expires` a `datetime.date`. A code can be used up to and including
  its expiry date.
- `invoice(order_id, region, today, code=None)` invoices a paid order and returns a dict with the
  keys `order`, `subtotal`, `discount`, `tax` and `total`, each amount a string with two decimals,
  such as `"47.98"`. `today` is a `datetime.date`. An order that is not paid is refused, and an
  order is invoiced once at most.
- The subtotal is each line's price times its quantity, added up. A `percent` code takes that
  percentage of the subtotal; a `fixed` code takes its amount, and never more than the subtotal.
  One discount code per order. An unknown or expired code is refused with a reason.
- Tax is by region on the subtotal less the discount: `UK` 20%, `DE` 19%, `export` 0%. Any other
  region is refused. The total is the subtotal less the discount plus the tax.
- The discount and the tax are each rounded half up to the cent.
- `export_csv(day)` returns the day's invoices as CSV text: the header
  `order,region,subtotal,discount,tax,total`, then one row per invoice made on that `today`, in
  the order they were made.
- Every refusal raises `InvoiceError`, defined in `src/invoicing.py`, and changes nothing.
