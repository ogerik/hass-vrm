#!/usr/bin/env python3
"""Minimale Home Assistant WebSocket-client + .env-loader.

Gebruikt door apply_dashboard.py en create_dashboard.py. Config komt uit .env
(HA_URL + HA_TOKEN, zie .env.example); het token is een long-lived access token
(HA-profiel -> Beveiliging).
"""
import json
import sys
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent


def load_env() -> dict:
    env = {}
    envfile = ROOT / ".env"
    if not envfile.exists():
        sys.exit("Geen .env gevonden. Kopieer .env.example naar .env en vul HA_URL + HA_TOKEN in.")
    for line in envfile.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    if not env.get("HA_URL") or not env.get("HA_TOKEN"):
        sys.exit("HA_URL of HA_TOKEN ontbreekt in .env")
    return env


class HAClient:
    def __init__(self, url: str, token: str):
        self.ws_url = url.replace("https://", "wss://").replace("http://", "ws://").rstrip("/") + "/api/websocket"
        self.token = token
        self._id = 0
        self.ws = None

    async def __aenter__(self):
        self.ws = await websockets.connect(self.ws_url, max_size=32 * 1024 * 1024, open_timeout=30)
        hello = json.loads(await self.ws.recv())
        if hello.get("type") != "auth_required":
            raise RuntimeError(f"Onverwacht bericht: {hello}")
        await self.ws.send(json.dumps({"type": "auth", "access_token": self.token}))
        res = json.loads(await self.ws.recv())
        if res.get("type") != "auth_ok":
            raise RuntimeError(f"Auth mislukt: {res}")
        return self

    async def __aexit__(self, *a):
        if self.ws:
            await self.ws.close()

    async def cmd(self, **payload):
        self._id += 1
        mid = self._id
        payload["id"] = mid
        await self.ws.send(json.dumps(payload))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid and msg.get("type") == "result":
                if not msg.get("success", False):
                    raise RuntimeError(msg.get("error"))
                return msg["result"]
