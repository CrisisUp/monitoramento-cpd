#!/usr/bin/env python3
"""
Suíte de Testes Ponta a Ponta (E2E) — Rack CPD (esp32-rack-01)
Valida ingestão MQTT mTLS (8883), itens dependentes no Zabbix 7.0 e disparo/recuperação
das triggers 25232 (Temperatura), 25235 (Porta Aberta) e 25236 (Invasão).
"""

import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import time
import urllib.request

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://localhost:8080/api_jsonrpc.php")
ZABBIX_USER = os.getenv("ZABBIX_USER", "Admin")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "zabbix")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "").strip()
HOST_NAME = os.getenv("ZABBIX_HOST", "esp32-rack-01")

MQTT_CONTAINER = os.getenv("MQTT_CONTAINER", "cpd-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "elo5/esp32-rack-01/status")

CONTAINER_CA_FILE = "/mosquitto/certs/ca.crt"
CONTAINER_CERT_FILE = "/mosquitto/certs/zabbix-client.crt"
CONTAINER_KEY_FILE = "/mosquitto/certs/zabbix-client.key"

TEST_HIGH_TEMP = float(os.getenv("TEST_HIGH_TEMP", "34.5"))
POLL_TIMEOUT_SEC = int(os.getenv("POLL_TIMEOUT_SEC", "60"))
POLL_INTERVAL_SEC = 3

TRIGGER_TEMP_ID = os.getenv("TRIGGER_TEMP_ID", "25232")
TRIGGER_PORTA_ID = os.getenv("TRIGGER_PORTA_ID", "25235")
TRIGGER_INVASAO_ID = os.getenv("TRIGGER_INVASAO_ID", "25236")

BASELINE_PAYLOAD = {
    "device_id": "esp32-rack-01",
    "temp_c": 23.4,
    "umid_pct": 47.5,
    "porta": "FECHADA",
    "modo": "ARMADO",
    "estado": "NORMAL",
    "dist_cm": 85.0,
    "invasoes": 0,
    "ambiente": "CPD_PRINCIPAL",
    "luz": "CLARO",
    "simulated": True,
}


class ZabbixClient:
    def __init__(self, url: str, user: str, password: str, token: str = ""):
        self.url = url if url.endswith("/api_jsonrpc.php") else f"{url.rstrip('/')}/api_jsonrpc.php"
        self.user = user
        self.password = password
        self.token = token
        self._req_id = 0

    def call(self, method: str, params: dict, auth: bool = True):
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": self._req_id}
        headers = {"Content-Type": "application/json-rpc"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        if "error" in body:
            raise RuntimeError(f"Erro API Zabbix ({method}): {body['error']}")
        return body["result"]

    def login(self) -> None:
        if self.token:
            # Valida se o token configurado está ativo
            try:
                self.call("host.get", {"output": ["hostid"], "limit": 1}, auth=True)
                return
            except Exception:
                self.token = ""
        self.token = self.call(
            "user.login",
            {"username": self.user, "password": self.password},
            auth=False,
        )


def publish_mqtt(payload_dict: dict, retain: bool = True) -> None:
    if not shutil.which("docker"):
        raise RuntimeError("Binário 'docker' não encontrado no PATH.")

    raw_json = json.dumps(payload_dict, separators=(",", ":"))
    cmd = [
        "docker", "exec", MQTT_CONTAINER,
        "mosquitto_pub",
        "-h", "localhost",
        "-p", str(MQTT_PORT),
    ]
    if MQTT_PORT == 8883:
        cmd.extend([
            "--cafile", CONTAINER_CA_FILE,
            "--cert", CONTAINER_CERT_FILE,
            "--key", CONTAINER_KEY_FILE,
        ])
    cmd.extend(["-t", MQTT_TOPIC, "-m", raw_json])
    if retain:
        cmd.append("-r")

    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=15)


def wait_for_item(client: ZabbixClient, itemid: str, predicate, label: str, timeout: int = POLL_TIMEOUT_SEC) -> str:
    deadline = time.time() + timeout
    last_val = None
    while time.time() < deadline:
        res = client.call("item.get", {"output": ["itemid", "lastvalue"], "itemids": [itemid]})
        if res:
            last_val = res[0].get("lastvalue")
            if last_val is not None and predicate(last_val):
                return str(last_val)
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(f"Timeout ({timeout}s) aguardando {label} (itemid={itemid}, último valor={last_val!r})")


def wait_for_trigger(client: ZabbixClient, triggerid: str, expected_value: str, label: str, timeout: int = POLL_TIMEOUT_SEC) -> str:
    """expected_value: '1' para PROBLEM, '0' para OK."""
    deadline = time.time() + timeout
    last_state = None
    state_name = "PROBLEM (1)" if expected_value == "1" else "OK (0)"
    while time.time() < deadline:
        res = client.call(
            "trigger.get",
            {"output": ["triggerid", "description", "value"], "triggerids": [triggerid]},
        )
        if res:
            last_state = str(res[0].get("value"))
            if last_state == expected_value:
                return last_state
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(
        f"Timeout ({timeout}s) aguardando trigger {triggerid} ({label}) -> {state_name} (atual={last_state!r})"
    )


REPORT_DIR = Path(os.getenv("E2E_REPORT_DIR", "reports"))


def export_e2e_report(
    started_at_utc: datetime,
    trigger_ids: list[str],
    problems: list[dict],
    recoveries: list[dict],
    status: str,
    error_message: str | None = None,
) -> Path:
    finished_at_utc = datetime.now(timezone.utc)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    prob_by_tid = {str(ev["objectid"]): ev for ev in problems}
    ok_by_tid = {str(ev["objectid"]): ev for ev in recoveries}

    triggers_summary = []
    for tid in [str(t) for t in trigger_ids]:
        ev_p = prob_by_tid.get(tid)
        ev_o = ok_by_tid.get(tid)
        p_clock = int(ev_p["clock"]) if ev_p else None
        o_clock = int(ev_o["clock"]) if ev_o else None
        triggers_summary.append(
            {
                "triggerid": tid,
                "name": (ev_p or ev_o or {}).get("name", ""),
                "problem_eventid": str(ev_p["eventid"]) if ev_p else None,
                "problem_timestamp_utc": (
                    datetime.fromtimestamp(p_clock, tz=timezone.utc).isoformat()
                    if p_clock is not None
                    else None
                ),
                "ok_eventid": str(ev_o["eventid"]) if ev_o else None,
                "ok_timestamp_utc": (
                    datetime.fromtimestamp(o_clock, tz=timezone.utc).isoformat()
                    if o_clock is not None
                    else None
                ),
                "recovery_seconds": (
                    o_clock - p_clock
                    if (p_clock is not None and o_clock is not None)
                    else None
                ),
            }
        )

    payload = {
        "schema_version": "1.0",
        "host": HOST_NAME,
        "status": status,
        "started_at_utc": started_at_utc.isoformat(),
        "finished_at_utc": finished_at_utc.isoformat(),
        "duration_seconds": round((finished_at_utc - started_at_utc).total_seconds(), 2),
        "error": error_message,
        "summary": {
            "total_triggers": len(triggers_summary),
            "passed": sum(
                1 for t in triggers_summary if t["problem_eventid"] and t["ok_eventid"]
            ),
            "failed": sum(
                1 for t in triggers_summary if not (t["problem_eventid"] and t["ok_eventid"])
            ),
        },
        "triggers": triggers_summary,
    }

    stamp = finished_at_utc.strftime("%Y%m%d_%H%M%S")
    history_file = REPORT_DIR / f"e2e_{stamp}.json"
    latest_file = REPORT_DIR / "e2e_latest.json"
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    history_file.write_text(rendered, encoding="utf-8")
    latest_file.write_text(rendered, encoding="utf-8")
    return history_file


def audit_generated_events(
    rpc_client,
    trigger_ids: list[str],
    time_from: int,
    wait_timeout: float = 5.0,
    started_at_utc: datetime | None = None,
) -> Path:
    """Consulta event.get no Zabbix, imprime os eventids e falha se faltar PROBLEM ou OK."""
    expected = {str(tid) for tid in trigger_ids}
    deadline = time.monotonic() + wait_timeout
    events: list[dict] = []
    problems: list[dict] = []
    recoveries: list[dict] = []
    missing_problem: list[str] = []
    missing_ok: list[str] = []

    while True:
        events = (
            rpc_client.call(
                "event.get",
                {
                    "output": ["eventid", "objectid", "clock", "ns", "value", "name"],
                    "source": 0,
                    "object": 0,
                    "objectids": trigger_ids,
                    "time_from": time_from,
                    "sortfield": ["clock", "eventid"],
                    "sortorder": "ASC",
                },
            )
            or []
        )

        problems = [ev for ev in events if str(ev.get("value")) == "1"]
        recoveries = [ev for ev in events if str(ev.get("value")) == "0"]

        got_problem = {str(ev.get("objectid")) for ev in problems}
        got_ok = {str(ev.get("objectid")) for ev in recoveries}

        missing_problem = sorted(expected - got_problem)
        missing_ok = sorted(expected - got_ok)

        if not missing_problem and not missing_ok:
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(0.5)

    print("\n" + "-" * 72)
    print(f"AUDITORIA DE EVENTOS ZABBIX (desde epoch={time_from})")
    print("-" * 72)
    print(
        f"Total de eventos: {len(events)} "
        f"| PROBLEM: {len(problems)} | OK: {len(recoveries)}"
    )

    for label, group in (("PROBLEM", problems), ("OK", recoveries)):
        ids = [str(ev["eventid"]) for ev in group]
        print(f"  [{label}] eventids: {', '.join(ids) if ids else '(nenhum)'}")
        for ev in group:
            ts = datetime.fromtimestamp(int(ev["clock"])).strftime("%H:%M:%S")
            print(
                f"    - eventid={ev['eventid']} | triggerid={ev['objectid']} "
                f"| hora={ts} | {ev.get('name', '')}"
            )

    ref_start = started_at_utc or datetime.fromtimestamp(time_from, tz=timezone.utc)
    if missing_problem or missing_ok:
        detalhes = []
        if missing_problem:
            detalhes.append(f"sem PROBLEM: {', '.join(missing_problem)}")
        if missing_ok:
            detalhes.append(f"sem OK: {', '.join(missing_ok)}")
        err_msg = "Auditoria de eventos Zabbix incompleta (" + " | ".join(detalhes) + ")"
        report_path = export_e2e_report(
            ref_start, trigger_ids, problems, recoveries, status="FAIL", error_message=err_msg
        )
        print(f"[RELATÓRIO] Histórico salvo em: {report_path}")
        raise RuntimeError(err_msg)

    report_path = export_e2e_report(
        ref_start, trigger_ids, problems, recoveries, status="PASS"
    )
    print(
        "[OK] Auditoria de eventos validada: PROBLEM e OK confirmados para "
        + ", ".join(sorted(expected))
    )
    print(f"[RELATÓRIO] Histórico JSON salvo em: {report_path} (e {REPORT_DIR / 'e2e_latest.json'})")
    return report_path


def main() -> int:
    started_at_utc = datetime.now(timezone.utc)
    suite_started_at = int(time.time()) - 5
    report_written = False
    print("=" * 72)
    print(f"SUÍTE DE TESTES RACK CPD — {HOST_NAME} (mTLS {MQTT_PORT} + Zabbix 7.0)")
    print("=" * 72)

    client = ZabbixClient(ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD, ZABBIX_TOKEN)

    try:
        # [1/6] Autenticação
        client.login()
        print("[1/6] Autenticação na API do Zabbix: OK")

        # [2/6] Mapeamento de itens
        items = client.call(
            "item.get",
            {
                "output": ["itemid", "key_", "name"],
                "host": HOST_NAME,
            },
        )
        by_key = {it["key_"]: it["itemid"] for it in items}
        required_keys = ["esp32.temp", "esp32.umid", "esp32.porta", "esp32.distancia", "esp32.invasoes"]
        missing = [k for k in required_keys if k not in by_key]
        if missing:
            raise RuntimeError(f"Itens ausentes no host {HOST_NAME}: {missing}")

        id_temp = by_key["esp32.temp"]
        id_umid = by_key["esp32.umid"]
        id_porta = by_key["esp32.porta"]
        id_dist = by_key["esp32.distancia"]
        id_inv = by_key["esp32.invasoes"]
        print(
            f"[2/6] Itens mapeados: temp={id_temp}(esp32.temp), umid={id_umid}(esp32.umid), "
            f"porta={id_porta}(esp32.porta), dist={id_dist}(esp32.distancia), invasoes={id_inv}(esp32.invasoes)"
        )

        # Garante estado inicial limpo antes de iniciar os cenários
        publish_mqtt(BASELINE_PAYLOAD, retain=True)
        wait_for_item(client, id_porta, lambda v: str(v).strip() == "FECHADA", "baseline porta=FECHADA")
        wait_for_item(client, id_inv, lambda v: int(float(v)) == 0, "baseline invasoes=0")

        # [3/6] Cenário 1: Temperatura Crítica -> Trigger 25232 PROBLEM
        payload_temp = {**BASELINE_PAYLOAD, "temp_c": TEST_HIGH_TEMP, "estado": "ALERTA_TEMP"}
        publish_mqtt(payload_temp, retain=True)
        val_t = wait_for_item(
            client, id_temp, lambda v: abs(float(v) - TEST_HIGH_TEMP) < 0.2, f"esp32.temp≈{TEST_HIGH_TEMP}"
        )
        wait_for_trigger(client, TRIGGER_TEMP_ID, "1", "Temperatura Crítica")
        print(f"[3/6] Temperatura crítica ({val_t}°C) + Trigger {TRIGGER_TEMP_ID} -> PROBLEM: OK")

        # [4/6] Cenário 2: Porta Aberta -> Trigger 25235 PROBLEM + Recuperação Trigger 25232 OK
        payload_porta = {**BASELINE_PAYLOAD, "porta": "ABERTA", "estado": "PORTA_ABERTA"}
        publish_mqtt(payload_porta, retain=True)
        val_p = wait_for_item(client, id_porta, lambda v: str(v).strip() == "ABERTA", "esp32.porta=ABERTA")
        wait_for_trigger(client, TRIGGER_PORTA_ID, "1", "Porta Aberta")
        wait_for_trigger(client, TRIGGER_TEMP_ID, "0", "Temperatura Crítica (recuperação)")
        print(
            f"[4/6] Porta ({val_p}) + Trigger {TRIGGER_PORTA_ID} -> PROBLEM "
            f"| Trigger {TRIGGER_TEMP_ID} -> OK: OK"
        )

        # [5/6] Cenário 3: Proximidade + Invasão -> Trigger 25236 PROBLEM
        payload_inv = {
            **BASELINE_PAYLOAD,
            "porta": "ABERTA",
            "dist_cm": 18.0,
            "invasoes": 1,
            "estado": "INVASAO",
        }
        publish_mqtt(payload_inv, retain=True)
        val_d = wait_for_item(client, id_dist, lambda v: abs(float(v) - 18.0) < 0.5, "esp32.distancia≈18.0")
        val_i = wait_for_item(client, id_inv, lambda v: int(float(v)) == 1, "esp32.invasoes=1")
        wait_for_trigger(client, TRIGGER_INVASAO_ID, "1", "Invasão Física")
        print(
            f"[5/6] Distância ({val_d}cm) + Invasões ({val_i}) + Trigger {TRIGGER_INVASAO_ID} -> PROBLEM: OK"
        )

        # [6/6] Restauração Baseline -> Recuperação Triggers 25232, 25235 e 25236 para OK
        publish_mqtt(BASELINE_PAYLOAD, retain=True)
        wait_for_item(client, id_temp, lambda v: abs(float(v) - 23.4) < 0.2, "restore esp32.temp=23.4")
        wait_for_item(client, id_porta, lambda v: str(v).strip() == "FECHADA", "restore esp32.porta=FECHADA")
        wait_for_item(client, id_inv, lambda v: int(float(v)) == 0, "restore esp32.invasoes=0")
        wait_for_trigger(client, TRIGGER_TEMP_ID, "0", "Temperatura Crítica (OK)")
        wait_for_trigger(client, TRIGGER_PORTA_ID, "0", "Porta Aberta (OK)")
        wait_for_trigger(client, TRIGGER_INVASAO_ID, "0", "Invasão Física (OK)")
        print(
            f"[6/6] Baseline restaurado + Triggers {TRIGGER_TEMP_ID}, {TRIGGER_PORTA_ID}, "
            f"{TRIGGER_INVASAO_ID} -> OK: OK"
        )

        print("=" * 72)
        print("RESULTADO FINAL: TODOS OS 6 ESTÁGIOS APROVADOS COM SUCESSO")
        audit_generated_events(
            client,
            [str(TRIGGER_TEMP_ID), str(TRIGGER_PORTA_ID), str(TRIGGER_INVASAO_ID)],
            suite_started_at,
            started_at_utc=started_at_utc,
        )
        report_written = True
        print("=" * 72)
        return 0

    except Exception as exc:
        if not report_written:
            report_path = export_e2e_report(
                started_at_utc,
                [str(TRIGGER_TEMP_ID), str(TRIGGER_PORTA_ID), str(TRIGGER_INVASAO_ID)],
                [],
                [],
                status="FAIL",
                error_message=str(exc),
            )
            print(f"[RELATÓRIO] Histórico de falha salvo em: {report_path}", file=sys.stderr)
        print(f"\n[FALHA NA SUÍTE] {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

