from __future__ import annotations


def validate_metric_value(value):
    if value is None:
        return 0.0
    return round(float(value), 2)
