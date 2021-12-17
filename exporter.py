import aiochclient
import aiohttp
import asyncio
import datetime
import json
import os

from traceback import print_exc
from time import perf_counter

GATEWAY_NAME = os.environ.get('GATEWAY_NAME', 'trashcan')
GATEWAY_URL = os.environ.get('GATEWAY_URL', 'http://192.168.12.1')

# How long to wait in between scrapes
SCRAPE_DELAY = int(os.environ.get('SCRAPE_DELAY', 5))

CLICKHOUSE_URL = os.environ['CLICKHOUSE_URL']
CLICKHOUSE_USER = os.environ['CLICKHOUSE_USER']
CLICKHOUSE_PASS = os.environ['CLICKHOUSE_PASS']
CLICKHOUSE_DB = os.environ['CLICKHOUSE_DB']

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
                        "INSERT INTO cell_5g_status_buffer (device, physical_cell_id, snr, rsrp, rsrp_strength_index, rsrq, downlink_arfcn, signal_strength_level, band, time) VALUES",
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
                except (KeyError, IndexError):
                    # In case 5G isn't connected
                    pass
                try:
                    await self.clickhouse.execute(
                        "INSERT INTO cell_lte_status_buffer (device, physical_cell_id, rssi, snr, rsrp, rsrp_strength_index, rsrq, downlink_arfcn, signal_strength_level, band, time) VALUES",
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
                except (KeyError, IndexError):
                    # In case LTE isn't connected
                    pass

                await self.clickhouse.execute(
                    "INSERT INTO cell_device_status_buffer (device, uptime, connected, version, model, ipv4_address, ipv6_address, eth_devices, wlan_devices, scrape_latency) VALUES",
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

                # Ethernet ports
                for iface_num in range(len(lan_data['lan_ether'])):
                    iface = lan_data['lan_ether'][iface_num]
                    if iface['Status'] == 'Down':
                        continue

                    try:
                        interfaces.append((
                            GATEWAY_NAME,
                            f'eth{iface_num}',
                            iface["stat"]["BytesReceived"],
                            iface["stat"]["BytesSent"],
                            iface["stat"]["PacketsReceived"],
                            iface["stat"]["PacketsSent"],
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
                            iface["TotalBytesReceived"],
                            iface["TotalBytesSent"],
                            iface["TotalPacketsReceived"],
                            iface["TotalPacketsSent"],
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
                        iface["X_ASB_COM_RxBytes"],
                        iface["X_ASB_COM_TxBytes"],
                        iface["X_ASB_COM_RxPackets"],
                        iface["X_ASB_COM_TxPackets"],
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
                        iface["BytesReceived"],
                        iface["BytesSent"],
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
                    "INSERT INTO cell_interfaces_buffer (device, interface, bytes_in, bytes_out, packets_in, packets_out, time) VALUES",
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