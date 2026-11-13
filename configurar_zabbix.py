#!/usr/bin/env python3
"""
configurar_zabbix.py — Infraestrutura como Código (IaC) para o Zabbix 7.0.

Cria/atualiza toda a estrutura de monitoramento do CPD no Zabbix via API.
Idempotente: pode rodar quantas vezes quiser sem duplicar.

Regras importantes do Zabbix 7.0 (descobertas na prática):
- No item.update, NÃO enviar hostid nem master_itemid (imutáveis).
- No item.update, NÃO enviar preprocessing vazio (rejeitado).
- trends > 0 SÓ é válido para items float (value_type=0).
  Para texto (4) e unsigned (3), trends deve ser "0".

Uso:
    source .venv/bin/activate
    python configurar_zabbix.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")
API_URL = f"{ZABBIX_URL}/api_jsonrpc.php"

HOST_NAME = os.getenv("ESP32_HOST_NAME", "esp32-cpd")
HOST_VISIBLE = os.getenv("ESP32_HOST_VISIBLE", "Rack CPD")
HOST_GROUP = os.getenv("ESP32_HOST_GROUP", "CPD")
MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "cpd-mosquitto")
MQTT_PORT = os.getenv("MQTT_BROKER_PORT", "1883")
MQTT_TOPIC_BASE = os.getenv("MQTT_TOPIC_BASE", "publico/rack_monitor_ABCD1234")

MASTER_KEY = "mqtt_status.sh"

# Constantes de value_type do Zabbix
VT_FLOAT = 0
VT_UNSIGNED = 3
VT_TEXT = 4


# ============================================================
# CLIENTE DA API
# ============================================================
class ZabbixAPI:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.auth = None
        self.req_id = 0

    def call(self, method, params=None):
        self.req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.req_id,
        }
        if self.auth:
            payload["auth"] = self.auth

        r = requests.post(self.url, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            err = data["error"]
            raise RuntimeError(
                f"API {method} falhou: [{err['code']}] {err['message']} — {err.get('data', '')}"
            )
        return data["result"]

    def login(self):
        self.auth = self.call("user.login", {
            "username": self.user,
            "password": self.password,
        })
        return self.auth

    def logout(self):
        if self.auth:
            try:
                self.call("user.logout", {})
            except Exception:
                pass
            self.auth = None


# ============================================================
# HELPERS DE IDEMPOTÊNCIA
# ============================================================
def upsert_group(api, name):
    existing = api.call("hostgroup.get", {"filter": {"name": [name]}})
    if existing:
        print(f"  [=] Grupo '{name}' já existe (ID {existing[0]['groupid']})")
        return existing[0]["groupid"]
    result = api.call("hostgroup.create", {"name": name})
    gid = result["groupids"][0]
    print(f"  [+] Grupo '{name}' criado (ID {gid})")
    return gid


def upsert_host(api, host, visible, group_id):
    existing = api.call("host.get", {"filter": {"host": [host]}})
    if existing:
        hid = existing[0]["hostid"]
        print(f"  [=] Host '{host}' já existe (ID {hid})")
        api.call("host.update", {
            "hostid": hid,
            "name": visible,
            "groups": [{"groupid": group_id}],
        })
        return hid

    result = api.call("host.create", {
        "host": host,
        "name": visible,
        "groups": [{"groupid": group_id}],
        "interfaces": [],
        "inventory_mode": -1,
    })
    hid = result["hostids"][0]
    print(f"  [+] Host '{host}' criado (ID {hid})")
    return hid


def upsert_master_item(api, host_id):
    """
    Item mestre (External check, text).
    - No UPDATE, só campos mutáveis: name, delay, history, trends.
    - trends: "0" (obrigatório para text).
    """
    existing = api.call("item.get", {
        "hostids": host_id,
        "filter": {"key_": [MASTER_KEY]},
    })

    if existing:
        itemid = existing[0]["itemid"]
        api.call("item.update", {
            "itemid": itemid,
            "name": "MQTT Status",
            "delay": "30s",
            "history": "31d",
            "trends": "0",
        })
        print(f"  [=] Item mestre '{MASTER_KEY}' atualizado (ID {itemid})")
        return itemid

    result = api.call("item.create", {
        "hostid": host_id,
        "name": "MQTT Status",
        "key_": MASTER_KEY,
        "type": 21,          # 21 = External check
        "value_type": VT_TEXT,
        "delay": "30s",
        "history": "31d",
        "trends": "0",
    })
    itemid = result["itemids"][0]
    print(f"  [+] Item mestre '{MASTER_KEY}' criado (ID {itemid})")
    return itemid


def upsert_dependent_item(api, host_id, master_id, name, key, value_type, units, jsonpath):
    """
    Item dependente (com JSONPath).
    - trends: 0 para text/unsigned, 365d só para float.
    - No UPDATE: sem hostid, sem master_itemid (imutáveis).
    """
    existing = api.call("item.get", {
        "hostids": host_id,
        "filter": {"key_": [key]},
    })

    # trends: só faz sentido para float
    trends = "365d" if value_type == VT_FLOAT else "0"

    payload = {
        "name": name,
        "key_": key,
        "type": 18,                  # 18 = Dependent item
        "value_type": value_type,
        "delay": "0",                # herda do mestre
        "history": "31d",
        "trends": trends,
        "preprocessing": [
            {
                "type": 12,           # 12 = JSONPath
                "params": jsonpath,
                "error_handler": 0,
                "error_handler_params": "",
            }
        ],
    }

    if units:
        payload["units"] = units

    if existing:
        payload["itemid"] = existing[0]["itemid"]
        api.call("item.update", payload)
        print(f"  [=] Item '{name}' atualizado")
    else:
        payload["hostid"] = host_id
        payload["master_itemid"] = master_id
        api.call("item.create", payload)
        print(f"  [+] Item '{name}' criado")


def upsert_macros(api, host_id):
    macros = [
        ("{$TEMP.ALERTA}", "28"),
        ("{$TEMP.CRITICO}", "32"),
        ("{$UMID.ALERTA}", "65"),
        ("{$UMID.CRITICO}", "80"),
        ("{$PORTA.TEMPO}", "1m"),
        ("{$ESP32.SEM_DADOS}", "2m"),
    ]
    existing = api.call("usermacro.get", {"hostids": host_id, "output": "extend"})
    existing_names = {m["macro"] for m in existing}

    to_create = [
        {"hostid": host_id, "macro": name, "value": value, "type": 0}
        for name, value in macros
        if name not in existing_names
    ]
    if to_create:
        api.call("usermacro.create", to_create)
        print(f"  [+] {len(to_create)} macro(s) criada(s)")
    else:
        print(f"  [=] Macros já existem")


def export_template(api, host_id):
    try:
        os.makedirs("zabbix", exist_ok=True)
        result = api.call("configuration.export", {
            "format": "yaml",
            "options": {"hosts": [host_id]},
        })
        path = "zabbix/template_esp32_cpd.yaml"
        with open(path, "w") as f:
            f.write(result)
        print(f"  [+] Template exportado para {path}")
    except Exception as e:
        print(f"  [!] Aviso: não foi possível exportar template: {e}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  CONFIGURAÇÃO DO ZABBIX VIA IaC")
    print("=" * 60)
    print(f"Servidor: {ZABBIX_URL}")
    print(f"Host:     {HOST_NAME} / {HOST_VISIBLE}")
    print(f"Grupo:    {HOST_GROUP}")
    print(f"Broker:   {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Tópico:   {MQTT_TOPIC_BASE}")
    print()

    api = ZabbixAPI(API_URL, ZABBIX_USER, ZABBIX_PASSWORD)

    try:
        print("[1/6] Autenticando...")
        api.login()
        print("  [+] Login OK")

        print(f"[2/6] Grupo '{HOST_GROUP}'...")
        group_id = upsert_group(api, HOST_GROUP)

        print(f"[3/6] Host '{HOST_NAME}'...")
        host_id = upsert_host(api, HOST_NAME, HOST_VISIBLE, group_id)

        print("[4/6] Item mestre...")
        master_id = upsert_master_item(api, host_id)

        print("[5/6] Itens dependentes...")
        items = [
            # (nome, key, value_type, units, jsonpath)
            ("Temperatura",    "esp32.temp",        VT_FLOAT,    "°C",  "$.temp_c"),
            ("Umidade",        "esp32.umid",        VT_FLOAT,    "%",   "$.umid_pct"),
            ("Porta Aberta",   "esp32.porta",       VT_TEXT,     "",    "$.porta"),
            ("Modo",           "esp32.modo",        VT_TEXT,     "",    "$.modo"),
            ("Estado",         "esp32.estado",      VT_TEXT,     "",    "$.estado"),
            ("Distância",      "esp32.distancia",   VT_FLOAT,    "cm",  "$.dist_cm"),
            ("Invasões",       "esp32.invasoes",    VT_UNSIGNED, "",    "$.invasoes"),
            ("Ambiente",       "esp32.ambiente",    VT_TEXT,     "",    "$.ambiente"),
            ("Luminosidade",   "esp32.luz",         VT_TEXT,     "",    "$.luz"),
        ]
        for name, key, vtype, units, jpath in items:
            try:
                upsert_dependent_item(api, host_id, master_id, name, key, vtype, units, jpath)
            except Exception as e:
                print(f"  [!] Falha no item '{name}': {e}")

        print("[6/6] Macros e template...")
        upsert_macros(api, host_id)
        export_template(api, host_id)

        print()
        print("=" * 60)
        print("  ✅ CONFIGURAÇÃO COMPLETA")
        print("=" * 60)
        print(f"  Zabbix: {ZABBIX_URL}")
        print(f"  Hosts:  {ZABBIX_URL}/zabbix.php?action=host.list")
        print(f"  Dados:  {ZABBIX_URL}/zabbix.php?action=latest.view")
        print()
        print("  Idempotência garantida: rode quantas vezes quiser.")

    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        sys.exit(1)
    finally:
        api.logout()


if __name__ == "__main__":
    main()
