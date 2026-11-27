# Network quality

Run on the bench only. The tool measures network quality without changing configuration.

## 1. Basic tests

~~~bash
git pull --ff-only
./quality --self-test
sudo ./quality --mode cellular
~~~

NetBird: enter the remote peer IP, not this device's IP. Default rates are 5/10/20/50 Hz.

~~~bash
sudo ./quality --mode netbird --netbird PEER_IPV4
~~~

From a Linux laptop connected to the Hotspot, not the companion itself:

~~~bash
./quality --mode local --local 192.168.50.1
~~~

## 2. Advanced cellular tests

Deep mode tests two Internet targets, payload sizes 512/1200/1400 B and a 600 s soak. Short test first:

~~~bash
sudo ./quality --mode cellular --deep --duration 10 --soak-duration 30
sudo ./quality --mode cellular --deep
~~~

## 3. RF monitoring

Verify the AT port belongs to RM520N and is free; close minicom. Logs read-only QENG/QCSQ, LTE/NR bands, RSRP, RSRQ and SINR (LTE SINR raw).

~~~bash
sudo apt install -y python3-serial psmisc
sudo ./quality --mode cellular --deep --rf-port /dev/ttyUSB2 --rf-interval 5
~~~

## 4. TCP/UDP and loaded latency

Use only an authorized server reachable through ECM; restrict the test port. On the server:

~~~bash
sudo apt install -y iperf3
iperf3 -s
~~~

On the companion, replace SERVER_IPV4. Tests consume mobile data; default TCP pacing 10 Mbps, UDP 1/3/5 Mbps both directions.

~~~bash
sudo apt install -y iperf3
sudo ./quality --mode cellular --deep --iperf-server SERVER_IPV4 \
  --rf-port /dev/ttyUSB2 --tcp-mbps 10 --udp-mbps 1,3,5 --load-duration 30
~~~

## 5. Results

~~~bash
./quality --help
sudo ls -lt quality-results/
~~~

| Output | Content |
|---|---|
| summary.csv / summary.json | RTT, loss, P95/P99, mdev, burst loss |
| *-packets.csv / *-windows.csv | Per-packet and nominal 10 s windows |
| *.txt / *-meta.json | Raw ping and route snapshots |
| rf.csv / rf-raw.jsonl | RF samples (optional) |
| *.iperf.json / throughput-summary.json | Load test results (optional) |

Default reference: mean ≤100 ms, max ≤150 ms, mdev ≤20 ms, loss 0%. These are configurable engineering indicators, not flight qualification.

~~~bash
sudo ./quality --mode cellular --mean-limit 120 --max-limit 300 --mdev-limit 30 --loss-limit 1
~~~

COMPLETE means valid measurement, not good performance; INVALID must not be treated as zero loss. Exit 2 means skipped/invalid tests; exit 130 means interrupted. NetBird binding does not prove the underlying uplink; ICMP RTT is not one-way/video latency; TCP pacing is not maximum capacity. Redact private IP/cell data before sharing.

References: [iperf3](https://software.es.net/iperf/invoking.html) · [Quectel AT manual](https://www.quectel.com/content/uploads/2025/09/Quectel_RG520NRG525FRG5x0FRM5x0N_Series_AT_Commands_Manual_V1.1.pdf).
