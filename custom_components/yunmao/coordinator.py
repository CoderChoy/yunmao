"""Coordinators and push listener management for Yun Mao."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import YunMaoClient, YunMaoClientError
from .const import (
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PUSH_FALLBACK_IDLE_SECONDS,
    PUSH_PORT,
    YunMaoCoverDescription,
    YunMaoLightDescription,
    get_cover_descriptions,
    get_light_descriptions,
)

_LOGGER = logging.getLogger(__name__)
_PUSH_SERVER = "push_server"
_MOTION_WINDOW_SECONDS = 4

PushListener = Callable[[dict[str, Any]], None]


@dataclass(frozen=True, slots=True)
class YunMaoCoordinatorData:
    """Raw gateway state cached by the coordinator."""

    switch_states: dict[str, int] = field(default_factory=dict)
    cover_states: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class YunMaoCoverState:
    """Derived cover state exposed to entities."""

    current_position: int
    is_closed: bool
    is_opening: bool
    is_closing: bool


@dataclass(slots=True)
class YunMaoRuntimeData:
    """Runtime data attached to a config entry."""

    client: YunMaoClient
    coordinator: "YunMaoCoordinator"


YunMaoConfigEntry = ConfigEntry[YunMaoRuntimeData]


class YunMaoPushServer:
    """Shared TCP listener used for gateway push updates."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._listeners: set[PushListener] = set()
        self._lock = asyncio.Lock()
        self._server: asyncio.AbstractServer | None = None

    async def async_add_listener(self, listener: PushListener) -> Callable[[], None]:
        """Register a push listener and start the server when needed."""

        async with self._lock:
            self._listeners.add(listener)
            if self._server is None:
                await self._async_start_locked()

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)
            if not self._listeners:
                self._hass.async_create_task(self.async_stop())

        return remove_listener

    async def async_stop(self) -> None:
        """Stop the shared push server if it is no longer needed."""

        async with self._lock:
            if self._listeners or self._server is None:
                return

            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _async_start_locked(self) -> None:
        """Start the push server while holding the lock."""

        try:
            self._server = await asyncio.start_server(
                self._async_handle_client, host="0.0.0.0", port=PUSH_PORT
            )
        except OSError as err:
            _LOGGER.warning(
                "Unable to bind Yun Mao push listener on port %s, polling fallback will be used: %s",
                PUSH_PORT,
                err,
            )
            self._server = None

    async def _async_handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a gateway push connection."""

        buffer = ""

        try:
            while True:
                data = await asyncio.wait_for(reader.read(8192), timeout=120)
                if not data:
                    break

                buffer += data.decode("utf-8", errors="ignore")
                buffer = self._process_buffer(buffer)
        except asyncio.TimeoutError:
            _LOGGER.debug("Closing idle Yun Mao push connection")
        except OSError as err:
            _LOGGER.debug("Yun Mao push connection closed: %s", err)
        finally:
            if buffer.strip():
                self._dispatch_line(buffer.strip())
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    def _process_buffer(self, buffer: str) -> str:
        """Process any complete lines buffered from the TCP stream."""

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line:
                self._dispatch_line(line)

        return buffer

    def _dispatch_line(self, line: str) -> None:
        """Dispatch a single JSON payload to registered listeners."""

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            _LOGGER.debug("Ignoring invalid Yun Mao push payload: %s", line)
            return

        if not isinstance(payload, dict):
            return

        for listener in tuple(self._listeners):
            try:
                listener(payload)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unhandled Yun Mao push listener error")


def async_get_push_server(hass: HomeAssistant) -> YunMaoPushServer:
    """Return the shared Yun Mao push server."""

    domain_data = hass.data.setdefault(DOMAIN, {})

    if _PUSH_SERVER not in domain_data:
        domain_data[_PUSH_SERVER] = YunMaoPushServer(hass)

    return domain_data[_PUSH_SERVER]


class YunMaoCoordinator(DataUpdateCoordinator[YunMaoCoordinatorData]):
    """Coordinate Yun Mao gateway state updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: YunMaoClient,
        entry_data: dict[str, Any],
    ) -> None:
        self.client = client
        self.light_descriptions = get_light_descriptions(entry_data)
        self.cover_descriptions = get_cover_descriptions(entry_data)
        self._known_light_macs = {
            desc.primary_mac for desc in self.light_descriptions
        } | {
            desc.secondary_mac
            for desc in self.light_descriptions
            if desc.secondary_mac is not None
        }
        self._known_cover_macs = {desc.mac for desc in self.cover_descriptions}
        self._cover_positions: dict[str, int] = {}
        self._cover_motion_deadlines: dict[str, tuple[str, float]] = {}
        self._last_gateway_event_monotonic: float | None = None
        self._last_push_monotonic: float | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{client.host}",
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )

    async def _async_update_data(self) -> YunMaoCoordinatorData:
        """Fetch fresh state from the gateway."""

        if self.data is not None and not self._should_query_gateway():
            return self.data

        try:
            data = self._parse_query_payload(await self.client.async_fetch_state())
        except YunMaoClientError as err:
            raise UpdateFailed(str(err)) from err

        self._last_gateway_event_monotonic = monotonic()
        return data

    def handle_push_payload(self, payload: dict[str, Any]) -> None:
        """Merge gateway push data into the cached state."""

        self._last_gateway_event_monotonic = monotonic()

        if payload.get("requestType") != "update":
            return

        mac = payload.get("id")
        attributes = payload.get("attributes")

        if not isinstance(mac, str) or not isinstance(attributes, dict):
            return

        self._last_push_monotonic = monotonic()

        switch_states = dict(self.data.switch_states) if self.data else {}
        cover_states = dict(self.data.cover_states) if self.data else {}
        updated = False

        if mac in self._known_light_macs and (raw_switch := attributes.get("SWI")) is not None:
            try:
                switch_states[mac] = int(str(raw_switch), 0)
                updated = True
            except ValueError:
                _LOGGER.debug("Ignoring invalid light payload for %s: %s", mac, raw_switch)

        if mac in self._known_cover_macs and isinstance(attributes.get("WIN"), str):
            status = attributes["WIN"]
            cover_states[mac] = status
            self._update_cover_position_cache(mac, status)
            updated = True

        if updated:
            self.async_set_updated_data(
                YunMaoCoordinatorData(
                    switch_states=switch_states,
                    cover_states=cover_states,
                )
            )

    def is_light_on(self, description: YunMaoLightDescription) -> bool | None:
        """Return the current logical light state."""

        if self.data is None:
            return None

        values = [
            self._switch_bit_is_on(self.data.switch_states.get(description.primary_mac), description.primary_pos)
        ]

        if description.secondary_mac is not None and description.secondary_pos is not None:
            values.append(
                self._switch_bit_is_on(
                    self.data.switch_states.get(description.secondary_mac),
                    description.secondary_pos,
                )
            )

        known_values = [value for value in values if value is not None]
        if not known_values:
            return None

        return any(known_values)

    def get_cover_state(self, description: YunMaoCoverDescription) -> YunMaoCoverState:
        """Return the derived cover state for an entity."""

        status = self.data.cover_states.get(description.mac) if self.data else None
        position = self._cover_positions.get(description.mac, 50)

        if status == "OPEN":
            position = 100
        elif status == "CLOSE":
            position = 0
        elif status == "STOP" and description.mac not in self._cover_positions:
            position = 50

        is_opening, is_closing = self._get_cover_motion(description.mac)

        return YunMaoCoverState(
            current_position=position,
            is_closed=position == 0,
            is_opening=is_opening,
            is_closing=is_closing,
        )

    async def async_set_light_state(
        self, description: YunMaoLightDescription, is_on: bool
    ) -> None:
        """Send a light command and update local state optimistically."""

        try:
            await self.client.async_set_light_state(
                description.primary_mac, description.primary_pos, is_on
            )
            if description.secondary_mac is not None and description.secondary_pos is not None:
                await self.client.async_set_light_state(
                    description.secondary_mac, description.secondary_pos, is_on
                )
        except YunMaoClientError as err:
            raise HomeAssistantError(str(err)) from err

        if self.data is None:
            return

        switch_states = dict(self.data.switch_states)
        switch_states[description.primary_mac] = self._set_switch_bit(
            switch_states.get(description.primary_mac, 0),
            description.primary_pos,
            is_on,
        )

        if description.secondary_mac is not None and description.secondary_pos is not None:
            switch_states[description.secondary_mac] = self._set_switch_bit(
                switch_states.get(description.secondary_mac, 0),
                description.secondary_pos,
                is_on,
            )

        self.async_set_updated_data(
            YunMaoCoordinatorData(
                switch_states=switch_states,
                cover_states=dict(self.data.cover_states),
            )
        )

    async def async_open_cover(self, description: YunMaoCoverDescription) -> None:
        """Open a cover."""

        await self._async_set_cover_status(description, "OPEN")
        self._cover_positions[description.mac] = 100
        self._cover_motion_deadlines[description.mac] = (
            "opening",
            monotonic() + _MOTION_WINDOW_SECONDS,
        )

    async def async_close_cover(self, description: YunMaoCoverDescription) -> None:
        """Close a cover."""

        await self._async_set_cover_status(description, "CLOSE")
        self._cover_positions[description.mac] = 0
        self._cover_motion_deadlines[description.mac] = (
            "closing",
            monotonic() + _MOTION_WINDOW_SECONDS,
        )

    async def async_stop_cover(self, description: YunMaoCoverDescription) -> None:
        """Stop a cover."""

        await self._async_set_cover_status(description, "STOP")
        self._cover_motion_deadlines.pop(description.mac, None)
        self._cover_positions.setdefault(description.mac, 50)

    async def async_set_cover_position(
        self, description: YunMaoCoverDescription, position: int
    ) -> None:
        """Set a cover target position."""

        try:
            await self.client.async_set_cover_position(description.mac, position)
        except YunMaoClientError as err:
            raise HomeAssistantError(str(err)) from err

        current_position = self.get_cover_state(description).current_position
        if position > current_position:
            self._cover_motion_deadlines[description.mac] = (
                "opening",
                monotonic() + _MOTION_WINDOW_SECONDS,
            )
        elif position < current_position:
            self._cover_motion_deadlines[description.mac] = (
                "closing",
                monotonic() + _MOTION_WINDOW_SECONDS,
            )
        else:
            self._cover_motion_deadlines.pop(description.mac, None)

        self._cover_positions[description.mac] = position

        if self.data is None:
            return

        cover_states = dict(self.data.cover_states)
        cover_states[description.mac] = "STOP"
        self.async_set_updated_data(
            YunMaoCoordinatorData(
                switch_states=dict(self.data.switch_states),
                cover_states=cover_states,
            )
        )

    def diagnostics_data(self) -> dict[str, Any]:
        """Return non-sensitive coordinator diagnostics."""

        return {
            "host_reachable": self.last_update_success,
            "push_fallback_idle_seconds": PUSH_FALLBACK_IDLE_SECONDS,
            "seconds_since_last_gateway_event": self._seconds_since(
                self._last_gateway_event_monotonic
            ),
            "seconds_since_last_push": self._seconds_since(self._last_push_monotonic),
            "light_count": len(self.light_descriptions),
            "cover_count": len(self.cover_descriptions),
            "known_light_macs": len(self._known_light_macs),
            "known_cover_macs": len(self._known_cover_macs),
            "switch_state_count": len(self.data.switch_states) if self.data else 0,
            "cover_state_count": len(self.data.cover_states) if self.data else 0,
        }

    async def _async_set_cover_status(
        self, description: YunMaoCoverDescription, status: str
    ) -> None:
        """Send a cover command and update local state optimistically."""

        try:
            await self.client.async_set_cover_status(description.mac, status)
        except YunMaoClientError as err:
            raise HomeAssistantError(str(err)) from err

        if self.data is None:
            return

        cover_states = dict(self.data.cover_states)
        cover_states[description.mac] = status
        self.async_set_updated_data(
            YunMaoCoordinatorData(
                switch_states=dict(self.data.switch_states),
                cover_states=cover_states,
            )
        )

    def _parse_query_payload(self, payload: dict[str, Any]) -> YunMaoCoordinatorData:
        """Parse the query response into cached raw state."""

        attributes = payload.get("attributes")
        if not isinstance(attributes, dict):
            raise UpdateFailed("Yun Mao gateway response is missing attributes")

        switch_states = dict(self.data.switch_states) if self.data else {}
        cover_states = dict(self.data.cover_states) if self.data else {}

        for mac, state in attributes.items():
            if not isinstance(mac, str) or not isinstance(state, dict):
                continue

            if mac in self._known_light_macs and (raw_switch := state.get("SWI")) is not None:
                try:
                    switch_states[mac] = int(str(raw_switch), 0)
                except ValueError:
                    _LOGGER.debug("Ignoring invalid switch value from gateway: %s", raw_switch)

            if mac in self._known_cover_macs and isinstance(state.get("WIN"), str):
                status = state["WIN"]
                cover_states[mac] = status
                self._update_cover_position_cache(mac, status)

        return YunMaoCoordinatorData(
            switch_states=switch_states,
            cover_states=cover_states,
        )

    def _get_cover_motion(self, mac: str) -> tuple[bool, bool]:
        """Return transient cover movement flags."""

        motion = self._cover_motion_deadlines.get(mac)
        if motion is None:
            return False, False

        direction, deadline = motion
        if deadline <= monotonic():
            self._cover_motion_deadlines.pop(mac, None)
            return False, False

        return direction == "opening", direction == "closing"

    def _update_cover_position_cache(self, mac: str, status: str) -> None:
        """Keep the optimistic cover position in sync with coarse status updates."""

        if status == "OPEN":
            self._cover_positions[mac] = 100
            self._cover_motion_deadlines.pop(mac, None)
        elif status == "CLOSE":
            self._cover_positions[mac] = 0
            self._cover_motion_deadlines.pop(mac, None)
        elif status == "STOP":
            self._cover_motion_deadlines.pop(mac, None)
            self._cover_positions.setdefault(mac, 50)

    def _should_query_gateway(self) -> bool:
        """Return True when polling should fall back to a direct gateway query."""

        if self._last_gateway_event_monotonic is None:
            return True

        return (
            monotonic() - self._last_gateway_event_monotonic
            >= PUSH_FALLBACK_IDLE_SECONDS
        )

    @staticmethod
    def _seconds_since(last_seen: float | None) -> int | None:
        """Return the whole-second age of a monotonic timestamp."""

        if last_seen is None:
            return None

        return int(monotonic() - last_seen)

    @staticmethod
    def _switch_bit_is_on(status: int | None, pos: int) -> bool | None:
        """Return the value of a single switch bit."""

        if status is None:
            return None
        return bool((status >> (pos - 1)) & 1)

    @staticmethod
    def _set_switch_bit(status: int, pos: int, is_on: bool) -> int:
        """Set or clear a single switch bit."""

        mask = 1 << (pos - 1)
        if is_on:
            return status | mask
        return status & ~mask
