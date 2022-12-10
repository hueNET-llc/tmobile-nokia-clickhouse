import aiochclient
import aiohttp
import asyncio
import colorlog
import datetime
import logging
import json
import os
import signal
import sys
import uvloop
uvloop.install()

from time import perf_counter

log = logging.getLogger('TMobile')


class TMobile:
    def __init__(self, loop:asyncio.AbstractEventLoop):
        # Setup logging
        self._setup_logging()
        # Load and check environment variables
        self._load_env_vars()

        # Get the event loop
        self.loop = loop
        # Event to stop the loop in case of SIGTERM
        self.event = asyncio.Event()

        # Queue of data waiting to be inserted into ClickHouse
        # This is in case ClickHouse goes down or something
        self.data_queue = asyncio.Queue(maxsize=self.data_queue_limit)

        # Interface counters to compare difference to
        self.interface_counters = {}

    def _setup_logging(self):
        """
            Sets up logging colors and formatting
        """
        # Create a new handler with colors and formatting
        shandler = logging.StreamHandler(stream=sys.stdout)
        shandler.setFormatter(colorlog.LevelFormatter(
            fmt={
                'DEBUG': '{log_color}{asctime} [{levelname}] {message}',
                'INFO': '{log_color}{asctime} [{levelname}] {message}',
                'WARNING': '{log_color}{asctime} [{levelname}] {message}',
                'ERROR': '{log_color}{asctime} [{levelname}] {message}',
                'CRITICAL': '{log_color}{asctime} [{levelname}] {message}',
            },
            log_colors={
                'DEBUG': 'blue',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bg_red',
            },
            style='{',
            datefmt='%H:%M:%S'
        ))
        # Add the new handler
        logging.getLogger('TMobile').addHandler(shandler)
        log.debug('Finished setting up logging')

    def _load_env_vars(self):
        """
            Loads environment variables
        """
        # Max number of inserts waiting to be inserted at once
        try:
            self.data_queue_limit = int(os.environ.get('DATA_QUEUE_LIMIT', 50))
        except ValueError:
            log.critical('Invalid DATA_QUEUE_LIMIT passed, must be a number')
            exit(1)

        # How long to wait in between scraping the gateway
        try:
            self.fetch_delay = int(os.environ.get('FETCH_DELAY', 10))
        except ValueError:
            log.critical('Invalid FETCH_DELAY passed, must be a number')
            exit(1)

        # Log level to use
        # 10/debug  20/info  30/warning  40/error
        try:
            self.log_level = int(os.environ.get('LOG_LEVEL', 20))
        except ValueError:
            log.critical('Invalid LOG_LEVEL passed, must be a number')
            exit(1)

        # Set the logging level
        logging.root.setLevel(self.log_level)

        # ClickHouse connection info
        try:
            self.gateway_name = os.environ['GATEWAY_NAME']
            self.gateway_url = os.environ['GATEWAY_URL']
            self.clickhouse_url = os.environ['CLICKHOUSE_URL']
            self.clickhouse_user = os.environ['CLICKHOUSE_USER']
            self.clickhouse_pass = os.environ['CLICKHOUSE_PASS']
            self.clickhouse_db = os.environ['CLICKHOUSE_DB']
        except KeyError as e:
            # Print the key that was missing
            log.critical(f'Missing required environment variable "{e.args[0]}"')
            exit(1)

        # ClickHouse table names
        self.clickhouse_5g_table = os.environ.get(
            'CLICKHOUSE_5G_TABLE',
            'tmobile_5g'
        )
        self.clickhouse_lte_table = os.environ.get(
            'CLICKHOUSE_LTE_TABLE',
            'tmobile_lte'
        )
        self.clickhouse_interfaces_table = os.environ.get(
            'CLICKHOUSE_INTERFACES_TABLE',
            'tmobile_interfaces'
        )
        self.clickhouse_status_table = os.environ.get(
            'CLICKHOUSE_STATUS_TABLE',
            'tmobile_status'
        )

    async def export(self):
        log.info('Starting export')
        while True:
            try:
                log.debug('Exporting...')
                start = perf_counter()

                async with self.session.get(f'{self.gateway_url}/fastmile_radio_status_web_app.cgi', timeout=15) as resp:
                    radio_data = json.loads(await resp.text())
                async with self.session.get(f'{self.gateway_url}/lan_status_web_app.cgi?lan', timeout=15) as resp:
                    lan_data = json.loads(await resp.text())
                async with self.session.get(F'{self.gateway_url}/dashboard_device_info_status_web_app.cgi', timeout=15) as resp:
                    device_data = json.loads(await resp.text())
                
                latency = perf_counter() - start

                # Get the current UTC timestamp
                timestamp = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()
                try:
                    self.data_queue.put_nowait([
                            f"""
                            INSERT INTO {self.clickhouse_5g_table} (
                                gateway, physical_cell_id, snr, rsrp,
                                rsrp_strength_index, rsrq, downlink_arfcn,
                                signal_strength_level, band, time
                            ) VALUES
                            """,
                            (
                                self.gateway_name,
                                radio_data['cell_5G_stats_cfg'][0]['stat']['PhysicalCellID'],
                                radio_data['cell_5G_stats_cfg'][0]['stat']['SNRCurrent'],
                                radio_data['cell_5G_stats_cfg'][0]['stat']['RSRPCurrent'],
                                radio_data['cell_5G_stats_cfg'][0]['stat']['RSRPStrengthIndexCurrent'],
                                radio_data['cell_5G_stats_cfg'][0]['stat']['RSRQCurrent'],
                                radio_data['cell_5G_stats_cfg'][0]['stat']['Downlink_NR_ARFCN'],
                                radio_data['cell_5G_stats_cfg'][0]['stat']['SignalStrengthLevel'],
                                radio_data['cell_5G_stats_cfg'][0]['stat']['Band'],
                                timestamp                            
                            )
                    ])
                except (KeyError, IndexError):
                    # In case 5G isn't connected
                    pass
                try:
                    self.data_queue.put_nowait([
                            f"""
                            INSERT INTO {self.clickhouse_lte_table} (
                                gateway, physical_cell_id, rssi, snr,
                                rsrp, rsrp_strength_index, rsrq, downlink_arfcn,
                                signal_strength_level, band, time
                            ) VALUES
                            """,
                            (
                                self.gateway_name,
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['PhysicalCellID'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['RSSICurrent'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['SNRCurrent'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['RSRPCurrent'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['RSRPStrengthIndexCurrent'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['RSRQCurrent'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['DownlinkEarfcn'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['SignalStrengthLevel'],
                                radio_data['cell_LTE_stats_cfg'][0]['stat']['Band'],
                                timestamp
                            )
                    ])
                except (KeyError, IndexError):
                    # In case LTE isn't connected
                    pass

                wired_clients = 0
                wireless_clients = 0
                for client in device_data['device_cfg']:
                    # Wired client
                    if client['InterfaceType'] == 'Ethernet':
                        wired_clients += 1
                    # Wireless client (802.11)
                    elif client['InterfaceType'] == '802.11':
                        wireless_clients += 1

                self.data_queue.put_nowait([
                    f"""
                    INSERT INTO {self.clickhouse_status_table} (
                        gateway, uptime, connected, version, model,
                        wired_devices, wireless_devices, scrape_latency
                    ) VALUES
                    """,
                    (
                        self.gateway_name,
                        device_data['device_app_status'][0]['UpTime'],
                        radio_data['connection_status'][0]['ConnectionStatus'],
                        device_data['device_app_status'][0]['SoftwareVersion'],
                        device_data['device_app_status'][0]['Description'],
                        wired_clients,
                        wireless_clients,
                        latency                    
                    )
                ])

                interfaces = []

                # Ethernet ports
                for iface_num in range(len(lan_data['lan_ether'])):
                    iface = lan_data['lan_ether'][iface_num]
                    if iface['Status'] == 'Down':
                        continue

                    try:
                        # Compare the current interface with the previous one
                        bytes_rx = max(int(iface['stat']['BytesReceived']) - self.interface_counters[f'lan{iface_num}']['bytes_rx'], 0)
                        bytes_tx = max(int(iface['stat']['BytesSent']) - self.interface_counters[f'lan{iface_num}']['bytes_tx'], 0)
                        packets_rx = max(int(iface['stat']['PacketsReceived']) - self.interface_counters[f'lan{iface_num}']['packets_rx'], 0)
                        packets_tx = max(int(iface['stat']['PacketsSent']) - self.interface_counters[f'lan{iface_num}']['packets_tx'], 0)
                    except KeyError:
                        # Interface is new, don't do anything and proceed to updating the counters
                        pass
                    else:
                        interfaces.append((
                            self.gateway_name,
                            f'eth{iface_num}',
                            bytes_rx,
                            bytes_tx,
                            packets_rx,
                            packets_tx,
                            timestamp
                        ))

                    # Update the counters
                    self.interface_counters[f'lan{iface_num}'] = {
                        'bytes_rx': max(int(iface['stat']['BytesReceived']), 0),
                        'bytes_tx': max(int(iface['stat']['BytesSent']), 0),
                        'packets_rx': max(int(iface['stat']['PacketsReceived']), 0),
                        'packets_tx': max(int(iface['stat']['PacketsSent']), 0)
                    }

                # WLAN radios
                for iface_num in range(len(lan_data['wlan_status_glb'])):
                    iface = lan_data['wlan_status_glb'][iface_num]
                    if iface['Enable'] != 1:
                        continue

                    try:
                        # Compare the current interface with the previous one
                        bytes_rx = max(int(iface['TotalBytesReceived']) - self.interface_counters[f'wlan{iface_num}']['bytes_rx'], 0)
                        bytes_tx = max(int(iface['TotalBytesSent']) - self.interface_counters[f'wlan{iface_num}']['bytes_tx'], 0)
                        packets_rx = max(int(iface['TotalPacketsReceived']) - self.interface_counters[f'wlan{iface_num}']['packets_rx'], 0)
                        packets_tx = max(int(iface['TotalPacketsSent']) - self.interface_counters[f'wlan{iface_num}']['packets_tx'], 0)
                    except KeyError:
                        # Interface is new, don't do anything and proceed to updating the counters
                        pass
                    else:
                        interfaces.append((
                            self.gateway_name,
                            f'wlan{iface_num}',
                            bytes_rx,
                            bytes_tx,
                            packets_rx,
                            packets_tx,
                            timestamp
                        ))

                    # Update the counters
                    self.interface_counters[f'wlan{iface_num}'] = {
                        'bytes_rx': max(int(iface['TotalBytesReceived']), 0),
                        'bytes_tx': max(int(iface['TotalBytesSent']), 0),
                        'packets_rx': max(int(iface['TotalPacketsReceived']), 0),
                        'packets_tx': max(int(iface['TotalPacketsSent']), 0)
                    }

                # LAN bridge
                iface = lan_data['lan_ifip']
                try:
                    # Compare the current interface with the previous one
                    bytes_rx = max(int(iface['X_ASB_COM_RxBytes']) - self.interface_counters['bridge']['bytes_rx'], 0)
                    bytes_tx = max(int(iface['X_ASB_COM_TxBytes']) - self.interface_counters['bridge']['bytes_tx'], 0)
                    packets_rx = max(int(iface['X_ASB_COM_RxPackets']) - self.interface_counters['bridge']['packets_rx'], 0)
                    packets_tx = max(int(iface['X_ASB_COM_TxPackets']) - self.interface_counters['bridge']['packets_tx'], 0)
                except KeyError:
                    # Interface is new, don't do anything and proceed to updating the counters
                    pass
                else:
                    interfaces.append((
                        self.gateway_name,
                        'bridge',
                        bytes_rx,
                        bytes_tx,
                        packets_rx,
                        packets_tx,
                        timestamp
                    ))

                # Update the counters
                self.interface_counters['bridge'] = {
                    'bytes_rx': max(int(iface['X_ASB_COM_RxBytes']), 0),
                    'bytes_tx': max(int(iface['X_ASB_COM_TxBytes']), 0),
                    'packets_rx': max(int(iface['X_ASB_COM_RxPackets']), 0),
                    'packets_tx': max(int(iface['X_ASB_COM_TxPackets']), 0)
                }

                # Cellular
                iface = radio_data['cellular_stats'][0]

                try:
                    # Compare the current interface with the previous one
                    bytes_rx = max(int(iface['BytesReceived']) - self.interface_counters['cellular']['bytes_rx'], 0)
                    bytes_tx = max(int(iface['BytesSent']) - self.interface_counters['cellular']['bytes_tx'], 0)
                    # The API doesn't return packets in/out on the cellular interface
                except KeyError:
                    # Interface is new, don't do anything and proceed to updating the counters
                    pass
                else:
                    interfaces.append((
                        self.gateway_name,
                        'cell',
                        bytes_rx,
                        bytes_tx,
                        None,
                        None,
                        timestamp
                    ))

                # Update the counters
                self.interface_counters['cellular'] = {
                    'bytes_rx': max(int(iface['BytesReceived']), 0),
                    'bytes_tx': max(int(iface['BytesSent']), 0),
                }

                log.debug(f'Got interface data: {interfaces}')

                if interfaces:
                    self.data_queue.put_nowait([
                        f"""
                        INSERT INTO {self.clickhouse_interfaces_table} (
                            gateway, interface, bytes_in, bytes_out,
                            packets_in, packets_out, time
                        ) VALUES
                        """,
                        interfaces
                    ])

                log.info(f'Export took {round(latency, 2)}s')
            except asyncio.QueueFull:
                log.error('Failed to insert data into ClickHouse, queue is full')
            except Exception:
                log.exception('Failed to update gateway data')
            finally:
                # Wait the interval before updating again
                await asyncio.sleep(self.fetch_delay)

    async def insert_to_clickhouse(self):
        """
            Gets data from the data queue and inserts it into ClickHouse
        """
        while True:
            # Get and check data from the queue
            if not (data := await self.data_queue.get()):
                continue

            # Keep trying until the insert succeeds
            while True:
                log.debug(f'Got data to insert: {data}')
                try:
                    # Insert the data into ClickHouse
                    # Check if the data is a list (bulk insert)
                    if isinstance(data[1], list):
                        await self.clickhouse.execute(
                            data[0], # Query
                            *data[1] # Data
                        )
                        log.debug(f'Inserted data for timestamp {data[1][-1]}')
                    else:
                        await self.clickhouse.execute(
                            data[0], # Query
                            data[1] # Data
                        )
                        log.debug(f'Inserted data for timestamp {data[1][-1]}')
                    # Insert succeeded, break the loop and move on
                    break
                except IndexError:
                    # Data was invalid somehow, skip it
                    log.error(f'Invalid data: {data}')
                # Insertion failed
                except Exception as e:
                    # Check if it was a parsing error
                    # Sometimes the gateway returns invalid 5G/LTE data
                    if 'Cannot parse' in f'{e}':
                        log.error(f'Insert failed for invalid data {data}')
                        break
                    try:
                        log.error(f'Insert failed for timestamp {data[1][-1]}: "{e}"')
                    except IndexError:
                        # Sometimes the data is super invalid somehow and the log message fails
                        # Catch it and fallback so we don't stop inserting future data
                        log.error(f'Insert failed: "{e}"')

                    # Wait before retrying so we don't spam retries
                    await asyncio.sleep(2)

    async def run(self):
        # Create a ClientSession that doesn't verify SSL certificates
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        )
        self.clickhouse = aiochclient.ChClient(
            self.session,
            url=os.environ['CLICKHOUSE_URL'],
            user=os.environ['CLICKHOUSE_USER'],
            password=os.environ['CLICKHOUSE_PASS'],
            database=os.environ['CLICKHOUSE_DB'],
            json=json
        )

        # Run the exporter in a task
        asyncio.create_task(self.export())

        # Start the ClickHouse inserter
        asyncio.create_task(self.insert_to_clickhouse())

        # Run forever (or until we get SIGTERM'd)
        await self.event.wait()
        # If we got here, we are exiting
        log.info('Exiting')
        # Close the aiohttp session so it doesn't complain
        await self.session.close()

loop = asyncio.new_event_loop()
tmobile = TMobile(loop)

# Handle SIGTERM
def sigterm_handler(_, __):
    # Set the event to stop the loop
    tmobile.event.set()
# Register the SIGTERM handler
signal.signal(signal.SIGTERM, sigterm_handler)

loop.run_until_complete(tmobile.run())