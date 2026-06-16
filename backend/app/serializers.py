"""Shared serializer functions for globe data models."""


def _trade_route_to_dict(r) -> dict:
    return {
        "from": r.from_country,
        "to": r.to_country,
        "value": r.value_label,
        "fromLat": r.from_lat,
        "fromLng": r.from_lng,
        "toLat": r.to_lat,
        "toLng": r.to_lng,
        "color": r.color,
    }


def _military_relation_to_dict(r) -> dict:
    return {
        "countryA": r.country_a,
        "countryB": r.country_b,
        "type": r.relation_type,
        "label": r.label,
        "fromLat": r.from_lat,
        "fromLng": r.from_lng,
        "toLat": r.to_lat,
        "toLng": r.to_lng,
    }


def _port_to_dict(p) -> dict:
    return {
        "countryCode": p.country_code,
        "name": p.name,
        "lat": p.latitude,
        "lng": p.longitude,
        "volume": p.volume,
    }
