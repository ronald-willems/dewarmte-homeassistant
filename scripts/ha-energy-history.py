#!/usr/bin/env python3
"""Read-only checks of the imported energy history on a real Home Assistant.

Reads ha_api_url from deploy.local.yaml and ha_api_token from secrets.yaml, like
the other ha-* scripts. Statistic ids and the config entry are looked up, not
hardcoded, so it works for any account. Run from the repo root:

    python scripts/ha-energy-history.py totals          # kWh per series + metadata
    python scripts/ha-energy-history.py dst             # stored hours on DST days (23/25)
    python scripts/ha-energy-history.py align 2026-10-31 [day ...]
                                                        # imported hours vs the live energy sensor
    python scripts/ha-energy-history.py status          # bell notifications + options-screen status

It never writes: delete and re-import go through the options screen.
"""
from __future__ import annotations

import argparse
import asyncio
import socket
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import aiohttp
import yaml

NL = ZoneInfo("Europe/Amsterdam")
# Electricity is what the live sensor and the import both measure.
LIVE_SENSOR_SUFFIX = "_electricity_consumption_energy"
IMPORTED_SUFFIX = "_electricity_consumed"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("totals", help="kWh per imported series, with its metadata")
    dst = sub.add_parser("dst", help="stored hours on each daylight-saving day")
    dst.add_argument("--from-year", type=int, default=2023)
    align = sub.add_parser("align", help="imported hours vs the live energy sensor")
    align.add_argument("days", nargs="+", type=date.fromisoformat)
    sub.add_parser("status", help="bell notifications and the options-screen status")
    args = parser.parse_args()
    asyncio.run(HomeAssistant.run(args))


