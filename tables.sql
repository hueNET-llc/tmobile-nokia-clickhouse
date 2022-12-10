-- PLEASE NOTE
-- These buffer tables are what I personally use to buffer and batch inserts
-- You may have to modify them to work in your setup

CREATE TABLE tmobile_status (
        gateway LowCardinality(String),
        uptime bigint,
        connected boolean,
        version LowCardinality(String),
        model LowCardinality(String),
        wired_devices smallint DEFAULT 0,
        wireless_devices smallint DEFAULT 0,
        scrape_latency float,
        time DateTime DEFAULT now()
    ) ENGINE = MergeTree() PARTITION BY toYYYYMM(time) ORDER BY (gateway, time) PRIMARY KEY (gateway, time);

CREATE TABLE tmobile_status_buffer (
        gateway LowCardinality(String),
        uptime bigint,
        connected boolean,
        version LowCardinality(String),
        model LowCardinality(String),
        wired_devices smallint DEFAULT 0,
        wireless_devices smallint DEFAULT 0,
        scrape_latency float,
        time DateTime DEFAULT now()
    ) ENGINE = Buffer(homelab, tmobile_status, 1, 10, 10, 10, 100, 10000, 10000);

CREATE TABLE tmobile_interfaces (
        gateway LowCardinality(String),
        interface LowCardinality(String),
        bytes_in UInt64,
        bytes_out UInt64,
        packets_in Nullable(UInt64),
        packets_out Nullable(UInt64),
        time DateTime DEFAULT now()
    ) ENGINE = MergeTree() PARTITION BY toYYYYMM(time) ORDER BY (gateway, interface, time) PRIMARY KEY (gateway, interface, time);

CREATE TABLE tmobile_interfaces_buffer (
        gateway LowCardinality(String),
        interface LowCardinality(String),
        bytes_in UInt64,
        bytes_out UInt64,
        packets_in Nullable(UInt64),
        packets_out Nullable(UInt64),
        time DateTime DEFAULT now()
    ) ENGINE = Buffer(homelab, tmobile_interfaces, 1, 10, 10, 10, 100, 10000, 10000);

CREATE TABLE tmobile_5g (
        gateway LowCardinality(String),
        physical_cell_id smallint,
        snr tinyint,
        rsrp smallint,
        rsrp_strength_index smallint,
        rsrq tinyint,
        downlink_arfcn int,
        signal_strength_level tinyint,
        band LowCardinality(String),
        time DateTime DEFAULT now()
    ) ENGINE = MergeTree() PARTITION BY toYYYYMM(time) ORDER BY (gateway, physical_cell_id, time) PRIMARY KEY (gateway, physical_cell_id, time);

CREATE TABLE tmobile_5g_buffer (
        gateway LowCardinality(String),
        physical_cell_id smallint,
        snr tinyint,
        rsrp smallint,
        rsrp_strength_index smallint,
        rsrq tinyint,
        downlink_arfcn int,
        signal_strength_level tinyint,
        band LowCardinality(String),
        time DateTime DEFAULT now()
    ) ENGINE = Buffer(homelab, tmobile_5g, 1, 10, 10, 10, 100, 10000, 10000);

CREATE TABLE tmobile_lte (
        gateway LowCardinality(String),
        physical_cell_id smallint,
        rssi smallint,
        snr tinyint,
        rsrp smallint,
        rsrp_strength_index smallint,
        rsrq tinyint,
        downlink_arfcn int,
        signal_strength_level tinyint,
        band LowCardinality(String),
        time DateTime DEFAULT now()
    ) ENGINE = MergeTree() PARTITION BY toYYYYMM(time) ORDER BY (gateway, physical_cell_id, time) PRIMARY KEY (gateway, physical_cell_id, time);

CREATE TABLE tmobile_lte_buffer (
        gateway LowCardinality(String),
        physical_cell_id smallint,
        rssi smallint,
        snr tinyint,
        rsrp smallint,
        rsrp_strength_index smallint,
        rsrq tinyint,
        downlink_arfcn int,
        signal_strength_level tinyint,
        band LowCardinality(String),
        time DateTime DEFAULT now()
    ) ENGINE = Buffer(homelab, tmobile_lte, 1, 10, 10, 10, 100, 10000, 10000);