import json
import sys

data = json.loads(sys.stdin.read())
order_id = data.get("order_id", "")

# Mock order database
orders = {
    "ORD-1234": {"status": "shipped", "items": ["Blue T-Shirt", "Running Shoes"], "tracking": "1Z999AA10"},
    "ORD-5678": {"status": "delivered", "items": ["Laptop Stand"], "tracking": "1Z999BB20"},
    "ORD-9999": {"status": "processing", "items": ["Wireless Mouse", "USB-C Hub"], "tracking": None},
}

order = orders.get(order_id)
if order:
    print(json.dumps(order))
else:
    print(json.dumps({"error": f"Order {order_id} not found"}))
