# Bench validation

Disarm/remove propellers; use independent console access. Do not perform network switching or load tests during flight.

## 1. Software and services

~~~bash
git rev-parse --short HEAD
./config --version
./quality --version
python3 -m py_compile config quality quality_advanced.py
./quality --self-test
sudo ./config --check
~~~

## 2. Verify setup

| Check | Expected |
|---|---|
| PX4 Ethernet | Ping 192.168.0.3; no default route on FC NIC |
| MAVLink | UDP 14556 → 14600; GCS heartbeat and parameter read |
| DDS | UDP 8888; session and changing ROS 2 data |
| ECM | DHCP, Internet, metric 100 |
| Hotspot | Client DHCP, ping 192.168.50.1, SSH |
| Remove/replug modem USB | Station/AP transitions |
| Station unavailable | Fallback AP |
| NetBird | Peer reachable; remote SSH |
| Reboot | Required services and real data recover |

~~~bash
sudo ctuav-net status
sudo ctuav-net logs
sudo journalctl -b -u mavlink-router -u microxrce-agent --no-pager -n 80
~~~

## 3. Quality

~~~bash
sudo ./quality --mode cellular --deep --duration 10 --soak-duration 30
sudo ./quality --mode cellular --deep
~~~

Optional RF and throughput commands: [Network Quality](NETWORK_QUALITY.md).

## 4. Validation status

| Platform / test | Status |
|---|---|
| Raspberry Pi 5 Ethernet, MAVLink, DDS discovery | Earlier bench observations |
| Orange Pi 6 ECM, Hotspot after dnsmasq-base, watchdog active | Observed |
| Quality v0.2.0, seven ICMP tests (27 Nov 2026) | Complete; gateway within reference, six Internet tests outside |
| Quality v0.2.1 and full new OS installation | Pending regression |
| Current AP/STA/fallback/reboot sequence | Pending |
| RF analysis, throughput, loaded latency, video | Pending |
| Jetson and RM520N on Raspberry Pi 5 | Not validated |

Keep raw test results locally. Full historical procedures and results remain in Git history.
