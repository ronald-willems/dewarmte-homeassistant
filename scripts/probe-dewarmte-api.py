#!/usr/bin/env python3
"""Read-only probe of the live DeWarmte API using the integration's own client.

Logs in with tests/secrets.yaml, then GETs devices / status / settings and runs
them through the real parsers. Use this to:
  - confirm the integration still parses the live API (first thing to run when
    users report breakage after a DeWarmte-side change), and
  - inspect the current response shapes.

It performs GET requests only and NEVER writes settings. Run from the repo root:
    python scripts/probe-dewarmte-api.py
"""
from __future__ import annotations

import asyncio
import os
import sys

import aiohttp
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.api.client import DeWarmteApiClient
from custom_components.dewarmte.api.models.config import ConnectionSettings


def _load_credentials() -> tuple[str, str]:
    with open("tests/secrets.yaml", encoding="utf-8") as f:
        dw = yaml.safe_load(f)["dewarmte"]
    return dw["username"], dw["password"]


async def main() -> int:
    username, password = _load_credentials()
    async with aiohttp.ClientSession() as session:
        client = DeWarmteApiClient(
            ConnectionSettings(username=username, password=password, update_interval=60),
            session,
        )

        devices = await client.async_discover_devices()
        if not devices:
            print("No devices discovered (login failed or account empty).")
            return 1
        print(f"Discovered {len(devices)} device(s):")
        for d in devices:
            print(f"  - {d.device_id}  product_id={d.product_id!r}  cooling={d.supports_cooling}")

        for device in devices:
            print(f"\n=== {device.device_id} ===")
            status = await client.async_get_status_data(device)
            print("status parsed:", "OK" if status else "FAILED (returned None)")

            settings = await client.async_get_operation_settings(device)
            if settings is None:
                print("settings parsed: FAILED (returned None) -- likely an API schema change")
                return 1
            print("settings parsed: OK")
            # Print a few fields most likely to shift when the API changes.
            for field in (
                "cooling_thermostat_type", "cooling_control_mode", "cooling_temperature",
                "cooling_schedules", "is_force_cooling_active",
                "force_cooling_temperature", "force_cooling_end", "version",
            ):
                print(f"  {field} = {getattr(settings, field, '<missing>')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
