import os
import sys
import time
from datetime import datetime

import requests

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "SEU_TOKEN_AQUI")

ITEM_ID = "36121"
HORAS = 24


def zabbix_rpc(method: str, params: dict) -> dict | list:
    headers = {
        "Content-Type": "application/json-rpc",
        "Authorization": f"Bearer {ZABBIX_TOKEN}",
    }
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }
    resp = requests.post(ZABBIX_URL, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"Erro Zabbix API ({method}): {data['error']}")
    return data["result"]


def fmt_ts(ts: str | int) -> str:
    return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")


def main() -> None:
    itens = zabbix_rpc(
        "item.get",
        {
            "output": ["itemid", "name", "key_", "value_type", "units"],
            "itemids": ITEM_ID,
            "selectHosts": ["host"],
        },
    )
    if not itens:
        print(f"Item {ITEM_ID} não encontrado.")
        return

    item = itens[0]
    host = item["hosts"][0]["host"] if item.get("hosts") else "desconhecido"
    units = item.get("units", "")
    value_type = int(item["value_type"])

    if value_type not in (0, 3):
        print(f"Item {ITEM_ID} não é numérico (value_type={value_type}); trends não disponíveis.")
        return

    agora = int(time.time())
    time_from = agora - (HORAS * 3600)

    trends = zabbix_rpc(
        "trend.get",
        {
            "output": ["clock", "num", "value_min", "value_avg", "value_max"],
            "itemids": ITEM_ID,
            "time_from": time_from,
            "time_till": agora,
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": HORAS,
        },
    )

    print(f"Host: {host} | Item: [{item['itemid']}] {item['name']} ({item['key_']})")
    print(f"Janela: últimas {HORAS}h | Registros encontrados: {len(trends)}\n")

    for row in trends:
        hora = fmt_ts(row["clock"])
        print(
            f"  {hora} | min={row['value_min']}{units} | "
            f"avg={row['value_avg']}{units} | max={row['value_max']}{units} "
            f"(amostras={row['num']})"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha na execução: {exc}", file=sys.stderr)
        sys.exit(1)
