#!/usr/bin/env python3
"""Voegt een view (YAML-bestand) toe aan een bestaand Lovelace-dashboard, of
vervangt hem op basis van `path`. Idempotent: bestaat er al een view met
hetzelfde `path`, dan wordt die op zijn bestaande plek vervangen (tab-volgorde
blijft behouden); een nieuwe view komt achteraan.

Met `--remove` wordt juist de view met dat path uit het dashboard gefilterd;
de overige views blijven intact. Ook idempotent: bestaat de view niet (meer),
dan wordt dat gemeld en stopt het script met exit 0.

Gebruik: python3 apply_dashboard.py <dashboard_url_path> <view.yaml>
         python3 apply_dashboard.py <dashboard_url_path> --remove <view_path>
Bijv.:   python3 apply_dashboard.py victron-vrm ha-config/vrm-view.yaml
         python3 apply_dashboard.py energie-plus --remove vrm
"""
import asyncio
import sys

import yaml

from ha_ws import HAClient, load_env


async def _load_config(client: HAClient, url_path: str) -> dict:
    try:
        cfg = await client.cmd(type="lovelace/config", url_path=url_path)
    except RuntimeError as e:
        # Vers (storage-)dashboard zonder opgeslagen config: begin leeg.
        if "config_not_found" in str(e):
            return {"views": []}
        raise
    # HAClient.cmd geeft msg["result"] terug; dat is de config zelf
    # ({"views": [...]}). Guard voor het geval een HA-versie de config
    # alsnog in een "config"-key wikkelt.
    if "views" not in cfg and isinstance(cfg.get("config"), dict):
        cfg = cfg["config"]
    return cfg


async def apply(env: dict, url_path: str, view: dict) -> tuple[list, list]:
    async with HAClient(env["HA_URL"], env["HA_TOKEN"]) as client:
        cfg = await _load_config(client, url_path)
        views = list(cfg.get("views", []))
        before = [v.get("path") for v in views]
        # Bestaande view met hetzelfde path: vervang in-place, zodat de
        # tab-volgorde behouden blijft. Nieuwe view: achteraan.
        for i, v in enumerate(views):
            if v.get("path") == view["path"]:
                views[i] = view
                break
        else:
            views.append(view)
        cfg["views"] = views
        await client.cmd(type="lovelace/config/save", url_path=url_path, config=cfg)
        return before, [v.get("path") for v in views]


async def remove(env: dict, url_path: str, view_path: str) -> tuple[list, list]:
    async with HAClient(env["HA_URL"], env["HA_TOKEN"]) as client:
        cfg = await _load_config(client, url_path)
        views = list(cfg.get("views", []))
        before = [v.get("path") for v in views]
        if view_path not in before:
            return before, before  # niets te doen (idempotent)
        cfg["views"] = [v for v in views if v.get("path") != view_path]
        await client.cmd(type="lovelace/config/save", url_path=url_path, config=cfg)
        return before, [v.get("path") for v in cfg["views"]]


async def main():
    if len(sys.argv) == 4 and sys.argv[2] == "--remove":
        url_path, view_path = sys.argv[1], sys.argv[3]
        work = lambda env: remove(env, url_path, view_path)
        done_msg = f"View '{view_path}' verwijderd uit dashboard '{url_path}'"
    elif len(sys.argv) == 3:
        url_path, view_file = sys.argv[1], sys.argv[2]
        try:
            with open(view_file) as f:
                view = yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            sys.exit(f"Kan {view_file} niet lezen: {e}")
        if not isinstance(view, dict) or not view.get("path"):
            sys.exit(f"{view_file} is geen view-mapping met een 'path'-key")
        work = lambda env: apply(env, url_path, view)
        done_msg = f"View '{view['path']}' opgeslagen in dashboard '{url_path}'"
    else:
        sys.exit(__doc__.strip())

    env = load_env()
    last_err = None
    for attempt in range(1, 4):  # Nabu Casa reset af en toe de verbinding
        try:
            before, after = await work(env)
            break
        except Exception as e:
            last_err = e
            print(f"  poging {attempt} mislukt ({type(e).__name__}); opnieuw...")
            await asyncio.sleep(3)
    else:
        sys.exit(f"Mislukt voor dashboard '{url_path}' na 3 pogingen: {last_err}")

    if before == after and sys.argv[2] == "--remove":
        print(f"View '{sys.argv[3]}' stond niet (meer) op dashboard '{url_path}'; niets gedaan")
    else:
        print(done_msg)
    print(f"  views voor: {before}")
    print(f"  views na  : {after}")


if __name__ == "__main__":
    asyncio.run(main())
