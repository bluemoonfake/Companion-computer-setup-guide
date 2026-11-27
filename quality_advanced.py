"""Optional RM520N RF logging and controlled iperf3 tests; no configuration changes."""
import csv
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

ENV = dict(os.environ, LC_ALL="C")
MODEM = ("2c7c", "0801")


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


def modem_port(port):
    p = Path(port).resolve(strict=True)
    if not re.fullmatch(r"/dev/ttyUSB\d+", str(p)):
        return False
    d = (Path("/sys/class/tty") / p.name / "device").resolve(strict=True)
    for q in (d, *d.parents):
        if (q / "idVendor").is_file() and (q / "idProduct").is_file():
            return ((q / "idVendor").read_text().strip().lower(),
                    (q / "idProduct").read_text().strip().lower()) == MODEM
    return False


RF_FIELDS = ["utc", "status", "state", "rat", "lte_cell_id", "lte_pci",
             "lte_earfcn", "lte_band", "lte_rsrp_dbm", "lte_rsrq_db", "lte_rssi_dbm",
             "lte_sinr_raw", "lte_cqi_raw", "nr_pci", "nr_arfcn", "nr_band",
             "nr_rsrp_dbm", "nr_rsrq_db", "nr_sinr_db", "nr_cell_id", "nr_bw_raw",
             "nr_scs_raw", "qcsq_raw"]


def parse_qeng(raw):
    """Quectel RG520N/RM5x0N AT manual V1.1 serving-cell layouts."""
    result = {}
    for line in raw.splitlines():
        if not line.startswith("+QENG:"):
            continue
        f = next(csv.reader([line.split(":", 1)[1].strip()], skipinitialspace=True))
        if not f:
            continue
        if f[0] == "servingcell":
            if len(f) < 2:
                continue
            result["state"] = f[1]
            if len(f) < 3:
                continue
            f = f[2:]
        if f[0] == "LTE" and len(f) >= 16:
            result.update(dict(zip(
                ("lte_cell_id","lte_pci","lte_earfcn","lte_band"),
                (f[4],f[5],f[6],f[7]))))
            result.update(dict(zip(("lte_rsrp_dbm","lte_rsrq_db","lte_rssi_dbm",
                                    "lte_sinr_raw","lte_cqi_raw"), f[11:16])))
            result.setdefault("rat", "LTE")
        elif f[0] == "NR5G-NSA" and len(f) >= 11:
            result.update(dict(zip(("nr_pci","nr_rsrp_dbm","nr_sinr_db","nr_rsrq_db",
                                    "nr_arfcn","nr_band","nr_bw_raw","nr_scs_raw"), f[3:11])))
            result["rat"] = "NR5G-NSA"
        elif f[0] == "NR5G-SA" and len(f) >= 14:
            result.update(dict(zip(("nr_cell_id","nr_pci","nr_arfcn","nr_band","nr_bw_raw",
                                    "nr_rsrp_dbm","nr_rsrq_db","nr_sinr_db","nr_scs_raw"),
                                   (f[4],f[5],f[7],f[8],f[9],f[10],f[11],f[12],f[13]))))
            result["rat"] = "NR5G-SA"
    return result


class RFSampler:
    def __init__(self, port, interval, out):
        if not modem_port(port):
            raise RuntimeError("AT port is not a detected RM520N ttyUSB device")
        if not shutil.which("fuser"):
            raise RuntimeError("Install psmisc to check whether the AT port is occupied")
        if invoke(["systemctl", "is-active", "--quiet", "ModemManager"]).returncode == 0:
            raise RuntimeError("ModemManager active; do not compete for its AT port")
        if invoke(["fuser", str(Path(port).resolve())]).returncode != 1:
            raise RuntimeError("AT port busy or fuser check failed; close minicom first")
        try:
            import serial
        except ImportError:
            raise ImportError("Install python3-serial for optional RF monitoring") from None
        self.ser = serial.Serial(port, 115200, timeout=.2, write_timeout=2, exclusive=True)
        self.interval = interval
        self.out = out
        self.stop = threading.Event()
        self.samples = []
        self.thread = None
        try:
            if "RM520N" not in self.at("ATI").upper():
                raise RuntimeError("Port did not identify RM520N")
        except BaseException:
            self.ser.close()
            raise

    def at(self, command):
        self.ser.reset_input_buffer()
        self.ser.write((command + "\r").encode("ascii"))
        buf = b""
        until = time.monotonic() + 4
        while time.monotonic() < until:
            buf += self.ser.read(1024)
            raw = buf.decode("ascii", errors="replace")
            lines = [x.strip() for x in raw.splitlines()]
            if "OK" in lines:
                return raw
            if any(x == "ERROR" or x.startswith(("+CME ERROR", "+CMS ERROR")) for x in lines):
                raise RuntimeError(command + " rejected by modem")
        raise RuntimeError(command + " timed out")

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            with (self.out / "rf.csv").open("w", newline="") as f, (self.out / "rf-raw.jsonl").open("w") as raw:
                w = csv.DictWriter(f, fieldnames=RF_FIELDS)
                w.writeheader()
                while not self.stop.is_set():
                    row = {"utc": stamp(), "status": "OK"}
                    record = {"utc": row["utc"]}
                    start = time.monotonic()
                    try:
                        q = self.at('AT+QENG="servingcell"')
                        record["qeng"] = q
                        row.update(parse_qeng(q))
                        if not row.get("state") and not row.get("rat"):
                            row["status"] = "UNPARSED"
                        try:
                            qcsq = self.at("AT+QCSQ")
                            record["qcsq"] = qcsq
                            row["qcsq_raw"] = " ".join(x for x in qcsq.splitlines() if x.startswith("+QCSQ"))
                        except RuntimeError as exc:
                            record["qcsq_error"] = str(exc)
                    except (OSError, RuntimeError, ValueError) as exc:
                        row["status"] = "ERROR"
                        record["error"] = str(exc)
                    w.writerow(row)
                    f.flush()
                    raw.write(json.dumps(record) + "\n")
                    raw.flush()
                    self.samples.append(row)
                    self.stop.wait(max(0, self.interval-(time.monotonic()-start)))
        finally:
            self.ser.close()

    def finish(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=12)
        samples = list(self.samples)
        valid = [s for s in samples if s.get("status") == "OK"]
        from collections import Counter
        summary = {"samples": len(samples), "samples_ok": len(valid),
                   "rat_counts": dict(Counter(s.get("rat", "unknown") for s in valid)),
                   "state_counts": dict(Counter(s.get("state", "unknown") for s in valid))}
        def signature(s):
            return tuple(s.get(k) for k in ("rat","lte_cell_id","lte_pci","lte_earfcn",
                                            "nr_cell_id","nr_pci","nr_arfcn"))
        summary["observed_cell_signature_changes"] = sum(
            signature(a) != signature(b) for a,b in zip(valid, valid[1:]))
        for k in ("lte_rsrp_dbm","lte_rsrq_db","nr_rsrp_dbm","nr_rsrq_db","nr_sinr_db"):
            vals = []
            for s in valid:
                try:
                    n = float(s.get(k, ""))
                    if -200 < n < 100:  # discard common out-of-range sentinels
                        vals.append(n)
                except ValueError:
                    pass
            if vals:
                summary[k] = {"min": min(vals), "mean": sum(vals)/len(vals), "max": max(vals), "samples": len(vals)}
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
