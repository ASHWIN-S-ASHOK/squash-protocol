import json
from squash.engine import SquashEngine
from squash.v2 import BinarySquashEngine

big_payload = {
    "user": {
        "id": 1,
        "name": "Ashwin Kumar",
        "email": "ashwin@email.com",
        "age": 28,
        "is_active": True,
        "address": {
            "street": "123 MG Road",
            "city": "Mumbai",
            "state": "Maharashtra",
            "zip_code": "400001",
            "country": "India",
        },
        "tags": ["developer", "kotlin", "python"],
    }
}

large_array_payload = {
    "users": [big_payload["user"] for _ in range(500)]
}

v2_engine = BinarySquashEngine()
v2_with_dict = v2_engine.to_binary_frame(large_array_payload, "large_array")

print(f"Payload keys: {large_array_payload.keys()}")
print(f"Users count: {len(large_array_payload['users'])}")
print(f"Serialized size: {len(v2_with_dict)}")
