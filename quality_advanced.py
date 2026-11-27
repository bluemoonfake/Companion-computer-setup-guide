"""Read-only SIM7600 RF sampling via ModemManager and controlled iperf3 tests."""
import csv
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

ENV = dict(os.environ, LC_ALL="C")


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(msg):
    print(msg, flush=True)


def invoke(args, timeout=10):
    return subprocess.run(args, env=ENV, text=True, capture_output=True, timeout=timeout)


def route(target):
    p = invoke(["ip", "-j", "-4", "route", "get", target])
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or "route lookup failed")
    return json.loads(p.stdout)[0]


def route_key(r):
    return tuple(r.get(k) for k in ("dev", "gateway", "prefsrc", "src"))


def parse_kv(text):
    result = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            result[key.strip()] = value.strip()
    return result


RF_MAP = {
    "state": "modem.generic.state",
    "access_technologies": "modem.generic.access-technologies",
    "quality_pct": "modem.generic.signal-quality.value",
    "quality_recent": "modem.generic.signal-quality.recent",
    "rsrp_dbm": "modem.signal.lte.rsrp",
    "rsrq_db": "modem.signal.lte.rsrq",
    "rssi_dbm": "modem.signal.lte.rssi",
    "snr_db": "modem.signal.lte.snr",
}
RF_FIELDS = ["utc", "status", *RF_MAP]


def selected_rf(status, signal):
    combined = {**status, **signal}
    return {name: combined[key] for name, key in RF_MAP.items()
            if key in combined and combined[key] not in ("", "--", "unknown")}


class RFSampler:
    def __init__(self, modem, interval, out, iface):
        if not shutil.which("mmcli"):
            raise RuntimeError("Install modemmanager for optional RF monitoring")
        self.modem = str(modem)
        info = self.query()
        kv = parse_kv(info)
        if "SIM7600" not in kv.get("modem.generic.model", "").upper():
            raise RuntimeError("Selected modem is not identified as SIM7600")
        if not re.search(r"(?<![\w.-])" + re.escape(iface) + r"\s*\(net\)", info):
            raise RuntimeError("Selected modem does not advertise measured network interface")
        self.interval = interval
        self.out = out
        self.stop = threading.Event()
        self.samples = []
        self.thread = None
        self.failure = None

    def query(self, *extra):
        p = invoke(["mmcli", "-m", self.modem, "-K", *extra], timeout=5)
        if p.returncode:
            raise RuntimeError(p.stderr.strip() or "mmcli query failed")
        return p.stdout

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            with (self.out / "rf.csv").open("w", newline="") as f, (self.out / "rf-raw.jsonl").open("w") as raw:
                w = csv.DictWriter(f, fieldnames=RF_FIELDS)
                w.writeheader()
                while not self.stop.is_set():
                    start = time.monotonic()
                    row = {"utc": stamp(), "status": "OK"}
                    try:
                        status = parse_kv(self.query())
                        try:
                            signal = parse_kv(self.query("--signal-get"))
                        except (OSError, RuntimeError, subprocess.TimeoutExpired):
                            signal = {}
                        row.update(selected_rf(status, signal))
                        if not any(k in row for k in ("quality_pct","rsrp_dbm","rsrq_db","rssi_dbm","snr_db")):
                            row["status"] = "NO_SIGNAL_DATA"
                    except (OSError, RuntimeError, subprocess.TimeoutExpired):
                        row["status"] = "ERROR"
                    # Save selected fields only, never full modem output (IMEI/SIM identifiers).
                    w.writerow(row)
                    f.flush()
                    raw.write(json.dumps(row) + "\n")
                    raw.flush()
                    self.samples.append(row)
                    self.stop.wait(max(0, self.interval-(time.monotonic()-start)))
        except OSError as exc:
            self.failure = str(exc)

    def finish(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=12)
        samples = list(self.samples)
        good = [x for x in samples if x["status"] == "OK"]
        summary = {"samples": len(samples), "samples_ok": len(good),
                   "extended_lte_samples": sum("rsrp_dbm" in x or "rsrq_db" in x for x in good),
                   "source": "ModemManager cached/read-only values; no polling configuration changed",
                   "error": self.failure}
        for key in ("quality_pct","rsrp_dbm","rsrq_db","rssi_dbm","snr_db"):
            vals = []
            for x in good:
                try:
                    n = float(x.get(key,""))
                    if -200 < n < 200:
                        vals.append(n)
                except ValueError:
                    pass
            if vals:
                summary[key] = {"min":min(vals),"mean":sum(vals)/len(vals),"max":max(vals),"samples":len(vals)}
        return summary


