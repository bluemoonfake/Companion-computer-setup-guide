# RM520N-GL bench validation checklist

Scope: Orange Pi 6 / Ubuntu 24.04, RM520N-GL ECM, optional USB Wi-Fi and NetBird. Test on a bench with independent console access; do not test while airborne. All commands use the branch checkout.

## 1. Versions and offline checks

~~~bash
git rev-parse --short HEAD
./config --version
./quality --version
python3 -m py_compile config quality quality_advanced.py
./quality --self-test
sudo ./config --check
~~~

Record the kernel, board, modem firmware and USB driver. Offline tests cover ICMP parsing, duplicates, total loss, percentiles, adjacent RTT delta, burst loss, reference thresholds and LTE/NSA sample parsing. They do not validate real hardware or SA firmware layouts.

## Flight-controller link and middleware (before optional networking)

Use [02 PX4 Ethernet](02_PX4_ETHERNET.md), [03 MAVLink](03_MAVLINK.md), and [04 ROS 2/DDS](04_ROS2_DDS.md).

| Case | Expected observation |
|---|---|
| Dedicated wired NIC | 192.168.0.2/24 to PX4 192.168.0.3/24; no default route on FC NIC |
| MAVLink | PX4 UDP 14556 to companion 14600, bidirectional heartbeat/parameter read, GCS receives stream |
| DDS | UDP 8888 session established, topic discovery and changing read-only data with matching px4_msgs/domain/QoS |
| Concurrent operation | Both independent protocols remain functional without port collisions |
| Reboot | Static Ethernet profile, router and Agent return automatically; verify data, not only service status |

Historical Pi 5 session (2026-10-16): Ethernet ping 10/10, mean ~0.210 ms, bidirectional MAVLink and XRCE session/topic discovery were observed. Exact router and Agent package revisions, domain of that session, and current end-to-end reboot/continuous topic streaming are not established by the recovered evidence. The new written procedures must be bench-tested; do not claim they are a previously executed installer.

## 2. Configuration and watchdog

Use sudo ./config from the local console only if installing or updating the installed CLI. Verify sudo ctuav-net status and sudo ctuav-net logs.

| Case | Expected observation |
|---|---|
| 5G and USB Wi-Fi present | ECM connected, AP connected, AP IP 192.168.50.1/24, default route via ECM |
| Remove modem USB cable, leave adapter connected | Station selected after stable modem absence; saved infrastructure Wi-Fi connects |
| Reattach modem USB cable | ECM DHCP returns and AP selected after stable presence |
| Station unavailable | Fallback AP, no repeated Station retries until state change or service restart |
| Reboot with modem present | NetworkManager, modem and watchdog recover without manual activation |
| Reboot without modem | Station or fallback AP according to policy |
| Hotspot client | Client DHCP lease, gateway ping, Internet through cellular, mDNS and SSH if enabled |
| NetBird | Management/Signal connected; system SSH from a remote peer tested separately |

Watch events with sudo journalctl -fu ctuav-network.service. Use an independent console because disconnecting the modem or switching Wi-Fi can drop SSH. Remove only the USB connection, not antennas or SIM while powered. Do not treat an active systemd service as proof of connectivity.

## 3. Quality campaigns

Start short, then increase duration. Use remote endpoints that permit tests.

~~~bash
sudo ./quality --mode cellular --deep --duration 10 --soak-duration 30
sudo ./quality --mode cellular --deep
sudo ./quality --mode netbird --netbird PEER_IPV4
~~~

For RF monitoring install python3-serial and psmisc and specify the verified free port with --rf-port /dev/ttyUSB2. For load testing install iperf3 and specify an authorized server with --iperf-server SERVER_IPV4. Do not add a public server by default. See NETWORK_QUALITY.md for interpretation, output paths and parameters.

Record results in a local campaign folder, including summary.json, summary.csv, raw ping logs, RF data (if enabled), iperf results (if enabled), and relevant before/after routes and NetBird connection types. Keep private identifiers and raw location-related cell data out of the repository. Compare repeated runs under equivalent conditions.

## 4. Known evidence and outstanding tests

| Item | Status as of 2026-11-27 |
|---|---|
| ECM default route, direct Internet and NetBird management | Observed working on Orange Pi 6 |
| Installer v0.1.0 preflight, profile creation and watchdog installation | Observed |
| AP initially failed due to missing dnsmasq binary | Confirmed in NetworkManager log |
| Install dnsmasq-base and activate AP | Observed working, correct AP address and active/enabled watchdog |
| Quality v0.1.0 ECM gateway 300 packets at 5 Hz | Reported complete, 0% loss, mean 1.414 ms, P95 1.621 ms, P99 2.172 ms, max 9.850 ms, mdev 0.554 ms |
| Quality v0.1.0 direct Internet trial | Invalid; underlying raw ping not reviewed, cause not determined |
| Installer v0.1.1 dependency prompt on clean image | Pending |
| Installer-driven bidirectional switching, fallback and reboot | Pending for current installation |
| Quality v0.2.1 offline tests and on-device smoke test | Pending execution |
| RF correlation, controlled load and long-duration campaign | Pending |
| Raspberry Pi 5 with RM520N-GL | Not validated |

Previously observed manual configurations and benchmarks do not replace current installer/quality regression tests. The tool reports ICMP reference indicators and optional transport measurements, not airworthiness or flight-control qualification.
