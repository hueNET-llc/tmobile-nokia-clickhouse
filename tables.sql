-- PLEASE NOTE
-- These buffer tables are what I personally use to buffer and batch inserts
-- You may have to modify them to work in your setup

CREATE TABLE cell_status (
        device LowCardinality(String),
        uptime bigint,
        connected boolean,
        version LowCardinality(String),
        model LowCardinality(String),
        ipv4_address LowCardinality(Nullable(String)),
        ipv6_address LowCardinality(Nullable(String)),
        eth_devices smallint DEFAULT 0,
        wlan_devices smallint DEFAULT 0,
        scrape_latency float,
        time DateTime DEFAULT now()
    ) ENGINE = MergeTree() PARTITION BY toDate(time) ORDER BY (device, time) PRIMARY KEY (device, time);

CREATE TABLE cell_status_buffer (
        device LowCardinality(String),
        uptime bigint,
        connected boolean,
        version LowCardinality(String),
        model LowCardinality(String),
        ipv4_address LowCardinality(Nullable(String)),
        ipv6_address LowCardinality(Nullable(String)),
        eth_devices smallint DEFAULT 0,
        wlan_devices smallint DEFAULT 0,
        scrape_latency float,
        time DateTime DEFAULT now()
    ) ENGINE = Buffer(homelab, cell_status, 1, 10, 10, 10, 100, 10000, 10000);

CREATE TABLE cell_interfaces (
        device LowCardinality(String),
        interface LowCardinality(String),
        bytes_in int,
        bytes_out int,
        packets_in Nullable(int),
        packets_out Nullable(int),
        time DateTime DEFAULT now()
    ) ENGINE = MergeTree() PARTITION BY toDate(time) ORDER BY (device, interface, time) PRIMARY KEY (device, interface, time);

CREATE TABLE cell_interfaces_buffer (
        device LowCardinality(String),
        interface LowCardinality(String),
        bytes_in int,
        bytes_out int,
        packets_in Nullable(int),
        packets_out Nullable(int),
        time DateTime DEFAULT now()
    ) ENGINE = Buffer(homelab, cell_interfaces, 1, 10, 10, 10, 100, 10000, 10000);

CREATE TABLE cell_5g (
        device LowCardinality(String),
        physical_cell_id smallint,
        snr tinyint,
        rsrp smallint,
        rsrp_strength_index smallint,
        rsrq tinyint,
        downlink_arfcn int,
        signal_strength_level tinyint,
        band LowCardinality(String),
        time DateTime DEFAULT now()
    ) ENGINE = MergeTree() PARTITION BY toDate(time) ORDER BY (device, physical_cell_id, time) PRIMARY KEY (device, physical_cell_id, time);

CREATE TABLE cell_5g_buffer (
        device LowCardinality(String),
        physical_cell_id smallint,
        snr tinyint,
        rsrp smallint,
        rsrp_strength_index smallint,
        rsrq tinyint,
        downlink_arfcn int,
        signal_strength_level tinyint,
        band LowCardinality(String),
        time DateTime DEFAULT now()
    ) ENGINE = Buffer(homelab, cell_5g, 1, 10, 10, 10, 100, 10000, 10000);

CREATE TABLE cell_lte (
        device LowCardinality(String),
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
    ) ENGINE = MergeTree() PARTITION BY toDate(time) ORDER BY (device, physical_cell_id, time) PRIMARY KEY (device, physical_cell_id, time);

CREATE TABLE cell_lte_buffer (
        device LowCardinality(String),
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
    ) ENGINE = Buffer(homelab, cell_lte, 1, 10, 10, 10, 100, 10000, 10000);