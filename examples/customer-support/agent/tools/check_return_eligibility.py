import json
import sys

data = json.loads(sys.stdin.read())
order_id = data.get("order_id", "")

# Mock return policy
eligible_orders = {
    "ORD-1234": {"eligible": True, "reason": "Within 30-day return window"},
    "ORD-5678": {"eligible": True, "reason": "Within 30-day return window"},
    "ORD-9999": {"eligible": False, "reason": "Order is still processing"},
}

result = eligible_orders.get(order_id, {"eligible": False, "reason": f"Order {order_id} not found"})
print(json.dumps(result))
