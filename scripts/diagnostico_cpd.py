#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

PROM_URL = os.getenv("PROM_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
HOSTS_ZABBIX = ("esp32-porta-01", "esp32-rack-01")

SEV_NAMES = {
    "0": "Not classified",
    "1": "Information",
    "2": "Warning",
    "3": "Average",
    "4": "High",
    "5": "Disaster",
}


def http_get_json(url: str, timeout: int = 5):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def prom_query(expr: str):
    url = f"{PROM_URL}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    return http_get_json(url).get("data", {}).get("result", [])


DOCKER_STACK_PREFIX = os.getenv("DOCKER_STACK_PREFIX", "cpd-")


def _extract_health(status_text: str) -> str:
    lowered = status_text.lower()
    if "(healthy)" in lowered:
        return "healthy"
    if "(unhealthy)" in lowered:
        return "unhealthy"
    if "(health: starting)" in lowered or "(starting)" in lowered:
        return "starting"
    return "n/a"


def check_docker_stack():
    print(f"=== [Docker] Estado e Saúde dos Contêineres ('{DOCKER_STACK_PREFIX}*') ===")
    cmd = ["docker", "ps", "-a", "--format", "{{json .}}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
    except OSError as exc:
        print(f"  Erro ao executar docker: {exc}")
        print()
        return
    except subprocess.TimeoutExpired:
        print("  Timeout ao consultar o daemon do Docker.")
        print()
        return

    if proc.returncode != 0:
        err_msg = (proc.stderr or "").strip() or f"exit code {proc.returncode}"
        print(f"  Falha ao listar contêineres: {err_msg}")
        print()
        return

    containers = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        name = item.get("Names", "")
        if DOCKER_STACK_PREFIX and not name.startswith(DOCKER_STACK_PREFIX):
            continue
        state = (item.get("State") or "unknown").lower()
        status = item.get("Status") or ""
        health = _extract_health(status)
        ok = (state == "running") and (health != "unhealthy")
        containers.append((name, state, health, status, ok))

    if not containers:
        print(f"  Nenhum contêiner encontrado com prefixo '{DOCKER_STACK_PREFIX}'.")
        print()
        return

    print(f"{'CONTAINER':<28} | {'STATE':<10} | {'HEALTH':<10} | {'STATUS'}")
    print("-" * 86)
    for name, state, health, status, ok in sorted(containers, key=lambda x: x[0]):
        flag = "OK" if ok else "ALERTA"
        print(f"{name:<28} | {state:<10} | {health:<10} | [{flag}] {status}")

    problem_count = sum(1 for c in containers if not c[4])
    print(f"  Resumo: {len(containers) - problem_count}/{len(containers)} em estado saudável/operacional.")
    print()


def check_prometheus():
    print("=== [Prometheus] Targets e CPU do Host ===")
    targets = http_get_json(f"{PROM_URL}/api/v1/targets").get("data", {}).get("activeTargets", [])
    for t in targets:
        job = t.get("labels", {}).get("job", "?")
        inst = t.get("labels", {}).get("instance", "?")
        health = t.get("health", "?")
        err = t.get("lastError", "")
        print(f"  {job:<16} | {inst:<30} | {health:<4} | err={err or '-'}")

    cpu_pct = prom_query('100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)')
    load1 = prom_query("node_load1")
    cores = prom_query('count by (instance) (node_cpu_seconds_total{mode="idle"})')

    if cpu_pct:
        print(f"  CPU (1m): {float(cpu_pct[0]['value'][1]):.2f}%")
    if load1:
        print(f"  Load1:    {load1[0]['value'][1]}")
    if cores:
        print(f"  CPUs:     {cores[0]['value'][1]}")
    print()


def check_containers():
    print("=== [cAdvisor] CPU e Memória RSS dos Containers ===")
    ignored = {
        "/", "/.lxc", "/docker", "/docker/buildkit",
        "/init.scope", "/system.slice", "/user.slice",
    }

    def aggregate(expr: str):
        acc = {}
        for r in prom_query(expr):
            m = r.get("metric", {})
            label = (
                m.get("name")
                or m.get("container_label_com_docker_compose_service")
                or m.get("id", "")
            )
            if not label or label in ignored:
                continue
            acc[label] = acc.get(label, 0.0) + float(r["value"][1])
        return acc

    cpu_map = aggregate('sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[1m]))')
    mem_map = {
        k: v / (1024 * 1024)
        for k, v in aggregate('sum by (name) (container_memory_rss{name!=""})').items()
    }

    names = sorted(set(cpu_map) | set(mem_map))
    print(f"{'CONTAINER':<32} | {'CPU (cores)':>11} | {'MEM RSS (MiB)':>13}")
    print("-" * 62)
    for c in names:
        print(f"{c:<32} | {cpu_map.get(c, 0.0):>11.4f} | {mem_map.get(c, 0.0):>13.1f}")
    print()


def check_mosquitto():
    print("=== [Mosquitto Exporter] Séries do job='mosquitto' ===")
    results = prom_query('{job="mosquitto"}')
    print(f"{'METRICA':<44} | {'LABELS':<34} | {'VALOR':>12}")
    print("-" * 96)
    for r in sorted(results, key=lambda x: x["metric"].get("__name__", "")):
        metric = dict(r.get("metric", {}))
        name = metric.pop("__name__", "?")
        metric.pop("job", None)
        metric.pop("instance", None)
        labels_str = ", ".join(f"{k}={v}" for k, v in sorted(metric.items())) or "-"
        val = r.get("value", ["", ""])[1]
        print(f"{name:<44} | {labels_str[:34]:<34} | {val:>12}")
    print()


MQTT_CONTAINER = os.getenv("MQTT_CONTAINER", "cpd-mosquitto")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "elo5/+/status")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = os.getenv("MQTT_PORT", "1883")
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")


def check_mqtt_status():
    print(f"=== [Mosquitto] Estados Retidos em '{MQTT_TOPIC}' ===")
    cmd = [
        "docker", "exec", MQTT_CONTAINER,
        "mosquitto_sub",
        "-h", MQTT_HOST,
        "-p", str(MQTT_PORT),
        "-t", MQTT_TOPIC,
        "-v",
        "-W", "2",
    ]
    if MQTT_USER:
        cmd.extend(["-u", MQTT_USER])
    if MQTT_PASSWORD:
        cmd.extend(["-P", MQTT_PASSWORD])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
    except OSError as exc:
        print(f"  Erro ao executar docker/mosquitto_sub: {exc}")
        print()
        return
    except subprocess.TimeoutExpired:
        print("  Timeout ao aguardar resposta do mosquitto_sub dentro do contêiner.")
        print()
        return

    if proc.returncode not in (0, 27):
        err_msg = (proc.stderr or "").strip() or f"exit code {proc.returncode}"
        print(f"  Falha ao consultar broker ({MQTT_CONTAINER}): {err_msg}")
        print()
        return

    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        print("  Nenhuma mensagem retida encontrada (ou broker sem publicações retidas).")
        print()
        return

    for ln in lines:
        parts = ln.split(maxsplit=1)
        topic = parts[0]
        payload = parts[1] if len(parts) > 1 else "(vazio)"
        print(f"  {topic:<34} -> {payload}")
    print()


def check_zabbix():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from configurar_zabbix import API_URL, ZABBIX_PASSWORD, ZABBIX_USER, ZabbixAPI

    print("=== [Zabbix] Problemas Ativos, Triggers e Macros ===")
    api = ZabbixAPI(API_URL, ZABBIX_USER, ZABBIX_PASSWORD)
    api.login()
    try:
        for host in HOSTS_ZABBIX:
            h = api.call("host.get", {"filter": {"host": host}, "output": ["hostid", "host"]})
            if not h:
                print(f"  Host {host}: não encontrado")
                continue
            hostid = h[0]["hostid"]

            probs = api.call("problem.get", {
                "hostids": [hostid],
                "output": ["eventid", "name", "severity"],
                "sortfield": "eventid",
                "sortorder": "DESC",
            })
            triggers = api.call("trigger.get", {
                "hostids": [hostid],
                "output": ["triggerid", "description", "expression", "priority", "status"],
                "expandExpression": True,
                "sortfield": "description",
            })
            macros = api.call("usermacro.get", {
                "hostids": [hostid],
                "output": ["macro", "value"],
            })

            print(f"\n-- Host: {host} --")
            print(f"  Problemas ativos ({len(probs)}):")
            for p in probs:
                sev = SEV_NAMES.get(str(p["severity"]), str(p["severity"]))
                print(f"    [sev={sev}] {p['name']} (eventid={p['eventid']})")

            print(f"  Triggers ({len(triggers)}):")
            for t in triggers:
                sev = SEV_NAMES.get(str(t["priority"]), str(t["priority"]))
                st = "ENABLED" if str(t["status"]) == "0" else "DISABLED"
                print(f"    [{sev} | {st}] {t['description']} -> {t['expression']}")

            print(f"  Macros de host ({len(macros)}):")
            for m in sorted(macros, key=lambda x: x["macro"]):
                print(f"    {m['macro']} = {m['value']}")
    finally:
        api.logout()
    print()


def main():
    parser = argparse.ArgumentParser(description="Diagnóstico rápido da stack CPD (Prometheus + Zabbix)")
    parser.add_argument(
        "targets",
        nargs="*",
        default="all",
        choices=["all", "docker", "prom", "containers", "mosquitto", "mqtt", "grafana", "zabbix"],
        help="Subconjuntos a verificar (padrão: all)",
    )
    args = parser.parse_args()
    raw_targets = [args.targets] if isinstance(args.targets, str) else args.targets
    selected = set(raw_targets or ["all"])
    run_all = "all" in selected

    if run_all or "prom" in selected:
        check_prometheus()
    if run_all or "containers" in selected:
        check_containers()
    if run_all or "mosquitto" in selected:
        check_mosquitto()
    if run_all or "mqtt" in selected:
        check_mqtt_status()
    if run_all or "zabbix" in selected:
        check_zabbix()


if __name__ == "__main__":
    main()
