import os
import sys
import time
from datetime import datetime
import requests

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "SEU_TOKEN_AQUI")

HOST_ID = "10685"
TRIGGER_ID = "25232"
ITEM_ID = "36121"
MACRO_NAME = "{$TEMP.CRITICO}"


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


def buscar_macro(alvo_id: str) -> str | None:
    res = zabbix_rpc(
        "usermacro.get",
        {
            "output": ["value"],
            "hostids": alvo_id,
            "filter": {"macro": MACRO_NAME},
        },
    )
    return res[0]["value"] if res else None


def resolver_macro_efetiva(host_obj: dict) -> tuple[str | None, str]:
    val_host = buscar_macro(HOST_ID)
    if val_host is not None:
        return val_host, f"Host ({host_obj.get('host')})"

    for tpl in sorted(host_obj.get("parentTemplates", []), key=lambda x: int(x["templateid"])):
        val_tpl = buscar_macro(tpl["templateid"])
        if val_tpl is not None:
            nome = tpl.get("name") or tpl.get("host")
            return val_tpl, f"Template ({nome})"

    globais = zabbix_rpc(
        "usermacro.get",
        {
            "output": ["value"],
            "globalmacro": True,
            "filter": {"macro": MACRO_NAME},
        },
    )
    if globais:
        return globais[0]["value"], "Global"

    return None, "não definida"


def main() -> None:
    inconsistencias: list[str] = []

    hosts = zabbix_rpc(
        "host.get",
        {
            "output": ["hostid", "host", "name", "status"],
            "hostids": HOST_ID,
            "selectParentTemplates": ["templateid", "name", "host"],
        },
    )
    if not hosts:
        print(f"[ERRO] Host {HOST_ID} não encontrado.")
        return
    host_obj = hosts[0]
    if str(host_obj.get("status")) != "0":
        inconsistencias.append(f"Host {host_obj['host']} está desabilitado (status={host_obj['status']}).")

    triggers = zabbix_rpc(
        "trigger.get",
        {
            "output": ["triggerid", "description", "expression", "status", "value", "lastchange"],
            "triggerids": TRIGGER_ID,
            "selectItems": ["itemid", "name", "key_", "value_type", "units", "lastvalue", "lastclock", "status"],
        },
    )
    if not triggers:
        print(f"[ERRO] Trigger {TRIGGER_ID} não encontrada.")
        return
    trig = triggers[0]

    if str(trig.get("status")) != "0":
        inconsistencias.append(f"Trigger {TRIGGER_ID} está desabilitada (status={trig['status']}).")
    if MACRO_NAME not in trig.get("expression", ""):
        inconsistencias.append(f"Expressão da trigger não contém {MACRO_NAME}: {trig.get('expression')}")

    valor_macro, origem_macro = resolver_macro_efetiva(host_obj)
    if valor_macro is None:
        inconsistencias.append(f"Macro {MACRO_NAME} não encontrada em Host, Templates nem Global.")

    print("=== 1. HOST E MACRO ===")
    print(f"Host:            {host_obj['host']} (id={host_obj['hostid']}, status={host_obj['status']})")
    print(f"Macro efetiva:   {MACRO_NAME} = {valor_macro} [origem: {origem_macro}]")

    print("\n=== 2. TRIGGER E ITENS VINCULADOS ===")
    estado_str = "PROBLEM (1)" if str(trig["value"]) == "1" else "OK (0)"
    print(f"Trigger:         [{trig['triggerid']}] {trig['description']}")
    print(f"Estado / Status: {estado_str} | habilitada={'sim' if str(trig['status']) == '0' else 'não'}")
    print(f"Expressão:       {trig['expression']}")
    print(f"Última mudança:  {fmt_ts(trig['lastchange'])}")

    agora = int(time.time())
    item_alvo_encontrado = False
    for it in trig.get("items", []):
        if str(it["itemid"]) == ITEM_ID:
            item_alvo_encontrado = True
        idade_seg = agora - int(it["lastclock"]) if int(it.get("lastclock", 0)) > 0 else None
        print(
            f"  - Item [{it['itemid']}] {it['key_']} | tipo={it['value_type']} | "
            f"lastvalue={it.get('lastvalue')}{it.get('units', '')} | "
            f"lastclock={fmt_ts(it.get('lastclock', 0))}"
            + (f" ({idade_seg}s atrás)" if idade_seg is not None else "")
        )
        if str(it.get("status")) != "0":
            inconsistencias.append(f"Item {it['itemid']} está desabilitado.")
        if idade_seg is not None and idade_seg > 300:
            inconsistencias.append(f"Item {it['itemid']} sem atualização há {idade_seg}s.")

    if not item_alvo_encontrado:
        inconsistencias.append(f"Item {ITEM_ID} não aparece entre os itens vinculados à trigger {TRIGGER_ID}.")

    problemas = zabbix_rpc(
        "problem.get",
        {
            "output": ["eventid", "name", "clock", "r_clock"],
            "object": 0,
            "source": 0,
            "objectids": TRIGGER_ID,
            "recent": True,
        },
    )
    ativos = [p for p in problemas if str(p.get("r_clock", "0")) == "0"]
    print(f"\n=== 3. PROBLEMAS ===\nAtivos: {len(ativos)} | Recentes (incl. resolvidos): {len(problemas)}")

    print("\n=== 4. DIAGNÓSTICO DE INCONSISTÊNCIAS ===")
    if inconsistencias:
        for inc in inconsistencias:
            print(f"  [ALERTA] {inc}")
    else:
        print("  Nenhuma inconsistência estrutural detectada na API do Zabbix.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha no checkup: {exc}", file=sys.stderr)
        sys.exit(1)