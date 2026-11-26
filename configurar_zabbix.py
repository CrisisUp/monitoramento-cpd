#!/usr/bin/env python3
"""
configurar_zabbix.py — Infraestrutura como Código (IaC) para o Zabbix 7.0.

Cria/atualiza de forma idempotente toda a estrutura de monitoramento do CPD
para os nós ESP32 (esp32-porta-01 e esp32-rack-01) consumindo MQTT mTLS (:8883)
via script externo `mqtt_status.sh` e pré-processamento JSONPath.

Regras observadas na API do Zabbix 7.0:
- Em `item.update`, NÃO enviar `hostid` nem `master_itemid` (imutáveis).
- Em `item.update`, NÃO enviar `preprocessing` vazio.
- `trends` > 0 só é válido para float (`value_type=0`); para `unsigned` (3) e `text` (4), usar `"0"`.
- Em `trigger.create` / `trigger.update`, usar sintaxe de expressão Zabbix 7.0 (`func(/host/key,param)`).

Uso:
    source .venv/bin/activate
    python configurar_zabbix.py
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080").rstrip("/")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")
API_URL = f"{ZABBIX_URL}/api_jsonrpc.php"

HOST_GROUP = os.getenv("ESP32_HOST_GROUP", "CPD")
MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "cpd-mosquitto")
MQTT_PORT = os.getenv("MQTT_BROKER_PORT", "8883")

MASTER_SCRIPT = "mqtt_status.sh"

# Constantes de value_type do Zabbix
VT_FLOAT = 0
VT_UNSIGNED = 3
VT_TEXT = 4

# Constantes de severidade de trigger do Zabbix
SEV_INFO = 1
SEV_WARNING = 2
SEV_AVERAGE = 3
SEV_HIGH = 4
SEV_DISASTER = 5

# error_handler no pré-processamento:
# 0 = Error message (padrão), 1 = Discard value, 2 = Set value to
ERR_DISCARD = 1

# Definição dos nós da arquitetura distribuída (Elo5System2)
# Tupla de item: (nome, key, value_type, units, jsonpath, discard_if_missing)
NODES: List[Dict[str, Any]] = [
    {
        "host": os.getenv("ESP32_PORTA_HOST", "esp32-porta-01"),
        "visible": os.getenv("ESP32_PORTA_VISIBLE", "Porta Sala CPD (Nó 1)"),
        "topic": os.getenv("MQTT_TOPIC_PORTA", "elo5/esp32-porta-01/status"),
        "export_file": "zabbix/template_esp32_porta_01.yaml",
        "items": [
            ("Porta Sala",      "esp32.porta",      VT_TEXT,     "", "$.porta",      False),
            ("Presença PIR",    "esp32.presenca",   VT_UNSIGNED, "", "$.presenca",   True),
            ("Modo Operação",   "esp32.modo",       VT_TEXT,     "", "$.modo",       False),
            ("Botão Pânico",    "esp32.panico",     VT_UNSIGNED, "", "$.panico",     True),
            ("Último NFC Sala", "esp32.ultimo_nfc", VT_TEXT,     "", "$.ultimo_nfc", True),
            ("Estado Geral",    "esp32.estado",     VT_TEXT,     "", "$.estado",     False),
        ],
        "macros": [
            ("{$PORTA.TEMPO}",     "1m"),
            ("{$ESP32.SEM_DADOS}", "2m"),
        ],
    },
    {
        "host": os.getenv("ESP32_RACK_HOST", "esp32-rack-01"),
        "visible": os.getenv("ESP32_RACK_VISIBLE", "Rack 01 CPD (Nó 2)"),
        "topic": os.getenv("MQTT_TOPIC_RACK", "elo5/esp32-rack-01/status"),
        "export_file": "zabbix/template_esp32_rack_01.yaml",
        "items": [
            ("Temperatura",     "esp32.temp",       VT_FLOAT,    "°C", "$.temp_c",     False),
            ("Umidade",         "esp32.umid",       VT_FLOAT,    "%",  "$.umid_pct",   False),
            ("Porta Rack",      "esp32.porta",      VT_TEXT,     "",   "$.porta",      False),
            ("Modo Operação",   "esp32.modo",       VT_TEXT,     "",   "$.modo",       False),
            ("Estado Geral",    "esp32.estado",     VT_TEXT,     "",   "$.estado",     False),
            ("Distância Rack",  "esp32.distancia",  VT_FLOAT,    "cm", "$.dist_cm",    True),
            ("Invasões",        "esp32.invasoes",   VT_UNSIGNED, "",   "$.invasoes",   True),
            ("Ambiente",        "esp32.ambiente",   VT_TEXT,     "",   "$.ambiente",   True),
            ("Luminosidade",    "esp32.luz",        VT_TEXT,     "",   "$.luz",        True),
        ],
        "macros": [
            ("{$TEMP.ALERTA}",     "28"),
            ("{$TEMP.CRITICO}",    "32"),
            ("{$UMID.ALERTA}",     "65"),
            ("{$UMID.CRITICO}",    "80"),
            ("{$PORTA.TEMPO}",     "1m"),
            ("{$ESP32.SEM_DADOS}", "2m"),
        ],
    },
]


# ============================================================
# CLIENTE JSON-RPC DO ZABBIX
# ============================================================
class ZabbixAPI:
    def __init__(self, url: str, user: str, password: str, timeout: int = 15):
        self.url = url
        self.user = user
        self.password = password
        self.timeout = timeout
        self.auth: Optional[str] = None
        self.req_id = 0

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self.req_id += 1
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else {},
            "id": self.req_id,
        }
        if self.auth:
            payload["auth"] = self.auth

        resp = requests.post(self.url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            err = data["error"]
            raise RuntimeError(
                f"Zabbix API {method} falhou [{err.get('code')}]: "
                f"{err.get('message')} — {err.get('data', '')}"
            )
        return data.get("result")

    def login(self) -> str:
        self.auth = self.call("user.login", {
            "username": self.user,
            "password": self.password,
        })
        return self.auth

    def logout(self) -> None:
        if self.auth:
            try:
                self.call("user.logout", {})
            except Exception:
                pass
            self.auth = None


# ============================================================
# HELPERS DE UPSERT IDEMPOTENTE
# ============================================================
def upsert_group(api: ZabbixAPI, name: str) -> str:
    existing = api.call("hostgroup.get", {"filter": {"name": [name]}, "output": ["groupid", "name"]})
    if existing:
        gid = existing[0]["groupid"]
        print(f"  [=] Grupo '{name}' já existe (ID {gid})")
        return gid

    created = api.call("hostgroup.create", {"name": name})
    gid = created["groupids"][0]
    print(f"  [+] Grupo '{name}' criado (ID {gid})")
    return gid


def upsert_host(api: ZabbixAPI, host: str, visible: str, group_id: str) -> str:
    existing = api.call("host.get", {"filter": {"host": [host]}, "output": ["hostid", "host", "name"]})
    if existing:
        hid = existing[0]["hostid"]
        api.call("host.update", {
            "hostid": hid,
            "name": visible,
            "groups": [{"groupid": group_id}],
        })
        print(f"  [=] Host '{host}' atualizado (ID {hid})")
        return hid

    created = api.call("host.create", {
        "host": host,
        "name": visible,
        "groups": [{"groupid": group_id}],
        "interfaces": [],
        "inventory_mode": -1,
    })
    hid = created["hostids"][0]
    print(f"  [+] Host '{host}' criado (ID {hid})")
    return hid


def upsert_master_item(api: ZabbixAPI, host_id: str, topic: str = "elo5/esp32-rack-01/status") -> str:
    """
    Item mestre do tipo External check (type=10, value_type=VT_TEXT).
    Em Zabbix 7.0, `trends` deve ser "0" para tipos não-numéricos float.
    """
    master_key = f'{MASTER_SCRIPT}["{topic}"]'
    existing = api.call("item.get", {
        "hostids": host_id,
        "filter": {"key_": [master_key]},
        "output": ["itemid", "key_"],
    })

    if existing:
        itemid = existing[0]["itemid"]
        api.call("item.update", {
            "itemid": itemid,
            "name": f"MQTT Status ({topic})",
            "delay": "30s",
            "history": "31d",
            "trends": "0",
        })
        print(f"  [=] Item mestre '{master_key}' atualizado (ID {itemid})")
        return itemid

    created = api.call("item.create", {
        "hostid": host_id,
        "name": f"MQTT Status ({topic})",
        "key_": master_key,
        "params": "",
        "type": 10,
        "value_type": VT_TEXT,
        "delay": "30s",
        "history": "31d",
        "trends": "0",
    })
    itemid = created["itemids"][0]
    print(f"  [+] Item mestre '{master_key}' criado (ID {itemid})")
    return itemid


def upsert_dependent_item(
    api: ZabbixAPI,
    host_id: str,
    master_id: str,
    name: str,
    key: str,
    value_type: int,
    units: str,
    jsonpath: str,
    discard_if_missing: bool = False,
) -> str:
    """
    Item dependente (type=18) com extração JSONPath (preprocessing type=12).
    """
    existing = api.call("item.get", {
        "hostids": host_id,
        "filter": {"key_": [key]},
        "output": ["itemid", "key_"],
    })

    trends = "365d" if value_type == VT_FLOAT else "0"
    error_handler = ERR_DISCARD if discard_if_missing else 0

    payload: Dict[str, Any] = {
        "name": name,
        "key_": key,
        "type": 18,
        "value_type": value_type,
        "delay": "0",
        "history": "31d",
        "trends": trends,
        "preprocessing": [
            {
                "type": 12,
                "params": jsonpath,
                "error_handler": error_handler,
                "error_handler_params": "",
            }
        ],
    }

    if units:
        payload["units"] = units

    if existing:
        itemid = existing[0]["itemid"]
        payload["itemid"] = itemid
        api.call("item.update", payload)
        print(f"  [=] Item '{name}' ({key}) atualizado")
        return itemid

    payload["hostid"] = host_id
    payload["master_itemid"] = master_id
    created = api.call("item.create", payload)
    itemid = created["itemids"][0]
    print(f"  [+] Item '{name}' ({key}) criado")
    return itemid


def upsert_macros(api: ZabbixAPI, host_id: str, macros: List[Tuple[str, str]]) -> None:
    existing = api.call("usermacro.get", {"hostids": host_id, "output": "extend"})
    by_name = {m["macro"]: m for m in existing}

    to_create = []
    updated_count = 0

    for macro_name, macro_value in macros:
        if macro_name not in by_name:
            to_create.append({
                "hostid": host_id,
                "macro": macro_name,
                "value": macro_value,
                "type": 0,
            })
        elif str(by_name[macro_name].get("value")) != str(macro_value):
            api.call("usermacro.update", {
                "hostmacroid": by_name[macro_name]["hostmacroid"],
                "value": macro_value,
            })
            updated_count += 1

    if to_create:
        api.call("usermacro.create", to_create)
        print(f"  [+] {len(to_create)} macro(s) criada(s)")
    if updated_count:
        print(f"  [=] {updated_count} macro(s) atualizada(s)")
    if not to_create and not updated_count:
        print("  [=] Macros já atualizadas")


def upsert_triggers(api: ZabbixAPI, host_id: str, host_name: str, topic: str) -> None:
    """
    Cria ou atualiza triggers idempotentes para os itens existentes no host.
    """
    host_items = api.call("item.get", {
        "hostids": host_id,
        "output": ["itemid", "key_"],
    })
    available_keys = {it["key_"] for it in host_items}
    master_key = f'{MASTER_SCRIPT}["{topic}"]'

    candidates = [
        {
            "description": f"[{host_name}] Botão de pânico acionado",
            "expression": f"last(/{host_name}/esp32.panico)>0",
            "priority": SEV_HIGH,
            "required_keys": {"esp32.panico"},
        },
        {
            "description": f"[{host_name}] Invasão / violação detectada",
            "expression": f"last(/{host_name}/esp32.invasoes)>0",
            "priority": SEV_HIGH,
            "required_keys": {"esp32.invasoes"},
        },
        {
            "description": f"[{host_name}] Porta aberta por mais de {{$PORTA.TEMPO}}",
            "expression": f'last(/{host_name}/esp32.porta)="ABERTA" and count(/{host_name}/esp32.porta,{{$PORTA.TEMPO}},"ne","ABERTA")=0',
            "priority": SEV_AVERAGE,
            "required_keys": {"esp32.porta"},
        },
        {
            "description": f"[{host_name}] Temperatura crítica acima de {{$TEMP.CRITICO}}°C",
            "expression": f"min(/{host_name}/esp32.temp,1m)>{{$TEMP.CRITICO}}",
            "priority": SEV_HIGH,
            "required_keys": {"esp32.temp"},
        },
        {
            "description": f"[{host_name}] Temperatura em alerta acima de {{$TEMP.ALERTA}}°C",
            "expression": f"min(/{host_name}/esp32.temp,1m)>{{$TEMP.ALERTA}}",
            "priority": SEV_WARNING,
            "required_keys": {"esp32.temp"},
        },
        {
            "description": f"[{host_name}] Sem telemetria MQTT há {{$ESP32.SEM_DADOS}}",
            "expression": f"nodata(/{host_name}/{master_key},{{$ESP32.SEM_DADOS}})=1",
            "priority": SEV_AVERAGE,
            "required_keys": {master_key},
        },
    ]

    for trig in candidates:
        if not trig["required_keys"].issubset(available_keys):
            continue

        existing = api.call("trigger.get", {
            "hostids": host_id,
            "filter": {"description": trig["description"]},
            "output": ["triggerid", "description"],
        })

        payload: Dict[str, Any] = {
            "description": trig["description"],
            "expression": trig["expression"],
            "priority": trig["priority"],
        }

        if existing:
            tid = existing[0]["triggerid"]
            payload["triggerid"] = tid
            api.call("trigger.update", payload)
            print(f"  [=] Trigger '{trig['description']}' atualizada (ID {tid})")
        else:
            created = api.call("trigger.create", payload)
            tid = created["triggerids"][0]
            print(f"  [+] Trigger '{trig['description']}' criada (ID {tid})")


def export_template(api: ZabbixAPI, host_id: str, path: str) -> None:
    try:
        target_dir = os.path.dirname(path) or "zabbix"
        os.makedirs(target_dir, exist_ok=True)
        yaml_content = api.call("configuration.export", {
            "format": "yaml",
            "options": {"hosts": [host_id]},
        })
        with open(path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        print(f"  [+] Template exportado para {path}")
    except Exception as exc:
        print(f"  [!] Aviso: não foi possível exportar template '{path}': {exc}")


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
def main() -> None:
    print("=" * 64)
    print("  CONFIGURAÇÃO DO ZABBIX 7.0 VIA IaC (Elo5System2 mTLS :8883)")
    print("=" * 64)
    print(f"Servidor : {ZABBIX_URL}")
    print(f"Grupo    : {HOST_GROUP}")
    print(f"Broker   : {MQTT_BROKER}:{MQTT_PORT} (mTLS)")
    print(f"Nós      : {', '.join(n['host'] for n in NODES)}")
    print()

    api = ZabbixAPI(API_URL, ZABBIX_USER, ZABBIX_PASSWORD)

    try:
        print("[1/3] Autenticando na API JSON-RPC...")
        api.login()
        print("  [+] Autenticação OK")

        print(f"\n[2/3] Garantindo grupo '{HOST_GROUP}'...")
        group_id = upsert_group(api, HOST_GROUP)

        print("\n[3/3] Provisionando hosts, itens, macros, triggers e exports...")
        for node in NODES:
            host_name = node["host"]
            visible_name = node["visible"]
            topic = node["topic"]

            print(f"\n--- Nó: {host_name} ({visible_name}) | Tópico: {topic} ---")
            host_id = upsert_host(api, host_name, visible_name, group_id)
            master_id = upsert_master_item(api, host_id, topic)

            for item_cfg in node["items"]:
                name, key, vtype, units, jpath, discard_missing = item_cfg
                try:
                    upsert_dependent_item(
                        api=api,
                        host_id=host_id,
                        master_id=master_id,
                        name=name,
                        key=key,
                        value_type=vtype,
                        units=units,
                        jsonpath=jpath,
                        discard_if_missing=discard_missing,
                    )
                except Exception as exc:
                    print(f"  [!] Falha no item '{name}' ({key}): {exc}")

            upsert_macros(api, host_id, node["macros"])
            upsert_triggers(api, host_id, host_name, topic)
            export_template(api, host_id, node["export_file"])

        print()
        print("=" * 64)
        print("  ✅ PROVISIONAMENTO CONCLUÍDO COM SUCESSO")
        print("=" * 64)
        print(f"  Zabbix UI : {ZABBIX_URL}")
        print(f"  Hosts     : {ZABBIX_URL}/zabbix.php?action=host.list")
        print(f"  Problemas : {ZABBIX_URL}/zabbix.php?action=problem.view")
        print(f"  Dados     : {ZABBIX_URL}/zabbix.php?action=latest.view")
        print()

    except Exception as exc:
        print(f"\n❌ ERRO FATAL: {exc}")
        sys.exit(1)
    finally:
        api.logout()


if __name__ == "__main__":
    main()