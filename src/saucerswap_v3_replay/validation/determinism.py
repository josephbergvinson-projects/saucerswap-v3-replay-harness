from __future__ import annotations

import hashlib
import json


def fingerprint_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
