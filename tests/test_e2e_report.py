import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import scripts.suite_testes_rack as suite


def test_export_e2e_report_pass_calculates_recovery_and_writes_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(suite, "REPORT_DIR", tmp_path)
    started = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)

    problems = [
        {"objectid": "25232", "eventid": "4101", "clock": "1764158405", "name": "Temperatura Crítica"},
        {"objectid": "25235", "eventid": "4102", "clock": "1764158410", "name": "Porta Aberta"},
    ]
    recoveries = [
        {"objectid": "25232", "eventid": "4103", "clock": "1764158412", "name": "Temperatura Crítica"},
        {"objectid": "25235", "eventid": "4104", "clock": "1764158418", "name": "Porta Aberta"},
    ]

    report_path = suite.export_e2e_report(
        started_at_utc=started,
        trigger_ids=["25232", "25235", "25236"],
        problems=problems,
        recoveries=recoveries,
        status="PASS",
    )

    latest_path = tmp_path / "e2e_latest.json"
    assert report_path.exists()
    assert latest_path.exists()

    data = json.loads(latest_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["status"] == "PASS"
    assert data["error"] is None
    assert data["summary"] == {"total_triggers": 3, "passed": 2, "failed": 1}

    by_id = {item["triggerid"]: item for item in data["triggers"]}
    assert by_id["25232"]["problem_eventid"] == "4101"
    assert by_id["25232"]["ok_eventid"] == "4103"
    assert by_id["25232"]["recovery_seconds"] == 7
    assert by_id["25235"]["recovery_seconds"] == 8
    assert by_id["25236"]["recovery_seconds"] is None


def test_export_e2e_report_fail_records_error_message(tmp_path, monkeypatch):
    monkeypatch.setattr(suite, "REPORT_DIR", tmp_path)
    started = datetime(2026, 11, 26, 12, 10, 0, tzinfo=timezone.utc)

    report_path = suite.export_e2e_report(
        started_at_utc=started,
        trigger_ids=["25232"],
        problems=[],
        recoveries=[],
        status="FAIL",
        error_message="Timeout aguardando trigger 25232",
    )

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["status"] == "FAIL"
    assert data["error"] == "Timeout aguardando trigger 25232"
    assert data["summary"] == {"total_triggers": 1, "passed": 0, "failed": 1}


def test_main_restores_baseline_via_finally_when_alarm_stage_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(suite, "REPORT_DIR", tmp_path)

    published = []
    monkeypatch.setattr(suite, "publish_mqtt", lambda payload, retain=True: published.append((dict(payload), retain)))

    fake_client = MagicMock()
    fake_client.call.return_value = [
        {"itemid": "1", "key_": "esp32.temp", "name": "Temp"},
        {"itemid": "2", "key_": "esp32.umid", "name": "Umid"},
        {"itemid": "3", "key_": "esp32.porta", "name": "Porta"},
        {"itemid": "4", "key_": "esp32.distancia", "name": "Dist"},
        {"itemid": "5", "key_": "esp32.invasoes", "name": "Inv"},
    ]
    monkeypatch.setattr(suite, "ZabbixClient", lambda *args, **kwargs: fake_client)

    def fake_wait_item(client, itemid, predicate, label, timeout=30):
        if len(published) >= 2 and itemid == "1":
            raise RuntimeError("Falha simulada após disparo de temperatura crítica")
        return "0"

    monkeypatch.setattr(suite, "wait_for_item", fake_wait_item)
    monkeypatch.setattr(suite, "wait_for_trigger", lambda *args, **kwargs: "1")

    rc = suite.main()
    assert rc == 1
    assert len(published) >= 3
    # Primeira publicação: baseline inicial; segunda: alarme temp; última (via finally): restauro baseline
    assert published[1][0]["estado"] == "ALERTA_TEMP"
    assert published[-1] == (suite.BASELINE_PAYLOAD, True)

    latest_data = json.loads((tmp_path / "e2e_latest.json").read_text(encoding="utf-8"))
    assert latest_data["status"] == "FAIL"
    assert "Falha simulada" in latest_data["error"]


def test_main_does_not_publish_baseline_if_login_fails_before_alarm(tmp_path, monkeypatch):
    monkeypatch.setattr(suite, "REPORT_DIR", tmp_path)

    published = []
    monkeypatch.setattr(suite, "publish_mqtt", lambda payload, retain=True: published.append((dict(payload), retain)))

    fake_client = MagicMock()
    fake_client.login.side_effect = RuntimeError("Credenciais Zabbix inválidas")
    monkeypatch.setattr(suite, "ZabbixClient", lambda *args, **kwargs: fake_client)

    rc = suite.main()
    assert rc == 1
    assert published == []
