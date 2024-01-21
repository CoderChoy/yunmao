import asyncio
from io import BytesIO
import json
import logging
import threading

from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
        self.data_cache = {}
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._background_task, "interval", seconds=2, max_instances=1
        )
        self._scheduler.start()

    async def _background_task(self):
        # 请求服务器并保存数据
        ip_addr = "192.168.88.118"
        server_data = await _request_data_from_server(ip_addr)
        # 保存数据到 data_cache 变量
        with self._lock:
            self.data_cache[ip_addr] = server_data

    def get_data_cache(self, ip_addr: str):
        with self._lock:
            return self.data_cache.get(ip_addr)


ym_singleton = YunMaoDataSingleton()