def throughput_suite(a, out, iface, limits, measure):
    if not shutil.which("iperf3"):
        raise RuntimeError("Install iperf3 first: sudo apt install iperf3")
    help_text = invoke(["iperf3","--help"]).stdout
    if "--bind-dev" not in help_text:
        raise RuntimeError("Installed iperf3 does not support --bind-dev; no unbound test will run")
    if route(a.iperf_server).get("dev") != iface:
        raise RuntimeError("iperf server route is not the selected cellular interface")
    if route(a.internet).get("dev") != iface:
        raise RuntimeError("latency target route is not the selected cellular interface")
    plan = [("tcp-upload", False, False, a.tcp_mbps),
            ("tcp-download", False, True, a.tcp_mbps)]
    plan += [(f"udp-upload-{rate}m", True, False, rate) for rate in a.udp_mbps]
    plan += [(f"udp-download-{rate}m", True, True, rate) for rate in a.udp_mbps]
    results = []
    for label, udp, reverse, rate in plan:
        before = route(a.iperf_server)
        if before.get("dev") != iface:
            raise RuntimeError("iperf server route changed; stopping load tests")
        args = ["iperf3","-4","-c",a.iperf_server,"-p",str(a.iperf_port),
                "--bind-dev",iface,"-J","-t",str(a.load_duration+5),
                "-b",f"{rate}M","--connect-timeout","5000"]
        if udp:
            args += ["-u","-l","1200"]
        if reverse:
            args += ["-R"]
        log(f"\n[LOAD] {label}: offered/paced {rate} Mbps; ping concurrently")
        started = stamp()
        proc = subprocess.Popen(args, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(proc.communicate, timeout=a.load_duration+30)
                # This is a requested overlap, not a proven fully saturated interval.
                time.sleep(2)
                ping_start = stamp()
                latency = measure(out, "loaded-"+label, a.internet, iface, a.baseline_rate,
                                  a.load_duration, limits) if proc.poll() is None else None
                ping_end = stamp()
                try:
                    stdout, stderr = future.result()
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate()
            finished = stamp()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        (out / f"{label}.iperf.json").write_text(stdout)
        (out / f"{label}.stderr.txt").write_text(stderr)
        try:
            data = json.loads(stdout)
        except ValueError:
            data = {}
        end = data.get("end", {})
        after = route(a.iperf_server)
        errors = []
        if proc.returncode != 0 or not end or data.get("error"):
            errors.append(data.get("error") or stderr.strip() or f"iperf exit={proc.returncode}")
        if route_key(before) != route_key(after):
            errors.append("route changed")
        if not latency or latency["measurement"] != "COMPLETE":
            errors.append("loaded ping missing or invalid")
        row = {"label": label, "status": "INVALID" if errors else "COMPLETE",
               "error": "; ".join(errors), "offered_mbps": rate, "command": args,
               "route_before": before, "route_after": after, "started_utc": started,
               "finished_utc": finished, "ping_started_utc": ping_start, "ping_finished_utc": ping_end,
               "loaded_latency": latency, "end_sum_sent": end.get("sum_sent"),
               "end_sum_received": end.get("sum_received"), "end_sum": end.get("sum")}
        results.append(row)
        (out / "throughput-summary.json").write_text(json.dumps(results,indent=2)+"\n")
        received = end.get("sum_received") or end.get("sum") or {}
        bps = received.get("bits_per_second")
        log(f"[{row['status']}] {label} receiver/summary Mbps={bps/1e6 if bps is not None else '-'}; "
            f"UDP loss={received.get('lost_percent','-')}%; jitter={received.get('jitter_ms','-')} ms")
        if errors:
            log("[WARN] " + row["error"])
        time.sleep(3)
    return results
