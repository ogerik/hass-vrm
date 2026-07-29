#!/usr/bin/env python3
"""Maakt een Lovelace-dashboard (storage-mode, in de zijbalk) aan via de
WS-API. Idempotent: bestaat er al een dashboard met dat url_path, dan wordt dat
gemeld en stopt het script met exit 0.

Gebruik: python3 create_dashboard.py <url_path> <titel> [icon]
Bijv.:   python3 create_dashboard.py victron-vrm VRM mdi:sine-wave

Let op: HA eist een koppelteken in url_path (bv. "victron-vrm").
"""
import asyncio
import sys

from ha_ws import HAClient, load_env


async def create(env: dict, url_path: str, title: str, icon: str) -> bool:
    """True = aangemaakt, False = bestond al."""
    async with HAClient(env["HA_URL"], env["HA_TOKEN"]) as client:
        dashboards = await client.cmd(type="lovelace/dashboards/list")
        if any(d.get("url_path") == url_path for d in dashboards):
            return False
        await client.cmd(
            type="lovelace/dashboards/create",
            url_path=url_path,
            title=title,
            icon=icon,
            show_in_sidebar=True,
            mode="storage",
            require_admin=False,
        )
        return True


async def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__.strip())
    url_path, title = sys.argv[1], sys.argv[2]
    icon = sys.argv[3] if len(sys.argv) == 4 else "mdi:view-dashboard"

    env = load_env()
    last_err = None
    for attempt in range(1, 4):  # Nabu Casa reset af en toe de verbinding
        try:
            created = await create(env, url_path, title, icon)
            break
        except Exception as e:
            last_err = e
            print(f"  poging {attempt} mislukt ({type(e).__name__}); opnieuw...")
            await asyncio.sleep(3)
    else:
        sys.exit(f"Aanmaken van dashboard '{url_path}' mislukt na 3 pogingen: {last_err}")

    if created:
        print(f"Dashboard '{url_path}' ({title}) aangemaakt, zichtbaar in de zijbalk")
    else:
        print(f"Dashboard '{url_path}' bestaat al; niets gedaan")


if __name__ == "__main__":
    asyncio.run(main())
