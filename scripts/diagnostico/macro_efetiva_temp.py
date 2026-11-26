import os
import sys

import requests

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "SEU_TOKEN_AQUI")

HOST_ID = "10685"
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


def buscar_macro_em_alvo(alvo_id: str) -> dict | None:
    res = zabbix_rpc(
        "usermacro.get",
        {
            "output": ["hostmacroid", "macro", "value", "description"],
            "hostids": alvo_id,
            "filter": {"macro": MACRO_NAME},
        },
    )
    return res[0] if res else None


def coletar_templates_recursivos(
    template_ids: list[str],
    visitados: set[str],
    ordenados: list[dict],
) -> None:
    pendentes = [tid for tid in template_ids if tid not in visitados]
    if not pendentes:
        return

    templates = zabbix_rpc(
        "template.get",
        {
            "output": ["templateid", "name", "host"],
            "templateids": pendentes,
            "selectParentTemplates": ["templateid", "name", "host"],
        },
    )
    templates.sort(key=lambda t: int(t["templateid"]))

    for tpl in templates:
        tid = tpl["templateid"]
        if tid in visitados:
            continue
        visitados.add(tid)
        ordenados.append(tpl)

        pais = [p["templateid"] for p in tpl.get("parentTemplates", [])]
        if pais:
            coletar_templates_recursivos(pais, visitados, ordenados)


def main() -> None:
    hosts = zabbix_rpc(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "hostids": HOST_ID,
            "selectParentTemplates": ["templateid", "name", "host"],
        },
    )
    if not hosts:
        print(f"Host {HOST_ID} não encontrado.")
        return

    host = hosts[0]
    print(f"Host:  {host['host']} (hostid={host['hostid']})")
    print(f"Macro: {MACRO_NAME}\n")

    valor_efetivo = None
    origem_efetiva = None

    # 1. Nível Host
    macro_host = buscar_macro_em_alvo(HOST_ID)
    if macro_host:
        print(f"  [Host]     {host['host']} -> {macro_host['value']}")
        valor_efetivo = macro_host["value"]
        origem_efetiva = f"Host ({host['host']})"
    else:
        print(f"  [Host]     {host['host']} -> não definida")

    # 2. Nível Templates (diretos e aninhados)
    visitados: set[str] = set()
    templates_ordenados: list[dict] = []
    pais_diretos = [t["templateid"] for t in host.get("parentTemplates", [])]
    coletar_templates_recursivos(pais_diretos, visitados, templates_ordenados)

    for tpl in templates_ordenados:
        nome_tpl = tpl.get("name") or tpl.get("host")
        macro_tpl = buscar_macro_em_alvo(tpl["templateid"])
        if macro_tpl:
            print(f"  [Template] {nome_tpl} (id={tpl['templateid']}) -> {macro_tpl['value']}")
            if valor_efetivo is None:
                valor_efetivo = macro_tpl["value"]
                origem_efetiva = f"Template ({nome_tpl})"
        else:
            print(f"  [Template] {nome_tpl} (id={tpl['templateid']}) -> não definida")

    # 3. Nível Global
    globais = zabbix_rpc(
        "usermacro.get",
        {
            "output": ["globalmacroid", "macro", "value"],
            "globalmacro": True,
            "filter": {"macro": MACRO_NAME},
        },
    )
    if globais:
        print(f"  [Global]   Zabbix Server -> {globais[0]['value']}")
        if valor_efetivo is None:
            valor_efetivo = globais[0]["value"]
            origem_efetiva = "Global"
    else:
        print("  [Global]   Zabbix Server -> não definida")

    print("\n--- Resultado ---")
    if valor_efetivo is not None:
        print(f"Valor efetivo: {valor_efetivo} (origem: {origem_efetiva})")
    else:
        print(f"A macro {MACRO_NAME} não está definida em nenhum nível.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha na execução: {exc}", file=sys.stderr)
        sys.exit(1)
