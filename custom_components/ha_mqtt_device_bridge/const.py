"""Constants for Home Assistant MQTT Device Bridge."""

DOMAIN = "ha_mqtt_device_bridge"

CONF_ALLOWED_INTEGRATIONS = "allowed_integrations"
CONF_QOS = "qos"
CONF_TOPIC_PREFIX = "topic_prefix"

DEFAULT_ALLOWED_INTEGRATIONS = ("overkiz", "miele")
DEFAULT_NAME = "Home Assistant MQTT Device Bridge"
DEFAULT_QOS = 0
DEFAULT_TOPIC_PREFIX = "ha2fhem"

SERVICE_REPUBLISH = "republish"

