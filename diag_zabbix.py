#!/usr/bin/env python3
"""Diagnóstico dos itens do Zabbix (para debug do Grafana)."""
import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

URL = os.getenv("ZABBIX_URL", "http://localhost:8080") + "/api_jsonrpc.php"
USER = os.getenv("ZABBIX_USER", "Admin")
PASS = os.getenv("ZABBIX_PASSWORD", "zabbix")
HOST = os.getenv("ESP32_HOST_NAME", "esp32-cpd")


def api(method, params, auth=None):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    if auth:
        payload["auth"] = auth
    r = requests.post(URL, json=payload, timeout=10).json()
    if "error" in r:
        raise RuntimeError(r["error"])
    return r["result"]


def main():
    print(f"Conectando em {URL} ...")
    auth = api("user.login", {"username": USER, "password": PASS})
    print(f"  Login OK\n")

    hosts = api("host.get", {"filter": {"host": [HOST]}}, auth)
    if not hosts:
        print(f"❌ Host '{HOST}' não encontrado.")
        return
    host_id = hosts[0]["hostid"]
    print(f"Host '{HOST}' → ID {host_id}\n")

    items = api("item.get", {
        "hostids": host_id,
        "output": ["itemid", "name", "key_", "value_type", "status", "lastvalue", "lastclock"],
        "sortfield": "name",
    }, auth)

    print(f"{'NAME':<28} {'KEY':<20} {'VT':<3} {'ST':<4} {'LAST CLOCK':<12} {'LAST VALUE'}")
    print("-" * 95)
    for it in items:
        vt = it["value_type"]
        st = "ON" if it["status"] == "0" else "OFF"
        last = (it.get("lastvalue") or "(vazio)")[:30]
        clock = it.get("lastclock", "0")
        print(f"{it['name']:<28} {it['key_']:<20} {vt:<3} {st:<4} {clock:<12} {last}")

    print()
    print("Legenda: VT = value_type (0=float, 3=unsigned, 4=text)")
    print("         ST = status (ON=habilitado, OFF=desabilitado)")
    print()
    print(f"Total de itens: {len(items)}")

    api("user.logout", {}, auth)


if __name__ == "__main__":
    main()
