#!/usr/bin/env python3
"""Cria triggers de Porta Aberta (50760) e Invasão (50764) no host esp32-rack-01 via API do Zabbix 7.0."""

import json
import os
import urllib.request

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "").strip()
HOST_NAME = os.getenv("ZABBIX_HOST", "esp32-rack-01")

TRIGGERS_SPEC = [
    {
        "description": "Rack CPD: Porta aberta detectada ({HOST.NAME})",
        "expression": f'last(/{HOST_NAME}/esp32.porta)="ABERTA"',
        "priority": 4,
        "comments": "Acionada quando o sensor magnético reed switch (item 50760) reporta estado ABERTA.",
        "tags": [
            {"tag": "component", "value": "physical-security"},
            {"tag": "sensor", "value": "reed-switch"},
        ],
    },
    {
        "description": "Rack CPD: Invasão física detectada ({HOST.NAME})",
        "expression": f"last(/{HOST_NAME}/esp32.invasoes)>0",
        "priority": 5,
        "comments": "Acionada quando o contador de invasões (item 50764) é maior que 0.",
        "tags": [
            {"tag": "component", "value": "physical-security"},
            {"tag": "incident", "value": "intrusion"},
        ],
    },
]


def zabbix_rpc(method: str, params: dict, token: str | None = None, req_id: int = 1):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": req_id}
    headers = {"Content-Type": "application/json-rpc"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        ZABBIX_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "error" in body:
        raise RuntimeError(f"Erro Zabbix API ({method}): {body['error']}")
    return body["result"]


def get_token() -> str:
    if ZABBIX_TOKEN:
        return ZABBIX_TOKEN
    return zabbix_rpc("user.login", {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD})


def main() -> None:
    token = get_token()
    existing = zabbix_rpc(
        "trigger.get",
        {
            "output": ["triggerid", "description", "priority", "status"],
            "filter": {"host": HOST_NAME},
        },
        token=token,
    )
    existing_by_desc = {t["description"]: t for t in existing}

    for spec in TRIGGERS_SPEC:
        desc = spec["description"]
        if desc in existing_by_desc:
            tid = existing_by_desc[desc]["triggerid"]
            print(f"[OK] Trigger já existe: triggerid={tid} | {desc}")
            continue

        res = zabbix_rpc("trigger.create", spec, token=token)
        tid = res["triggerids"][0]
        print(f"[CRIADA] triggerid={tid} | {desc} | expr={spec['expression']}")


if __name__ == "__main__":
    main()
