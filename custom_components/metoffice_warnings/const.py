"""Constants for the Met Office Warnings integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "metoffice_warnings"

CONF_API_KEY: Final = "api_key"
CONF_BASE_URL: Final = "base_url"

# Confirmed against a live call: unlike Met Office DataHub, this host is the
# same fixed public gateway for every NSWWS subscriber - only the API key is
# personal. Offered as the config flow's default so most users never need to
# type it, but left editable in case Met Office versions or migrates it.
DEFAULT_BASE_URL: Final = "https://data.hub.api.metoffice.gov.uk/nswws/v1.1"
CONF_AREAS: Final = "areas"
CONF_MONITOR_ALL: Final = "monitor_all"
CONF_USE_HOME_LOCATION: Final = "use_home_location"
CONF_SCAN_INTERVAL_MINUTES: Final = "scan_interval_minutes"

DEFAULT_SCAN_INTERVAL_MINUTES: Final = 10
MIN_SCAN_INTERVAL_MINUTES: Final = 5
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

# Confirmed against a live call. There is no fixed "issued" path - the feed's
# rel="related" link ("Latest version of all issued warnings") gives a URL
# containing the feed's own UUID, which must be discovered on every poll
# rather than assumed stable. The header is "apikey", not "x-api-key" as the
# older metoffice.github.io docs claim - api-management.metoffice.cloud's
# error response for a missing/wrong header confirms "apikey" is correct.
FEED_PATH: Final = "/objects/feed"
API_KEY_HEADER: Final = "apikey"

AREA_ALL: Final = "all"

WARNING_LEVEL_NONE: Final = "none"
WARNING_LEVEL_YELLOW: Final = "yellow"
WARNING_LEVEL_AMBER: Final = "amber"
WARNING_LEVEL_RED: Final = "red"

WARNING_LEVELS: Final = (
    WARNING_LEVEL_NONE,
    WARNING_LEVEL_YELLOW,
    WARNING_LEVEL_AMBER,
    WARNING_LEVEL_RED,
)
