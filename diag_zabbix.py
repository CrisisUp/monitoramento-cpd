#!/usr/bin/env python3
"""
diag_zabbix.py — Diagnóstico rápido dos nós ESP32 (mTLS :8883) no Zabbix 7.0.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")
API_URL = f"{ZABBIX_URL}/api_jsonrpc.php"

TARGET_HOSTS = ["esp32-porta-01", "esp32-rack-01", "esp32-cpd"]


def zbx(method, params, auth=None):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    if auth:
        payload["auth"] = auth
    r = requests.post(API_URL, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["result"]


def main():
    print(f"Conectando em {API_URL} ...")
    auth = zbx("user.login", {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD})
    print("  Login OK\n")

    hosts = zbx("host.get", {"filter": {"host": TARGET_HOSTS}, "output": ["hostid", "host", "name"]}, auth)
    if not hosts:
        print("Nenhum host ESP32 encontrado.")
        return

    for h in hosts:
        print(f"Host '{h['host']}' ({h['name']}) → ID {h['hostid']}")
        items = zbx(
            "item.get",
            {
                "hostids": h["hostid"],
                "output": ["name", "key_", "value_type", "status", "lastclock", "lastvalue", "error"],
                "sortfield": "name",
            },
            auth,
        )
        print(f"{'NAME':<22} {'KEY':<44} {'VT':<3} {'ST':<4} {'LAST CLOCK':<12} {'LAST VALUE'}")
        print("-" * 115)
        for it in items:
            st = "ON" if str(it["status"]) == "0" else "OFF"
            val = (it.get("lastvalue") or "")[:36]
            err = it.get("error") or ""
            suffix = f"  [ERR: {err}]" if err else ""
            print(f"{it['name']:<22} {it['key_']:<44} {it['value_type']:<3} {st:<4} {it['lastclock']:<12} {val}{suffix}")
        print(f"\nTotal de itens ({h['host']}): {len(items)}\n")

    print("Legenda: VT = value_type (0=float, 3=unsigned, 4=text) | ST = status (ON=habilitado, OFF=desabilitado)")
    zbx("user.logout", {}, auth)


if __name__ == "__main__":
    main()
