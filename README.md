# tmobile-nokia-clickhouse #
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/hueNET-llc/tmobile-nokia-clickhouse/Docker%20Hub?style=flat-square)](https://github.com/hueNET-llc/tmobile-nokia-clickhouse/actions/workflows/master.yml)
[![Docker Image Version (latest by date)](https://img.shields.io/docker/v/rafaelwastaken/tmobile-nokia-clickhouse)](https://hub.docker.com/r/rafaelwastaken/tmobile-nokia-clickhouse)

A T-Mobile Nokia 5G Gateway exporter for ClickHouse

## Environment Variables ##
```
=== Gateway Info ===
GATEWAY_NAME        -   The device name (e.g. "gateway", default: "trashcan")
GATEWAY_URL         -   The modem's URL (e.g. "http://192.168.12.1", default: "http://192.168.12.1")

=== Scraping Settings ===
SCRAPE_DELAY        -   How long to wait in between scrapes (e.g. "10" for 10 seconds, default: "10")

=== ClickHouse Login Info ===
CLICKHOUSE_URL      -   ClickHouse URL (e.g. "https://192.168.0.69:8123")
CLICKHOUSE_USER     -   ClickHouse login username (e.g. "username")
CLICKHOUSE_PASS     -   ClickHouse login password (e.g. "password")
CLICKHOUSE_DB       -   ClickHouse database (e.g. "metrics")

=== ClickHouse Table Names ===
5G_TABLE            -   5G stats table name (default: "cell_5g")
LTE_TABLE           -   LTE stats table name (default: "cell_lte")
STATUS_TABLE        -   Gateway status table name (default: "cell_status")
INTERFACES_TABLE    -   Interface stats table name (default: "cell_interfaces")
```