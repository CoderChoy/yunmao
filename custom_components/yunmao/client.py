"""TCP client for Yun Mao gateways."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .const import GATEWAY_PORT

COMMAND_SERIAL = "210431"
QUERY_ID = "0000000000000000"


class YunMaoClientError(HomeAssistantError):
    """Base Yun Mao client error."""


class YunMaoConnectionError(YunMaoClientError):
    """Raised when the Yun Mao gateway is unavailable."""


class YunMaoProtocolError(YunMaoClientError):
    """Raised when the Yun Mao gateway response is invalid."""


class YunMaoClient:
    """Async Yun Mao TCP client."""

    def __init__(self, host: str) -> None:
        self.host = host

    async def async_fetch_state(self) -> dict[str, Any]:
        """Fetch the latest gateway state."""

        response = await self._async_request(
            {
                "sourceId": self.host,
                "serialNum": self.host,
                "requestType": "query",
                "id": QUERY_ID,
            },
            expect_response=True,
        )
        if response is None:
            raise YunMaoProtocolError("Missing Yun Mao gateway response")
        return response

    async def async_set_light_state(self, mac: str, pos: int, is_on: bool) -> None:
        """Set a light channel state."""

        await self._async_request(
            {
                "sourceId": self.host,
                "serialNum": COMMAND_SERIAL,
                "requestType": "cmd",
                "id": mac,
                "attributes": {f"KY{pos}": "ON" if is_on else "OFF"},
            },
            expect_response=False,
        )

    async def async_set_cover_status(self, mac: str, status: str) -> None:
        """Set a cover status command."""

        await self._async_request(
            {
                "sourceId": self.host,
                "serialNum": COMMAND_SERIAL,
                "requestType": "cmd",
                "id": mac,
                "attributes": {"WIN": status},
            },
            expect_response=False,
        )

    async def async_set_cover_position(self, mac: str, position: int) -> None:
        """Set a cover target position."""

        await self._async_request(
            {
                "sourceId": self.host,
                "serialNum": COMMAND_SERIAL,
                "requestType": "cmd",
                "id": mac,
                "attributes": {"LEV": str(position)},
            },
            expect_response=False,
        )

    async def _async_request(
        self, payload: dict[str, Any], expect_response: bool
    ) -> dict[str, Any] | None:
        """Send a request to the gateway."""

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host=self.host, port=GATEWAY_PORT), timeout=5
            )
        except (asyncio.TimeoutError, OSError) as err:
            raise YunMaoConnectionError("Unable to connect to the Yun Mao gateway") from err

        try:
            writer.write(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            await asyncio.wait_for(writer.drain(), timeout=5)

            if writer.can_write_eof():
                writer.write_eof()

            if not expect_response:
                return None

            response = await self._async_read_response(reader)
            try:
                decoded = json.loads(response.decode("utf-8"))
            except json.JSONDecodeError as err:
                raise YunMaoProtocolError("Invalid response from the Yun Mao gateway") from err

            if not isinstance(decoded, dict):
                raise YunMaoProtocolError("Unexpected response type from the Yun Mao gateway")

            return decoded
        except asyncio.TimeoutError as err:
            raise YunMaoConnectionError("Timed out while talking to the Yun Mao gateway") from err
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def _async_read_response(self, reader: asyncio.StreamReader) -> bytes:
        """Read the full response body from the gateway."""

        payload = bytearray()

        while True:
            chunk = await asyncio.wait_for(reader.read(8192), timeout=5)
            if not chunk:
                break
            payload.extend(chunk)

        if not payload:
            raise YunMaoProtocolError("Empty response from the Yun Mao gateway")

        return bytes(payload)
