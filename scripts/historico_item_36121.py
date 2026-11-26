import os
import sys
from datetime import datetime
import requests

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "SEU_TOKEN_AQUI")

ITEM_ID = "36121"
LIMIT = 15


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
    return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    itens = zabbix_rpc(
        "item.get",
        {
            "output": ["itemid", "name", "key_", "value_type", "units", "lastvalue", "lastclock"],
            "itemids": ITEM_ID,
            "selectHosts": ["host"],
        },
    )
    if not itens:
        print(f"Item {ITEM_ID} não encontrado.")
        return

    item = itens[0]
    host = item["hosts"][0]["host"] if item.get("hosts") else "desconhecido"
    value_type = int(item["value_type"])
    units = item.get("units", "")

    print(f"Host:       {host}")
    print(f"Item:       [{item['itemid']}] {item['name']} ({item['key_']})")
    print(f"Tipo/Unid.: value_type={value_type} | unidade='{units or '-'}'")
    print(f"Último:     {item.get('lastvalue')} {units} em {fmt_ts(item['lastclock'])}\n" if int(item.get("lastclock", 0)) else "\n")

    historico = zabbix_rpc(
        "history.get",
        {
            "output": ["clock", "ns", "value"],
            "history": value_type,
            "itemids": ITEM_ID,
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": LIMIT,
        },
    )

    print(f"Últimas {len(historico)} leituras no histórico:")
    for row in historico:
        print(f"  - {fmt_ts(row['clock'])} (ns={row['ns']}) -> {row['value']} {units}".rstrip())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha na execução: {exc}", file=sys.stderr)
        sys.exit(1)