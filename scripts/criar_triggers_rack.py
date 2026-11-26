#!/usr/bin/env python3
"""Provisiona e sincroniza triggers e macros do rack CPD no Zabbix 7.0 via JSON-RPC."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "").strip()
HOST_NAME = os.getenv("ZABBIX_HOST", "esp32-rack-01")
TEMP_CRIT_MACRO = os.getenv("ZABBIX_TEMP_CRIT_MACRO", "{$TEMP.CRITICO}")
TEMP_CRIT_DEFAULT = os.getenv("ZABBIX_TEMP_CRIT_VALUE", "32")
REQUEST_TIMEOUT = float(os.getenv("ZABBIX_TIMEOUT", "15"))


def build_triggers_spec(host_name: str, temp_macro: str) -> list[dict[str, Any]]:
    """Monta a especificação declarativa das triggers para o host do rack."""
    return [
        {
            "item_key": "esp32.temp",
            "description": f"[{host_name}] Temperatura crítica acima de {temp_macro}°C",
            "expression": f"last(/{host_name}/esp32.temp)>{temp_macro}",
            "priority": 4,
            "comments": (
                f"Acionada quando a última leitura de temperatura (esp32.temp) "
                f"ultrapassa {temp_macro}°C."
            ),
            "tags": [
                {"tag": "component", "value": "thermal"},
                {"tag": "sensor", "value": "temperature"},
            ],
        },
        {
            "item_key": "esp32.porta",
            "description": "Rack CPD: Porta aberta detectada ({HOST.NAME})",
            "expression": f'last(/{host_name}/esp32.porta)="ABERTA"',
            "priority": 4,
            "comments": (
                "Acionada quando o sensor magnético reed switch (esp32.porta) "
                "reporta estado ABERTA."
            ),
            "tags": [
                {"tag": "component", "value": "physical-security"},
                {"tag": "sensor", "value": "reed-switch"},
            ],
        },
        {
            "item_key": "esp32.invasoes",
            "description": "Rack CPD: Invasão física detectada ({HOST.NAME})",
            "expression": f"last(/{host_name}/esp32.invasoes)>0",
            "priority": 5,
            "comments": (
                "Acionada quando o contador de invasões (esp32.invasoes) "
                "é maior que 0."
            ),
            "tags": [
                {"tag": "component", "value": "physical-security"},
                {"tag": "incident", "value": "intrusion"},
            ],
        },
    ]


class ZabbixRPCClient:
    """Cliente minimalista e resiliente para a API JSON-RPC do Zabbix 7.0."""

    def __init__(
        self,
        url: str,
        user: str,
        password: str,
        token: str = "",
        timeout: float = 15.0,
    ) -> None:
        self.url = url.rstrip("/")
        self.user = user
        self.password = password
        self.token = token.strip()
        self.timeout = timeout
        self._req_id = 0

    def call(self, method: str, params: Any, auth: str | None = None) -> Any:
        self._req_id += 1
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._req_id,
        }
        headers = {"Content-Type": "application/json-rpc"}
        use_bearer = auth if auth is not None else self.token
        if use_bearer:
            headers["Authorization"] = f"Bearer {use_bearer}"

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body_err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Falha HTTP {exc.code} na API do Zabbix ({method}): {body_err}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Falha de conexão com a API do Zabbix em {self.url}: {exc.reason}"
            ) from exc

        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Resposta JSON inválida da API do Zabbix ({method}): {raw[:300]}"
            ) from exc

        if "error" in body:
            err = body["error"]
            raise RuntimeError(
                f"Erro Zabbix API ({method}): code={err.get('code')} "
                f"message={err.get('message')} data={err.get('data')}"
            )

        return body["result"]

    def authenticate(self) -> None:
        if self.token:
            return
        result = self.call(
            "user.login",
            {"username": self.user, "password": self.password},
            auth="",
        )
        if not isinstance(result, str) or not result:
            raise RuntimeError(f"Resposta inesperada no user.login: {result}")
        self.token = result


def resolve_host_id(client: ZabbixRPCClient, host_name: str) -> str:
    hosts = client.call(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "filter": {"host": [host_name]},
        },
    )
    if not hosts:
        raise RuntimeError(f"Host '{host_name}' não encontrado no Zabbix.")
    return str(hosts[0]["hostid"])


def ensure_temp_macro(
    client: ZabbixRPCClient,
    host_id: str,
    macro_name: str,
    default_value: str,
) -> None:
    """Garante que a macro crítica (ex.: {$TEMP.CRITICO}) exista no host."""
    macros = client.call(
        "usermacro.get",
        {
            "hostids": [host_id],
            "filter": {"macro": macro_name},
            "output": ["hostmacroid", "macro", "value"],
        },
    )
    if macros:
        current_val = str(macros[0].get("value", ""))
        print(f"[MACRO OK] {macro_name}={current_val} (hostid={host_id})")
        return

    created = client.call(
        "usermacro.create",
        {
            "hostid": host_id,
            "macro": macro_name,
            "value": default_value,
        },
    )
    macro_ids = created.get("hostmacroids", [])
    print(
        f"[MACRO CRIADA] {macro_name}={default_value} "
        f"(hostmacroid={macro_ids[0] if macro_ids else 'n/a'})"
    )


def _normalize_tags(tags: list[dict[str, str]] | None) -> list[tuple[str, str]]:
    if not tags:
        return []
    return sorted((str(t.get("tag", "")), str(t.get("value", ""))) for t in tags)


def _find_matching_trigger(
    existing: list[dict[str, Any]],
    spec: dict[str, Any],
    matched_ids: set[str],
) -> dict[str, Any] | None:
    """Localiza trigger existente por descrição exata ou pela chave do item monitorado."""
    desc = str(spec["description"])
    item_key = str(spec.get("item_key", ""))

    for trig in existing:
        tid = str(trig["triggerid"])
        if tid in matched_ids:
            continue
        if str(trig.get("description", "")) == desc:
            return trig

    if item_key:
        for trig in existing:
            tid = str(trig["triggerid"])
            if tid in matched_ids:
                continue
            if f"/{item_key}" in str(trig.get("expression", "")):
                return trig

    return None


SHOW_DIFF = os.getenv("ZABBIX_SHOW_DIFF", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _diff_trigger(
    target: dict[str, Any], spec: dict[str, Any]
) -> dict[str, tuple[Any, Any]]:
    """Retorna {campo: (esperado, atual)} para cada atributo divergente no Zabbix."""
    diffs: dict[str, tuple[Any, Any]] = {}

    expected_desc = str(spec["description"])
    actual_desc = str(target.get("description", ""))
    if actual_desc != expected_desc:
        diffs["description"] = (expected_desc, actual_desc)

    expected_expr = str(spec["expression"])
    actual_expr = str(target.get("expression", ""))
    if actual_expr != expected_expr:
        diffs["expression"] = (expected_expr, actual_expr)

    expected_prio = int(spec["priority"])
    actual_prio = int(target.get("priority", -1))
    if actual_prio != expected_prio:
        diffs["priority"] = (expected_prio, actual_prio)

    expected_comments = str(spec.get("comments", ""))
    actual_comments = str(target.get("comments", ""))
    if actual_comments != expected_comments:
        diffs["comments"] = (expected_comments, actual_comments)

    expected_tags = _normalize_tags(spec.get("tags"))
    actual_tags = _normalize_tags(target.get("tags"))
    if actual_tags != expected_tags:
        diffs["tags"] = (expected_tags, actual_tags)

    return diffs


def sync_triggers(
    client: ZabbixRPCClient,
    host_id: str,
    host_name: str,
    specs: list[dict[str, Any]],
) -> None:
    """Cria triggers ausentes e atualiza triggers existentes quando divergentes."""
    existing = client.call(
        "trigger.get",
        {
            "hostids": [host_id],
            "output": [
                "triggerid",
                "description",
                "expression",
                "priority",
                "comments",
                "status",
            ],
            "expandExpression": True,
            "selectTags": ["tag", "value"],
            "sortfield": "triggerid",
            "sortorder": "ASC",
        },
    )

    matched_ids: set[str] = set()

    for raw_spec in specs:
        spec = {k: v for k, v in raw_spec.items() if k != "item_key"}
        desc = spec["description"]
        target = _find_matching_trigger(existing, raw_spec, matched_ids)

        if target is None:
            created = client.call("trigger.create", spec)
            tid = str(created["triggerids"][0])
            matched_ids.add(tid)
            print(f"[CRIADA] triggerid={tid} | {desc} | expr={spec['expression']}")
            continue

        tid = str(target["triggerid"])
        matched_ids.add(tid)

        diffs = _diff_trigger(target, spec)

        if not diffs:
            print(f"[OK] triggerid={tid} | {desc}")
            continue

        if SHOW_DIFF:
            for field, (expected_val, actual_val) in diffs.items():
                print(
                    f"  [DIFF triggerid={tid}.{field}] "
                    f"esperado={expected_val!r} | atual={actual_val!r}"
                )

        update_payload: dict[str, Any] = {
            "triggerid": tid,
            "description": desc,
            "expression": spec["expression"],
            "priority": spec["priority"],
            "comments": spec.get("comments", ""),
            "tags": spec.get("tags", []),
        }
        client.call("trigger.update", update_payload)
        print(
            f"[ATUALIZADA] triggerid={tid} | {desc} | "
            f"expr={spec['expression']} (host={host_name})"
        )


def main() -> int:
    client = ZabbixRPCClient(
        url=ZABBIX_URL,
        user=ZABBIX_USER,
        password=ZABBIX_PASSWORD,
        token=ZABBIX_TOKEN,
        timeout=REQUEST_TIMEOUT,
    )
    client.authenticate()
    host_id = resolve_host_id(client, HOST_NAME)
    ensure_temp_macro(client, host_id, TEMP_CRIT_MACRO, TEMP_CRIT_DEFAULT)
    specs = build_triggers_spec(HOST_NAME, TEMP_CRIT_MACRO)
    sync_triggers(client, host_id, HOST_NAME, specs)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
