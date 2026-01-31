# Order & Stock Domain Rules

## Order Lifecycle
- pending → confirmed → shipped → delivered
- pending/confirmed → cancelled
- shipped/delivered CANNOT be cancelled

## Stock Rules
- Stock is reduced ONLY when order is created
- Stock is restored ONLY when order is cancelled
- Stock can NEVER go below zero

## Atomicity Rules
- Order creation is atomic
- Stock deduction + order items must succeed together
- Partial orders are forbidden

## Snapshot Rules
- OrderItem stores product_name, price, size, color
- Order history must not change if product changes

## Access Rules
- Customers can track orders using order_id + phone
- Only admin can change order status
