import os
import sys

import requests

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_USER = os.getenv("ZABBIX_USER", "")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "")


class ZabbixClient:
    def __init__(self, url: str, token: str = "", timeout: int = 10) -> None:
        self.url = url
        self.token = token
        self.timeout = timeout
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def login(self, username: str, password: str) -> str:
        if not username or not password:
            raise ValueError("Defina ZABBIX_USER e ZABBIX_PASSWORD para autenticar via user.login.")

        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "username": username,
                "password": password,
            },
            "id": self._next_id(),
        }
        headers = {"Content-Type": "application/json-rpc"}
        resp = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Falha no user.login: {data['error']}")

        self.token = data["result"]
        return self.token

    def call(self, method: str, params: dict | list | None = None) -> dict | list:
        if not self.token and method != "apiinfo.version":
            self.login(ZABBIX_USER, ZABBIX_PASSWORD)

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else {},
            "id": self._next_id(),
        }
        headers = {"Content-Type": "application/json-rpc"}
        if self.token and method != "apiinfo.version":
            headers["Authorization"] = f"Bearer {self.token}"

        resp = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Erro Zabbix API ({method}): {data['error']}")
        return data["result"]


def main() -> None:
    client = ZabbixClient(url=ZABBIX_URL, token=ZABBIX_TOKEN)

    if not client.token:
        client.login(ZABBIX_USER, ZABBIX_PASSWORD)

    versao = client.call("apiinfo.version")
    usuario = client.call("user.get", {"output": ["userid", "username"]})
    hosts = client.call("host.get", {"output": ["hostid", "host", "status"], "hostids": "10685"})

    print(f"Zabbix versão: {versao}")
    print(f"Usuário autenticado: {usuario}")
    print(f"Host 10685: {hosts}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
