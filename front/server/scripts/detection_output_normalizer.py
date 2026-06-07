import math
from typing import Any


def normalize_detection_output(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        return round(value, 9)
    if isinstance(value, dict):
        return {
            str(key): normalize_detection_output(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        normalized = [normalize_detection_output(item) for item in value]
        return sorted(normalized, key=lambda item: repr(item))
    return value
