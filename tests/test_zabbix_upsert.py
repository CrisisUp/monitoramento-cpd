"""
test_zabbix_upsert.py — Testes da lógica de upsert do configurar_zabbix.py.
"""

import pytest

from configurar_zabbix import (
    VT_FLOAT,
    VT_TEXT,
    VT_UNSIGNED,
    upsert_dependent_item,
    upsert_group,
    upsert_host,
    upsert_master_item,
)


# ---------- GRUPO ----------
def test_upsert_group_cria_se_nao_existe(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [],
        {"groupids": ["42"]},
    ]
    gid = upsert_group(zabbix_mock, "CPD")
    assert gid == "42"
    assert zabbix_mock.call.call_count == 2
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "hostgroup.create"


def test_upsert_group_nao_duplica(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"groupid": "42"}],
    ]
    gid = upsert_group(zabbix_mock, "CPD")
    assert gid == "42"
    assert zabbix_mock.call.call_count == 1
    args, _ = zabbix_mock.call.call_args_list[0]
    assert args[0] == "hostgroup.get"


# ---------- HOST ----------
def test_upsert_host_cria_se_nao_existe(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [],
        {"hostids": ["10683"]},
    ]
    hid = upsert_host(zabbix_mock, "esp32-cpd", "Rack CPD", "42")
    assert hid == "10683"
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "host.create"


def test_upsert_host_atualiza_se_existe(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"hostid": "10683"}],
        {},
    ]
    hid = upsert_host(zabbix_mock, "esp32-cpd", "Rack CPD", "42")
    assert hid == "10683"
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "host.update"


# ---------- ITEM MESTRE ----------
def test_upsert_master_item_cria(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [],
        {"itemids": ["50740"]},
    ]
    iid = upsert_master_item(zabbix_mock, "10683")
    assert iid == "50740"
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "item.create"


def test_upsert_master_item_nao_envia_preprocessing(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"itemid": "50740"}],
        {},
    ]
    upsert_master_item(zabbix_mock, "10683")
    args, _ = zabbix_mock.call.call_args_list[1]
    params = args[1]
    assert "preprocessing" not in params


# ---------- ITENS DEPENDENTES ----------
@pytest.mark.parametrize(
    "value_type,trends_esperado",
    [
        (VT_FLOAT, "365d"),
        (VT_TEXT, "0"),
        (VT_UNSIGNED, "0"),
    ],
)
def test_trends_por_tipo(zabbix_mock, value_type, trends_esperado):
    zabbix_mock.call.side_effect = [
        [],
        {"itemids": ["1"]},
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", value_type, "", "$.campo"
    )
    args, _ = zabbix_mock.call.call_args_list[1]
    params = args[1]
    assert params["trends"] == trends_esperado


def test_upsert_item_nao_envia_hostid_no_update(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"itemid": "1"}],
        {},
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )
    args, _ = zabbix_mock.call.call_args_list[1]
    params = args[1]
    assert "hostid" not in params
    assert "master_itemid" not in params


def test_upsert_item_nao_duplica(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [],
        {"itemids": ["1"]},
        [{"itemid": "1"}],
        {"itemids": ["1"]},
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )
    args, _ = zabbix_mock.call.call_args_list[3]
    assert args[0] == "item.update"
    assert args[1]["itemid"] == "1"



from unittest.mock import MagicMock

from configurar_zabbix import SEV_HIGH, upsert_triggers


def _make_api_with_items(keys, existing_triggers=None):
    existing_triggers = existing_triggers or {}
    api = MagicMock()
    counter = {"n": 30000}

    def side_effect(method, params=None):
        params = params or {}
        if method == "item.get":
            return [{"itemid": str(100 + i), "key_": k} for i, k in enumerate(keys)]
        if method == "trigger.get":
            desc = params.get("filter", {}).get("description", "")
            if desc in existing_triggers:
                return [{"triggerid": existing_triggers[desc], "description": desc}]
            return []
        if method == "trigger.create":
            counter["n"] += 1
            return {"triggerids": [str(counter["n"])]}
        if method == "trigger.update":
            return {"triggerids": [params["triggerid"]]}
        return []

    api.call.side_effect = side_effect
    return api


