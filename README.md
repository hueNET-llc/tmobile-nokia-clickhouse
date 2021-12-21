# tmobile-nokia-clickhouse #
A T-Mobile Nokia 5G Gateway exporter for ClickHouse

Configuration is done via environment variables in order to more easily support running it in a container

## Environment Variables ##
```
--- Gateway Info ---
GATEWAY_NAME        -   The device name (e.g. "gateway", default: "trashcan")
GATEWAY_URL         -   The modem's URL (e.g. "http://192.168.12.1", default: "https://192.168.12.1")

--- Scraping Settings ---
SCRAPE_DELAY        -   How long to wait in between scrapes (e.g. "10" for 10 seconds, default: "10")

--- ClickHouse Login Info ---
CLICKHOUSE_URL      -   The ClickHouse URL (e.g. "https://192.168.0.69:8123")
CLICKHOUSE_USER     -   The ClickHouse login username
CLICKHOUSE_PASS     -   The ClickHouse login password
CLICKHOUSE_DB       -   The ClickHouse database

--- ClickHouse Table Names ---
5G_TABLE            -   5G stats table name (default: "cell_5g")
LTE_TABLE           -   LTE stats table name (default: "cell_lte")
STATUS_TABLE        -   Gateway status table name (default: "cell_status")
INTERFACES_TABLE    -   Interface stats table name (default: "cell_interfaces")
```