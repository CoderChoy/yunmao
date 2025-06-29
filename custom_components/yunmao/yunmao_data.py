import asyncio
from io import BytesIO
import json
import logging
import threading

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from homeassistant.components.cover import CoverEntity
from homeassistant.components.light import LightEntity

_LOGGER = logging.getLogger(__name__)


async def _request_data_from_server(ip_addr: str):
    reader, writer = await asyncio.open_connection(host=ip_addr, port=8888)
    # remove comment to test slow client
    body = (
        '{"sourceId":"' + ip_addr + '","serialNum":"' + ip_addr + '",'
        '"requestType":"query","id":"0000000000000000"}'
    )
    writer.write(body.encode("utf8"))  # prepare data
    await writer.drain()  # send data

    if writer.can_write_eof():
        writer.write_eof()  # tell server that we sent all data

    # better use BytesIO than += if you gonna concat many times
    data_from_server = BytesIO()  # now get server answer
    result_json = None
    try:
        while True:
            # read chunk up to 8k bytes
            data = await asyncio.wait_for(reader.read(8192), timeout=5.0)
            data_from_server.write(data)
            # if server told use that no more data
            if reader.at_eof():
                break

        result_json = json.loads(data_from_server.getvalue().decode("utf8"))
    finally:
        writer.close()
        return result_json


async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    _LOGGER.info(f"Client {addr} connected.")

    try:
        while True:
            # 一分钟有一个心跳包，2分钟没收到数据包可中断连接
            data = await asyncio.wait_for(reader.read(8192), 120)
            if not data:
                break
            decode_data: str = data.decode("utf-8")
            # _LOGGER.warning(f"Received {decode_data} \n")
            for message in decode_data.split("\n"):
                if len(message) > 6:
                    ym_singleton.handle_gateway_data(json.loads(message))

    except TimeoutError:
        _LOGGER.error("Client connection timed out")
    except ConnectionResetError:
        _LOGGER.error(f"Connection with {addr} was reset by the peer.")
    except Exception as e:
        _LOGGER.error(f"Error occurred with {addr}: {e}")
    finally:
        _LOGGER.error(f"Closing the connection with {addr}")
        writer.close()
        await writer.wait_closed()


async def start_yun_mao_server():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 21688)
    async with server:
        await server.serve_forever()


def background_server_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_yun_mao_server())


class YunMaoDataSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.lights: list[LightEntity] = []
        self.covers: list[CoverEntity] = []
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._background_task, "interval", seconds=10, max_instances=1
        )
        self._scheduler.start()
        self._thread = threading.Thread(
            target=background_server_task, name="YunMaoServer"
        )
        self._thread.start()

    def add_light_entity(self, entity: LightEntity):
        with self._lock:
            self.lights.append(entity)

    def add_cover_entity(self, entity: CoverEntity):
        self.covers.append(entity)

    async def _background_task(self):
        # 请求服务器并保存数据
        ip_addr = "192.168.88.118"
        server_data = await _request_data_from_server(ip_addr)
        if server_data is None:
            return
        self._scheduler.shutdown()

        with self._lock:
            for light in self.lights:
                swi = server_data.get("attributes").get(light._mac).get("SWI")
                if swi is not None:
                    bits = int(light._pos)
                    status = int(swi, 0)
                    while bits > 1:
                        status >>= 1
                        bits -= 1
                    light._attr_is_on = status & 1 == 1
                    light.schedule_update_ha_state()
                    # _LOGGER.warning(f"request_data light._attr_is_on={light._attr_is_on} bits={bits} status={status}")

            for cover in self.covers:
                status = server_data.get("attributes").get(cover._mac).get("WIN")
                if status == "CLOSE":
                    cover._attr_is_closed = True
                    cover._attr_current_cover_position = 0
                elif status == "OPEN":
                    cover._attr_is_closed = False
                    cover._attr_current_cover_position = 100
                elif status == "STOP":
                    cover._attr_is_closed = False
                    cover._attr_current_cover_position = 50
                cover.schedule_update_ha_state()

    def handle_gateway_data(self, data: dict):
        # Received {"sourceId":"301B976FB162","req":"heart","requestType":"update","serialNum":-1,"attributes":
        # {"SWI":"0X00","MAC":"FFFF301B977B72F1","GRP":"00","data":"","LIVE":"ON","NAM":"厨房面板","KEY":"2","RSSI":"-64",
        # "RLT":"0000","TYP":"SW-KY2","SAV":"DO"},"id":"FFFF301B977B72F1"}
        if data.get("requestType") == "update" and data.get("attributes") is not None:
            attributes = data.get("attributes")
            mac = data.get("id")
            with self._lock:
                for light in self.lights:
                    if light._mac == mac or light._mac2 == mac:
                        swi = attributes.get("SWI")
                        if swi is not None:
                            bits = int(light._pos if light._mac == mac else light._pos2)
                            status = int(swi, 0)
                            while bits > 1:
                                status >>= 1
                                bits -= 1
                            is_on = status & 1 == 1
                            if light._attr_is_on != is_on:
                                light._attr_is_on = is_on
                                light.schedule_update_ha_state()
                                # _LOGGER.error(f"handle_gateway_data light._attr_is_on={light._attr_is_on} bits={bits} status={status}")

                for cover in self.covers:
                    if (
                        cover._mac == mac
                        and not cover.is_opening
                        and not cover.is_closing
                    ):
                        status = attributes.get("WIN")
                        if status == "CLOSE":
                            cover._attr_is_closed = True
                            cover._attr_current_cover_position = 0
                        elif status == "OPEN":
                            cover._attr_is_closed = False
                            cover._attr_current_cover_position = 100
                        elif status == "STOP":
                            cover._attr_is_closed = False
                            cover._attr_current_cover_position = 50
                        if status is not None:
                            cover.schedule_update_ha_state()


ym_singleton = YunMaoDataSingleton()
