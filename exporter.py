import aiochclient
import aiohttp
import asyncio
import datetime
import json
import os

from traceback import print_exc
from time import perf_counter

# Gateway info
GATEWAY_NAME = os.environ.get('GATEWAY_NAME', 'trashcan')
GATEWAY_URL = os.environ.get('GATEWAY_URL', 'http://192.168.12.1')

# Scraping settings
SCRAPE_DELAY = int(os.environ.get('SCRAPE_DELAY', 10))

# ClickHouse login info
CLICKHOUSE_URL = os.environ['CLICKHOUSE_URL']
CLICKHOUSE_USER = os.environ['CLICKHOUSE_USER']
CLICKHOUSE_PASS = os.environ['CLICKHOUSE_PASS']
CLICKHOUSE_DB = os.environ['CLICKHOUSE_DB']

# ClickHouse table names
FIVEG_TABLE = os.environ.get(
    'CLICKHOUSE_5G_TABLE',
    'cell_5g'
)
LTE_TABLE = os.environ.get(
    'CLICKHOUSE_LTE_TABLE',
    'cell_lte'
)
INTERFACES_TABLE = os.environ.get(
    'CLICKHOUSE_INTERFACES_TABLE',
    'cell_interfaces'
)
STATUS_TABLE = os.environ.get(
    'CLICKHOUSE_STATUS_TABLE',
    'cell_status'
)
class Exporter:
    async def start(self):
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

        await self.export()

    async def export(self):
        while True:
            try:
                start = perf_counter()

                async with self.session.get(f'{GATEWAY_URL}/fastmile_radio_status_web_app.cgi', timeout=15) as resp:
                    radio_data = json.loads(await resp.text())
                async with self.session.get(f'{GATEWAY_URL}/lan_status_web_app.cgi?lan', timeout=15) as resp:
                    lan_data = json.loads(await resp.text())
                async with self.session.get(F'{GATEWAY_URL}/dashboard_device_info_status_web_app.cgi', timeout=15) as resp:
                    device_data = json.loads(await resp.text())
                
                latency = perf_counter() - start

                # Get the current UTC timestamp
                timestamp = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()
                try:
                    await self.clickhouse.execute(
                        f"INSERT INTO {FIVEG_TABLE} (device, physical_cell_id, snr, rsrp, rsrp_strength_index, rsrq, downlink_arfcn, signal_strength_level, band, time) VALUES",
                        (
                            GATEWAY_NAME,
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
                    )
                except (aiochclient.exceptions.ChClientError, KeyError, IndexError):
                    # In case 5G isn't connected
                    pass
                try:
                    await self.clickhouse.execute(
                        f"INSERT INTO {LTE_TABLE} (device, physical_cell_id, rssi, snr, rsrp, rsrp_strength_index, rsrq, downlink_arfcn, signal_strength_level, band, time) VALUES",
                        (
                            GATEWAY_NAME,
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
                    )
                except (aiochclient.exceptions.ChClientError, KeyError, IndexError):
                    # In case LTE isn't connected
                    pass

                await self.clickhouse.execute(
                    f"INSERT INTO {STATUS_TABLE} (device, uptime, connected, version, model, ipv4_address, ipv6_address, eth_devices, wlan_devices, scrape_latency) VALUES",
                    (
                        GATEWAY_NAME,
                        device_data['device_app_status'][0]['UpTime'],
                        radio_data['connection_status'][0]['ConnectionStatus'],
                        device_data['device_app_status'][0]['SoftwareVersion'],
                        device_data['device_app_status'][0]['Description'],
                        radio_data['apn_cfg'][0]['X_ALU_COM_IPAddressV4'],
                        radio_data['apn_cfg'][0]['X_ALU_COM_IPAddressV6'],
                        len([dev for dev in device_data['device_cfg'] if dev['InterfaceType'] == 'Ethernet']),
                        len([dev for dev in device_data['device_cfg'] if dev['InterfaceType'] == '802.11']),
                        latency
                    )
                )

                interfaces = []

                # IMPORTANT: The interface counters seem to randomly overflow (example below)
                # Make sure to apply max() to the counters to prevent this
                # ┌────────────────time─┬─interface─┬────bytes_in─┐
                # │ 2022-12-02 23:59:44 │ cell      │ -2047731018 │
                # │ 2022-12-02 23:59:57 │ cell      │ -2043702372 │
                # └─────────────────────┴───────────┴─────────────┘
                # ┌────────────────time─┬─interface─┬───bytes_in─┐
                # │ 2022-12-01 23:59:42 │ br0       │ -922068449 │
                # │ 2022-12-01 23:59:53 │ br0       │ -922028830 │
                # │ 2022-12-01 23:59:42 │ eth0      │ -623448961 │
                # │ 2022-12-01 23:59:53 │ eth0      │ -623405626 │
                # └─────────────────────┴───────────┴────────────┘
                # ┌────────────────time─┬─interface─┬────bytes_in─┐
                # │ 2022-11-30 23:59:40 │ br0       │ -1257435445 │
                # │ 2022-11-30 23:59:51 │ br0       │ -1257397732 │
                # │ 2022-11-30 23:59:40 │ cell      │   -76842077 │
                # │ 2022-11-30 23:59:51 │ cell      │   -76792249 │
                # └─────────────────────┴───────────┴─────────────┘


                # Ethernet ports
                for iface_num in range(len(lan_data['lan_ether'])):
                    iface = lan_data['lan_ether'][iface_num]
                    if iface['Status'] == 'Down':
                        continue

                    try:
                        interfaces.append((
                            GATEWAY_NAME,
                            f'eth{iface_num}',
                            max(iface["stat"]["BytesReceived"], 0),
                            max(iface["stat"]["BytesSent"], 0),
                            max(iface["stat"]["PacketsReceived"], 0),
                            max(iface["stat"]["PacketsSent"], 0),
                            timestamp
                        ))
                    except KeyError:
                        pass

                # WLAN radios
                for iface_num in range(len(lan_data['wlan_status_glb'])):
                    iface = lan_data['wlan_status_glb'][iface_num]
                    if iface['Enable'] != 1:
                        continue

                    try:
                        interfaces.append((
                            GATEWAY_NAME,
                            f'wlan{iface_num}',
                            max(iface["TotalBytesReceived"], 0),
                            max(iface["TotalBytesSent"], 0),
                            max(iface["TotalPacketsReceived"], 0),
                            max(iface["TotalPacketsSent"], 0),
                            timestamp
                        ))
                    except KeyError:
                        pass

                # LAN bridge
                iface = lan_data['lan_ifip']
                try:
                    interfaces.append((
                        GATEWAY_NAME,
                        'br0',
                        max(iface["X_ASB_COM_RxBytes"], 0),
                        max(iface["X_ASB_COM_TxBytes"], 0),
                        max(iface["X_ASB_COM_RxPackets"], 0),
                        max(iface["X_ASB_COM_TxPackets"], 0),
                        timestamp
                    ))
                except KeyError:
                    pass

                # Cellular
                iface = radio_data['cellular_stats'][0]
                try:
                    interfaces.append((
                        GATEWAY_NAME,
                        'cell',
                        max(iface["BytesReceived"], 0),
                        max(iface["BytesSent"], 0),
                        # The API doesn't expose packets sent/received
                        # on the cellular interface for some reason
                        None,
                        None,
                        timestamp
                    ))
                except KeyError:
                    pass

                # Batch insert the data into the buffer
                await self.clickhouse.execute(
                    f"INSERT INTO {INTERFACES_TABLE} (device, interface, bytes_in, bytes_out, packets_in, packets_out, time) VALUES",
                    *interfaces
                )
                print(f'Update took {round(latency, 2)}s')
            except Exception:
                print('Failed to update')
                print_exc()
            finally:
                await asyncio.sleep(SCRAPE_DELAY)

loop = asyncio.new_event_loop()
loop.run_until_complete(Exporter().start())