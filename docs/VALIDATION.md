# Bench validation

Disarm/remove propellers and use local console access.

~~~bash
git rev-parse --short HEAD
./config --version
./quality --version
bash -n config
python3 -m py_compile quality quality_advanced.py
./quality --self-test
sudo ./config --check
~~~

| Check | Expected |
|---|---|
| PX4 Ethernet | Ping 192.168.0.3; no FC default route |
| MAVLink | UDP 14556 → 14600; GCS heartbeat and read-only parameter request |
| DDS | UDP 8888; session and changing ROS 2 data |
| QMI | ModemManager connected; LTE bearer and wwan interface |
| Hotspot | Client DHCP, 192.168.50.1 ping and SSH |
| NetBird | Peer reachable; remote SSH |
| Reboot | LTE/AP reconnect and required services recover |

~~~bash
sudo ./config --status
sudo ./config --logs
sudo ./quality --mode cellular --deep --duration 10 --soak-duration 30
~~~

Earlier SIM7600 QMI and Pi 5 Ethernet configurations were observed working. The new QMI wizard, adapted quality tool, RF sampling and complete installation are pending hardware regression. AP uses NetworkManager autoconnect (not the RM520N USB-presence watchdog). See [Network Quality](NETWORK_QUALITY.md).
