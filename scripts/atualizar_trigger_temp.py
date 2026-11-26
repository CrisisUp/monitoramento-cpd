import json
import os
import re
import sys
import urllib.request

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php").rstrip("/")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")
ZABBIX_TOKEN = os.getenv("ZABBIX_API_TOKEN", "")
HOST_NAME = os.getenv("ZABBIX_HOST", "esp32-rack-01")


def zabbix_rpc(method: str, params: dict, auth_token: str | None = None, req_id: int = 1):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": req_id,
    }
    headers = {"Content-Type": "application/json-rpc"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    req = urllib.request.Request(
        ZABBIX_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "error" in data:
        raise RuntimeError(f"Erro na API Zabbix ({method}): {data['error']}")
    return data["result"]


def main():
    token = ZABBIX_TOKEN or zabbix_rpc(
        "user.login",
        {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD},
    )

    hosts = zabbix_rpc(
        "host.get",
        {"filter": {"host": [HOST_NAME]}, "output": ["hostid", "host"]},
        auth_token=token,
    )
    if not hosts:
        print(f"Host '{HOST_NAME}' não encontrado no Zabbix.", file=sys.stderr)
        sys.exit(1)

    host_id = hosts[0]["hostid"]

    triggers = zabbix_rpc(
        "trigger.get",
        {
            "hostids": [host_id],
            "output": ["triggerid", "description", "expression", "status"],
        },
        auth_token=token,
    )

    alvo = None
    for trg in triggers:
        desc = (trg.get("description") or "").lower()
        expr = trg.get("expression") or ""
        if ("temperatura crítica" in desc or "temperatura critica" in desc) or (
            "esp32.temp" in expr and (">32" in expr or "{$TEMP.CRITICO}" in expr)
        ):
            alvo = trg
            break

    if not alvo:
        print(f"Trigger de temperatura crítica não encontrada para '{HOST_NAME}'.", file=sys.stderr)
        sys.exit(1)

    trigger_id = alvo["triggerid"]
    old_expr = alvo["expression"]

    new_expr, subs = re.subn(r">\s*32(?:\.0+)?\s*$", ">{$TEMP.CRITICO}", old_expr.strip())

    print(f"Host:            {HOST_NAME} (hostid={host_id})")
    print(f"Trigger:         [{trigger_id}] {alvo['description']}")
    print(f"Expressão atual: {old_expr}")

    if old_expr == new_expr:
        print("A expressão já está utilizando {$TEMP.CRITICO} (nenhuma alteração necessária).")
        return

    if subs == 0:
        print("Não foi possível casar '>32' na expressão atual; revise manualmente.", file=sys.stderr)
        sys.exit(1)

    zabbix_rpc(
        "trigger.update",
        {"triggerid": trigger_id, "expression": new_expr},
        auth_token=token,
    )

    verificadas = zabbix_rpc(
        "trigger.get",
        {"triggerids": [trigger_id], "output": ["triggerid", "expression"]},
        auth_token=token,
    )
    print(f"Expressão nova:  {verificadas[0]['expression']}")
    print("Trigger atualizada e verificada com sucesso.")


if __name__ == "__main__":
    main()
