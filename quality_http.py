"""Opt-in Cloudflare HTTP goodput and timestamped ICMP observations."""
import csv
import json
import math
import os
import re
import shutil
import signal
import socket
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from quality_advanced import route, route_key

HOST = "speed.cloudflare.com"
ENV = dict(os.environ, LC_ALL="C")
REPLY = re.compile(r"^\[([\d.]+)\].*icmp_seq=(\d+)\b.*\btime([=<])([\d.]+)\s*ms")
TOTAL = re.compile(r"(\d+) packets transmitted,\s*(\d+) (?:packets )?received")


def p95(values):
    x = sorted(values)
    if not x:
        return None
    i = (len(x)-1)*.95
    return x[math.floor(i)] + (x[math.ceil(i)]-x[math.floor(i)])*(i-math.floor(i))


def phase_stats(values):
    return {"samples": len(values), "mean_ms": statistics.mean(values) if values else None,
            "p95_ms": p95(values), "max_ms": max(values) if values else None}


def latency_stats(raw, start, end, hz):
    phases = {"idle": [], "http_request": [], "recovery": []}
    records = []
    seen = set()
    for line in raw.splitlines():
        m = REPLY.search(line)
        if not m:
            continue
        received, seq, bound, rtt = float(m[1]), int(m[2]), m[3], float(m[4])
        if seq in seen:
            continue
        seen.add(seq)
        sent = received-rtt/1000
        # Exclude replies crossing request boundaries. Upper-bound RTT is conservative.
        phase = ("idle" if received < start else
                 "http_request" if sent >= start and received <= end else
                 "recovery" if sent > end else "boundary")
        records.append((received, seq, rtt, bound == "<", phase))
        if phase in phases:
            phases[phase].append(rtt)
    totals = TOTAL.search(raw)
    tx, rx = (int(totals[1]), int(totals[2])) if totals else (None, None)
    valid = tx is not None and 0 <= rx <= tx and rx == len(seen)
    return {"status": "COMPLETE" if valid else "INVALID",
            "transmitted": tx, "received": rx,
            "overall_loss_pct": 100*(tx-rx)/tx if valid and tx else None,
            "rate_hz": hz, "phases": {k: phase_stats(v) for k,v in phases.items()}}, records


def resolve_cellular(iface):
    for ip in sorted({r[4][0] for r in socket.getaddrinfo(HOST, 443, socket.AF_INET, socket.SOCK_STREAM)}):
        if route(ip).get("dev") == iface:
            return ip
    raise RuntimeError("No Cloudflare IPv4 destination routed through selected cellular interface")


def validate_transfer(data, direction, size, ip, rc):
    errors = []
    if rc:
        errors.append("curl exit="+str(rc))
    status = data.get("response_code", data.get("http_code", 0))
    if not isinstance(status, (int, float)) or not 200 <= status < 300:
        errors.append("HTTP response not 2xx")
    if data.get("remote_ip") != ip:
        errors.append("unexpected remote IPv4")
    if data.get("size_"+direction) != size:
        errors.append("incomplete payload")
    speed = data.get("speed_"+direction)
    if not isinstance(speed, (int,float)) or not math.isfinite(speed) or speed <= 0:
        errors.append("invalid speed")
    return errors


def trial(a, out, iface, direction, n, upload):
    name = f"cloudflare-{direction}-{n}"
    ip = resolve_cellular(iface)
    before = route(ip)
    ping_before = route(a.internet)
    if ping_before.get("dev") != iface:
        raise RuntimeError("RTT target does not use selected cellular interface")
    size = (a.http_download_mb if direction == "download" else a.http_upload_mb)*1000000
    args = ["curl","-q","-4","--interface",iface,"--noproxy","*",
            "--resolve",f"{HOST}:443:{ip}","--proto","=https","--fail",
            "--connect-timeout","10","--max-time","120","-sS","-o","/dev/null",
            "-w","%{json}"]
    if direction == "download":
        args += [f"https://{HOST}/__down?bytes={size}"]
    else:
        args += ["--data-binary", "@"+str(upload), f"https://{HOST}/__up"]
    ping_args = ["ping","-4","-n","-D","-I",iface,"-i",str(1/a.baseline_rate),"-W","5",a.internet]
    print(f"[HTTP] {direction} {n}/{a.http_repeat}: {size/1000000:g} MB; 5 s idle and recovery", flush=True)
    with (out / (name+"-ping.txt")).open("w") as log:
        ping = subprocess.Popen(ping_args, env=ENV, stdout=log, stderr=subprocess.STDOUT)
        try:
            time.sleep(5)
            start = time.time()
            proc = subprocess.run(args, env=ENV, text=True, capture_output=True, timeout=130)
            end = time.time()
            time.sleep(5)
        finally:
            if ping.poll() is None:
                ping.send_signal(signal.SIGINT)
                try:
                    ping.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    ping.kill()
                    ping.wait()
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        data = {}
    (out / (name+"-curl.json")).write_text(proc.stdout)
    (out / (name+"-curl.stderr.txt")).write_text(proc.stderr)
    errors = validate_transfer(data, direction, size, ip, proc.returncode)
    after = route(ip)
    ping_after = route(a.internet)
    if route_key(before) != route_key(after) or route_key(ping_before) != route_key(ping_after):
        errors.append("route changed")
    latency, records = latency_stats((out / (name+"-ping.txt")).read_text(), start, end, a.baseline_rate)
    if ping.returncode not in (0,1) or latency["status"] != "COMPLETE":
        latency["status"] = "INVALID"
        errors.append("concurrent ICMP incomplete")
    with (out / (name+"-packets.csv")).open("w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["reply_epoch_s","icmp_seq","rtt_ms","upper_bound","phase"])
        w.writerows(records)
    row = {"label":name,"status":"INVALID" if errors else "COMPLETE",
           "error":"; ".join(errors),"direction":direction,"requested_bytes":size,
           "http_mbps":data["speed_"+direction]*8/1e6 if not errors else None,
           "http_start_epoch_s":start,"http_end_epoch_s":end,
           "request_seconds":end-start,"http_status":data.get("response_code"),
           "remote_ip":ip,"route_before":before,"route_after":after,
           "latency":latency}
    (out / (name+"-meta.json")).write_text(json.dumps(row,indent=2,allow_nan=False)+"\n")
    if errors:
        print("[INVALID] "+row["error"],flush=True)
    else:
        print(f"[COMPLETE] {direction}: {row['http_mbps']:.2f} Mbps | RTT request window: "
              f"{latency['phases']['http_request']}",flush=True)
    return row


def http_suite(a, out, iface):
    if not shutil.which("curl"):
        raise RuntimeError("Install curl first: sudo apt install curl")
    total = a.http_repeat*(a.http_download_mb+a.http_upload_mb)
    print(f"[INFO] Cloudflare HTTP payload budget: {total} MB plus protocol overhead",flush=True)
    rows = []
    # Private temporary file; incompressible payload; removed even on interruption.
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        upload = Path(tmp)/"payload.bin"
        upload.write_bytes(os.urandom(a.http_upload_mb*1000000))
        for n in range(1,a.http_repeat+1):
            for direction in ("download","upload"):
                rows.append(trial(a,out,iface,direction,n,upload))
                (out/"cloudflare-summary.json").write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")
    for direction in ("download","upload"):
        vals = [r["http_mbps"] for r in rows if r["direction"] == direction and r["status"] == "COMPLETE"]
        if vals:
            print(f"[HTTP SUMMARY] {direction}: median {statistics.median(vals):.2f} Mbps "
                  f"(valid {len(vals)}/{a.http_repeat})",flush=True)
    return rows
