"""Constants for the BituoPMD integration."""

DOMAIN = "bituopmd"

CONF_HOST_IP = "host_ip"
CONF_IDENTITY_HOST = "identity_host"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 5
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 3600
REQUEST_TIMEOUT = 10
# Consecutive poll failures tolerated before entities are marked unavailable.
# Single transient failures (e.g. HA event-loop stalls) keep the last data.
FAILURE_THRESHOLD = 2

DATA_KEY_ENTRIES = "entries"
DATA_KEY_FRONTEND = "frontend_registered"
