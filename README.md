# tmobile-nokia-clickhouse #
A T-Mobile Nokia 5G Gateway exporter for ClickHouse

Configuration is done via environment variables in order to more easily support running it in a container

## Environment Variables ##
```
GATEWAY_NAME      -   The device name (i.e. "gateway", defaults to "trashcan")
GATEWAY_URL       -   The modem's URL (i.e. "http://192.168.12.1", defaults to "https://192.168.12.1")

SCRAPE_DELAY    -   How long to wait in between scrapes (i.e. "5" for 5 seconds, defaults to "5")

CLICKHOUSE_URL  -   The ClickHouse URL (i.e. "https://192.168.0.69:8123")
CLICKHOUSE_USER -   The ClickHouse login username
CLICKHOUSE_PASS -   The ClickHouse login password
CLICKHOUSE_DB   -   The ClickHouse database
```