class HomeAssistant:
    """A websocket + REST session against the configured Home Assistant."""

    def __init__(self, session: aiohttp.ClientSession, ws: aiohttp.ClientWebSocketResponse,
                 base_url: str, token: str) -> None:
        self._session = session
        self._ws = ws
        self._base_url = base_url
        self._headers = {"Authorization": f"Bearer {token}"}
        self._next_id = 0

    @classmethod
    async def run(cls, args: argparse.Namespace) -> None:
        base_url, token = _connection_settings()
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(base_url.replace("http", "ws", 1) + "/api/websocket") as ws:
                await ws.receive_json()
                await ws.send_json({"type": "auth", "access_token": token})
                if (await ws.receive_json())["type"] != "auth_ok":
                    raise SystemExit("Home Assistant rejected the token in secrets.yaml")
                ha = cls(session, ws, base_url, token)
                await getattr(ha, args.command)(args)

    # --- commands -------------------------------------------------------

    async def totals(self, _args: argparse.Namespace) -> None:
        for meta in await self._imported_statistics():
            rows = await self._statistics([meta["statistic_id"]], "month", "change",
                                          start=datetime(2000, 1, 1, tzinfo=timezone.utc))
            total = sum(r["change"] or 0 for r in rows.get(meta["statistic_id"], []))
            print(f"{meta['statistic_id']}: {total:.2f} kWh over {len(rows.get(meta['statistic_id'], []))} months"
                  f"  (unit_class={meta.get('unit_class')}, mean_type={meta.get('mean_type')})")

    async def dst(self, args: argparse.Namespace) -> None:
        stat_id = next(m["statistic_id"] for m in await self._imported_statistics()
                       if m["statistic_id"].endswith("_heat_supplied"))
        for day in _dst_days(args.from_year):
            start, end = _dutch_day(day)
            rows = (await self._statistics([stat_id], "hour", "state", start=start, end=end)).get(stat_id, [])
            expected = int((end - start) / timedelta(hours=1))
            flag = "" if len(rows) in (0, expected) else "  <-- unexpected"
            print(f"{day}: {len(rows)} hours stored, {expected} in that Dutch day{flag}")
        print("(0 hours means DeWarmte has no data for that day)")

    async def align(self, args: argparse.Namespace) -> None:
        meta = [m for m in await self._imported_statistics() if m["statistic_id"].endswith(IMPORTED_SUFFIX)]
        if len(meta) != 1:
            raise SystemExit(f"Expected one imported electricity series, found {len(meta)}")
        imported = [meta[0]["statistic_id"]]
        # The import is named "<device name> Electricity consumed"; the live
        # sensor's entity id starts with the same device name.
        device_name = meta[0]["name"].removesuffix(" Electricity consumed")
        live_id = f"sensor.{_slug(device_name)}{LIVE_SENSOR_SUFFIX}"
        live = [m["statistic_id"] for m in await self._all_statistics() if m["statistic_id"] == live_id]
        if not live:
            raise SystemExit(f"No live sensor {live_id} in the recorder")
        worst = 0.0
        for day in args.days:
            start, end = _dutch_day(day)
            rows = await self._statistics(imported + live, "hour", "change", start=start, end=end)
            by_hour = {sid: {r["start"]: r["change"] or 0 for r in rows.get(sid, [])} for sid in imported + live}
            print(f"== {day}")
            for ts in sorted(set(by_hour[imported[0]]) | set(by_hour[live[0]])):
                got, want = by_hour[imported[0]].get(ts), by_hour[live[0]].get(ts)
                if got is not None and want is not None:
                    worst = max(worst, abs(got - want))
                hour = datetime.fromtimestamp(ts / 1000, timezone.utc).astimezone(NL)
                print(f"  {hour:%H:00}  imported {_kwh(got)}  live sensor {_kwh(want)}")
        print(f"largest hourly difference: {worst:.2f} kWh (a shifted hour shows up as ~1 kWh)")

    async def status(self, _args: argparse.Namespace) -> None:
        notes = await self._call({"type": "persistent_notification/get"})
        for note in notes:
            if note["notification_id"].startswith("dewarmte_energy_history"):
                print(f"bell: {note['message']}")
        for entry in await self._rest("GET", "/api/config/config_entries/entry?domain=dewarmte"):
            flow = await self._rest("POST", "/api/config/config_entries/options/flow",
                                    {"handler": entry["entry_id"]})
            try:
                menu = await self._rest("POST", f"/api/config/config_entries/options/flow/{flow['flow_id']}",
                                        {"next_step_id": "energy_history"})
                print(f"options screen ({entry['title']}): {menu['description_placeholders']['status']}")
            finally:
                await self._rest("DELETE", f"/api/config/config_entries/options/flow/{flow['flow_id']}")

    # --- plumbing -------------------------------------------------------

    async def _imported_statistics(self) -> list[dict[str, Any]]:
        found = [m for m in await self._all_statistics() if m["statistic_id"].startswith("dewarmte:")]
        if not found:
            raise SystemExit("No dewarmte: statistics found; is the import switched on?")
        return found

    async def _all_statistics(self) -> list[dict[str, Any]]:
        return await self._call({"type": "recorder/list_statistic_ids"})

    async def _statistics(self, ids: list[str], period: str, kind: str, *,
                          start: datetime, end: datetime | None = None) -> dict[str, list]:
        message = {"type": "recorder/statistics_during_period", "statistic_ids": ids,
                   "period": period, "types": [kind], "start_time": start.isoformat()}
        if end is not None:
            message["end_time"] = end.isoformat()
        return await self._call(message)

    async def _call(self, message: dict[str, Any]) -> Any:
        self._next_id += 1
        await self._ws.send_json({"id": self._next_id, **message})
        reply = await self._ws.receive_json()
        if not reply.get("success"):
            raise SystemExit(f"{message['type']} failed: {reply.get('error')}")
        return reply["result"]

    async def _rest(self, method: str, path: str, body: dict | None = None) -> Any:
        async with self._session.request(method, self._base_url + path, json=body,
                                         headers=self._headers) as response:
            response.raise_for_status()
            return await response.json() if response.content_type == "application/json" else None


def _connection_settings() -> tuple[str, str]:
    """URL from deploy.local.yaml, token from secrets.yaml.

    A `.local` host is resolved up front: the system resolver knows mDNS, but
    aiohttp's own resolver may not.
    """
    with open("deploy.local.yaml", encoding="utf-8") as f:
        url = urlsplit(yaml.safe_load(f)["ha_api_url"].rstrip("/"))
    with open("secrets.yaml", encoding="utf-8") as f:
        token = yaml.safe_load(f)["ha_api_token"]
    host = socket.gethostbyname(url.hostname)
    return f"{url.scheme}://{host}:{url.port or 8123}", token


def _dutch_day(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=NL).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=NL).astimezone(timezone.utc)
    return start, end


def _dst_days(from_year: int) -> list[date]:
    """The last Sundays of March and October: the 23- and 25-hour days."""
    days = []
    for year in range(from_year, date.today().year + 1):
        for month in (3, 10):
            last = date(year, month, 31)
            days.append(last - timedelta(days=(last.weekday() + 1) % 7))
    return [d for d in days if d <= date.today()]


def _slug(name: str) -> str:
    """Home Assistant's entity-id slug, close enough for device names."""
    return "_".join("".join(c if c.isalnum() else " " for c in name.lower()).split())


def _kwh(value: float | None) -> str:
    return "    -" if value is None else f"{value:5.2f}"


if __name__ == "__main__":
    main()