def test_upsert_triggers_cria_apenas_triggers_compativeis_com_os_itens_do_no():
    topic = "elo5/esp32-porta-01/status"
    master_key = f"mqtt_status.sh[\"{topic}\"]"
    api = _make_api_with_items([master_key, "esp32.porta", "esp32.panico"])
    upsert_triggers(api, host_id="10684", host_name="esp32-porta-01", topic=topic)
    creates = [c.args[1] for c in api.call.call_args_list if c.args[0] == "trigger.create"]
    descs = {c["description"] for c in creates}
    assert "[esp32-porta-01] Botão de pânico acionado" in descs
    assert "[esp32-porta-01] Porta aberta por mais de {$PORTA.TEMPO}" in descs
    assert "[esp32-porta-01] Sem telemetria MQTT há {$ESP32.SEM_DADOS}" in descs
    assert not any("Temperatura" in d or "Invasão" in d for d in descs)
    panico = next(c for c in creates if "pânico" in c["description"])
    assert panico["priority"] == SEV_HIGH


def test_upsert_triggers_atualiza_em_reexecucao_idempotente():
    topic = "elo5/esp32-rack-01/status"
    desc_crit = "[esp32-rack-01] Temperatura crítica acima de {$TEMP.CRITICO}°C"
    desc_warn = "[esp32-rack-01] Temperatura em alerta acima de {$TEMP.ALERTA}°C"
    api = _make_api_with_items(["esp32.temp"], {desc_crit: "25232"})
    upsert_triggers(api, host_id="10685", host_name="esp32-rack-01", topic=topic)
    updates = [c.args[1] for c in api.call.call_args_list if c.args[0] == "trigger.update"]
    creates = [c.args[1] for c in api.call.call_args_list if c.args[0] == "trigger.create"]
    assert len(updates) == 1 and updates[0]["triggerid"] == "25232"
    assert len(creates) == 1 and creates[0]["description"] == desc_warn


def test_upsert_triggers_configura_dependencies_hierarquicas():
    topic = "elo5/esp32-rack-01/status"
    master_key = f'mqtt_status.sh["{topic}"]'
    api = _make_api_with_items([master_key, "esp32.temp", "esp32.invasoes"])
    upsert_triggers(api, host_id="10685", host_name="esp32-rack-01", topic=topic)

    creates = {c.args[1]["description"]: c.args[1] for c in api.call.call_args_list if c.args[0] == "trigger.create"}
    offline_desc = "[esp32-rack-01] Sem telemetria MQTT há {$ESP32.SEM_DADOS}"
    crit_desc = "[esp32-rack-01] Temperatura crítica acima de {$TEMP.CRITICO}°C"
    warn_desc = "[esp32-rack-01] Temperatura em alerta acima de {$TEMP.ALERTA}°C"

    assert offline_desc in creates
    assert creates[offline_desc]["dependencies"] == []
    assert creates[crit_desc]["dependencies"] == [{"triggerid": "30001"}]
    assert creates[warn_desc]["dependencies"] == [{"triggerid": "30001"}, {"triggerid": "30003"}]


def test_upsert_services_and_sla_cria_arvore_e_sla():
    from configurar_zabbix import upsert_services_and_sla

    api = MagicMock()
    api.call.side_effect = [
        [], {"serviceids": ["10"]},
        [], {"serviceids": ["11"]},
        [], {"serviceids": ["12"]},
        [], {"serviceids": ["13"]},
        [], {"slaids": ["1"]},
    ]
    upsert_services_and_sla(api)

    methods = [c.args[0] for c in api.call.call_args_list]
    assert methods.count("service.create") == 4
    assert methods.count("sla.create") == 1
    sla_payload = [c.args[1] for c in api.call.call_args_list if c.args[0] == "sla.create"][0]
    assert sla_payload["slo"] == 99.9
    assert sla_payload["service_tags"] == [{"tag": "cpd", "operator": 0, "value": "core"}]
