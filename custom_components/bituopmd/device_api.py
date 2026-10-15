"""HTTP helpers for EW meters and Bituo Dial gateways.

EW meters: GET /data is a flat ProductModel JSON (power in kW).
Dial: GET /data is {ok,event,d:{dial_sn,meters[]}} (power already in W).
"""
import logging
import requests

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 12

KIND_METER = "meter"
KIND_DIAL = "dial"

DIAL_METER_EXCLUDE = {
    "sn",
    "label",
    "online",
    "_source",
    "_dial",
}


class DeviceProbeError(Exception):
    """Raised when the host is not a Bituo EW meter or Dial with HTTP on."""


def http_get_json(url):
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def is_dial_payload(payload):
    if not isinstance(payload, dict):
        return False
    if payload.get("event") != "data":
        return False
    inner = payload.get("d")
    return isinstance(inner, dict) and ("meters" in inner or "dial_sn" in inner)


def coerce_value(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def normalize_dial_meter(meter):
    if not isinstance(meter, dict):
        return None
    sn = meter.get("sn")
    if not sn:
        return None
    out = {}
    for key, value in meter.items():
        if key in DIAL_METER_EXCLUDE:
            continue
        if key == "_rssi":
            out["RSSI"] = coerce_value(value)
            continue
        out[key] = coerce_value(value)
    out["sn"] = sn
    out["label"] = meter.get("label") or sn
    out["online"] = bool(meter.get("online"))
    return out


def probe_device(host_ip):
    """Identify an EW meter or a Dial gateway at host_ip."""
    try:
        payload = http_get_json(f"http://{host_ip}/data")
    except requests.RequestException as err:
        raise DeviceProbeError(str(err)) from err

    if is_dial_payload(payload):
        inner = payload.get("d") or {}
        dial_sn = inner.get("dial_sn") or "DIAL"
        meters = []
        for item in inner.get("meters") or []:
            normalized = normalize_dial_meter(item)
            if normalized is not None:
                meters.append(normalized)
        return {
            "kind": KIND_DIAL,
            "host": host_ip,
            "title": f"Bituo Dial {dial_sn}",
            "dial_sn": dial_sn,
            "meters": meters,
        }

    if not payload:
        raise DeviceProbeError("No data returned")

    model = payload.get("ProductModel") or payload.get("productModel") or "Bituo PMD"
    return {
        "kind": KIND_METER,
        "host": host_ip,
        "title": f"{model} - {host_ip}",
        "payload": payload,
    }


def scale_ew_power_fields(data):
    """EW /data reports power in kW; PMD sensors expect W."""
    if not isinstance(data, dict):
        return data
    for key in list(data.keys()):
        lower = key.lower()
        if "power" in lower and "factor" not in lower:
            try:
                data[key] = float(data[key]) * 1000
            except (TypeError, ValueError):
                _LOGGER.error("Non-numeric power for key %s: %s", key, data[key])
                data[key] = None
    return data
