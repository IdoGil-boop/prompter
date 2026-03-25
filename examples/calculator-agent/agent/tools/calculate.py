import json
import sys

args = json.loads(sys.stdin.read())
expression = args.get("expression", "")
try:
    result = eval(expression)
    print(result)
except Exception as e:
    print(f"Error: {e}")
