import os
import sys

import requests

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "SEU_TOKEN_AQUI")

HOST_ID = "10685"
MACRO_NAME = "{$TEMP.CRITICO}"
MACRO_VALUE = "30"
MACRO_DESC = "Limiar crítico de temperatura do rack (°C)"


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


def main() -> None:
    # 1. Verifica se a macro já existe no host
    macros = zabbix_rpc(
        "usermacro.get",
        {
            "output": ["hostmacroid", "macro", "value", "description"],
            "hostids": HOST_ID,
            "filter": {"macro": MACRO_NAME},
        },
    )

    if macros:
        existente = macros[0]
        macro_id = existente["hostmacroid"]
        valor_atual = existente["value"]

        if valor_atual == MACRO_VALUE:
            print(f"Macro {MACRO_NAME} já está definida como '{MACRO_VALUE}' (hostmacroid={macro_id}).")
            return

        zabbix_rpc(
            "usermacro.update",
            {
                "hostmacroid": macro_id,
                "value": MACRO_VALUE,
                "description": MACRO_DESC,
            },
        )
        print(f"Macro atualizada: {MACRO_NAME} = '{valor_atual}' -> '{MACRO_VALUE}' (hostmacroid={macro_id})")
    else:
        res = zabbix_rpc(
            "usermacro.create",
            {
                "hostid": HOST_ID,
                "macro": MACRO_NAME,
                "value": MACRO_VALUE,
                "description": MACRO_DESC,
            },
        )
        novo_id = res["hostmacroids"][0]
        print(f"Macro criada: {MACRO_NAME} = '{MACRO_VALUE}' (hostmacroid={novo_id})")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Falha na execução: {exc}", file=sys.stderr)
        sys.exit(1)
