import os
import sys
from datetime import datetime
import requests

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "SEU_TOKEN_AQUI")
TRIGGER_ID = "25232"


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
    ts_int = int(ts)
    if ts_int == 0:
        return "nunca"
    return datetime.fromtimestamp(ts_int).strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    # 1. Estado atual da trigger
    triggers = zabbix_rpc(
        "trigger.get",
        {
            "output": ["triggerid", "description", "value", "status", "priority", "lastchange"],
            "triggerids": TRIGGER_ID,
            "selectHosts": ["host", "hostid"],
        },
    )
    if not triggers:
        print(f"Trigger {TRIGGER_ID} não encontrada.")
        return

    t = triggers[0]
    host_nome = t["hosts"][0]["host"] if t.get("hosts") else "desconhecido"
    estado = "PROBLEM (DISPARADA)" if str(t["value"]) == "1" else "OK"
    habilitada = "Sim" if str(t["status"]) == "0" else "Não"

    print(f"Host:           {host_nome}")
    print(f"Trigger:        [{t['triggerid']}] {t['description']}")
    print(f"Estado atual:   {estado} | Habilitada: {habilitada}")
    print(f"Última mudança: {fmt_ts(t['lastchange'])}\n")

    # 2. Problemas ativos ou resolvidos recentemente
    problemas = zabbix_rpc(
        "problem.get",
        {
            "output": ["eventid", "name", "clock", "r_clock", "severity", "acknowledged", "opdata"],
            "object": 0,
            "source": 0,
            "objectids": TRIGGER_ID,
            "recent": True,
            "sortfield": "eventid",
            "sortorder": "DESC",
        },
    )
    print(f"Problemas (ativos/recentes): {len(problemas)}")
    for p in problemas:
        status_prob = "RESOLVIDO" if str(p["r_clock"]) != "0" else "ATIVO"
        print(
            f"  - eventid={p['eventid']} | {status_prob} | início={fmt_ts(p['clock'])} "
            f"| fim={fmt_ts(p['r_clock'])} | opdata={p.get('opdata') or '-'} | {p['name']}"
        )

    # 3. Últimos 10 eventos históricos da trigger (0 = OK, 1 = PROBLEM)
    eventos = zabbix_rpc(
        "event.get",
        {
            "output": ["eventid", "clock", "value", "name"],
            "source": 0,
            "object": 0,
            "objectids": TRIGGER_ID,
            "sortfield": ["clock", "eventid"],
            "sortorder": "DESC",
            "limit": 10,
        },
    )
    print(f"\nÚltimos {len(eventos)} eventos registrados:")
    for ev in eventos:
        tipo = "PROBLEM" if str(ev["value"]) == "1" else "OK"
        print(f"  - {fmt_ts(ev['clock'])} | eventid={ev['eventid']} | {tipo:7s} | {ev['name']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha na execução: {exc}", file=sys.stderr)
        sys.exit(1)