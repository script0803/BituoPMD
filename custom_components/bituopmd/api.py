"""Async HTTP client for Bituo power monitoring devices."""

from __future__ import annotations

import asyncio
from ipaddress import ip_address
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import REQUEST_TIMEOUT


class BituoApiError(Exception):
    """Base class for Bituo API errors."""


class BituoApiConnectionError(BituoApiError):
    """Raised when a device cannot be reached."""


class BituoApiResponseError(BituoApiError):
    """Raised when a device returns an invalid response."""


def normalize_host(host: str) -> str:
    """Validate and normalize the IPv4 or IPv6 address used by a device."""
    value = host.strip()
    try:
        return str(ip_address(value))
    except ValueError as err:
        raise BituoApiResponseError("A valid IP address is required") from err


class BituoApiClient:
    """Small async client for the device's local HTTP API."""

    def __init__(self, session: ClientSession, host: str) -> None:
        """Initialize the client."""
        self._session = session
        self.host = normalize_host(host)
        bracketed_host = f"[{self.host}]" if ":" in self.host else self.host
        self._base_url = f"http://{bracketed_host}"

    async def async_get_data(self) -> dict[str, Any]:
        """Return the primary metering payload."""
        payload = await self._async_request_json("GET", "data")
        if not isinstance(payload, dict) or not payload:
            raise BituoApiResponseError("Device returned an empty metering payload")
        return payload

    async def async_get_auxiliary_data(self) -> dict[str, Any]:
        """Return the optional Home Assistant capability payload."""
        payload = await self._async_request_json("GET", "hadata")
        if not isinstance(payload, dict):
            raise BituoApiResponseError("Device returned an invalid capability payload")
        return payload

    async def async_get_switch_state(self) -> bool:
        """Return the relay state exposed by switch-capable models."""
        payload = await self._async_request("GET", "status")
        text = payload.strip().lower()
        if text in {"true", "on", "1"}:
            return True
        if text in {"false", "off", "0"}:
            return False
        raise BituoApiResponseError("Device returned an invalid switch state")

    async def async_get_action(self, action: str) -> str:
        """Run an explicitly validated GET action."""
        return await self._async_request("GET", action)

    async def async_post_action(self, action: str, data: dict[str, Any]) -> str:
        """Run an explicitly validated POST action."""
        return await self._async_request("POST", action, json=data)

    async def _async_request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        """Request and decode a JSON response."""
        raw = await self._async_request(method, path, **kwargs)
        try:
            import json

            return json.loads(raw)
        except (TypeError, ValueError) as err:
            raise BituoApiResponseError(
                f"Device returned invalid JSON from /{path}"
            ) from err

    async def _async_request(self, method: str, path: str, **kwargs: Any) -> str:
        """Perform one bounded local API request."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.request(
                    method, f"{self._base_url}/{path}", **kwargs
                )
                response.raise_for_status()
                return await response.text()
        except TimeoutError as err:
            raise BituoApiConnectionError(
                f"Timed out communicating with {self.host}"
            ) from err
        except ClientResponseError as err:
            raise BituoApiResponseError(
                f"Device {self.host} returned HTTP {err.status}"
            ) from err
        except ClientError as err:
            raise BituoApiConnectionError(
                f"Unable to communicate with {self.host}"
            ) from err
