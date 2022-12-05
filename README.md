# tmobile-nokia-clickhouse #
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/hueNET-llc/tmobile-nokia-clickhouse/Master%20-%20Build%20and%20push%20to%20Docker%20Hub?style=flat-square)](https://github.com/hueNET-llc/tmobile-nokia-clickhouse/actions/workflows/master.yml)
[![Docker Image Version (latest by date)](https://img.shields.io/docker/v/rafaelwastaken/tmobile-nokia-clickhouse)](https://hub.docker.com/r/rafaelwastaken/tmobile-nokia-clickhouse)

A T-Mobile Nokia 5G Gateway exporter for ClickHouse

## Environment Variables ##
```
=== Gateway ===
GATEWAY_NAME    -   The device name (e.g. "gateway", default: "trashcan")
GATEWAY_URL     -   The modem's URL (e.g. "http://192.168.12.1", default: "http://192.168.12.1")

=== Exporter ===
SCRAPE_DELAY    -   How long to wait in between scrapes (e.g. "10" for 10 seconds, default: "10")
LOG_LEVEL       -   Logging verbosity (default: "20"), levels: 0 (debug) / 10 (info) / 20 (warning) / 30 (error) / 40 (critical)

=== ClickHouse ===
CLICKHOUSE_URL                  -   ClickHouse URL (e.g. "https://192.168.0.69:8123")
CLICKHOUSE_USER                 -   ClickHouse login username (e.g. "username")
CLICKHOUSE_PASS                 -   ClickHouse login password (e.g. "password")
CLICKHOUSE_DB                   -   ClickHouse database (e.g. "metrics")
CLICKHOUSE_5G_TABLE             -   5G stats table name (default: "cell_5g")
CLICKHOUSE_LTE_TABLE            -   LTE stats table name (default: "cell_lte")
CLICKHOUSE_STATUS_TABLE         -   Gateway status table name (default: "cell_status")
CLICKHOUSE_INTERFACES_TABLE     -   Interface stats table name (default: "cell_interfaces")
```