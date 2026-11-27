# Bench validation

Disarm/remove propellers and use independent console access.

| Check | Expected |
|---|---|
| PX4 Ethernet | Ping 192.168.0.3; no default route on FC NIC |
| MAVLink | UDP 14556 → 14600, GCS heartbeat and parameter read |
| DDS | UDP 8888, session and changing ROS 2 data |
| Optional cellular | Correct modem branch, Internet and automatic reconnect |
| Optional Hotspot | Client DHCP, local ping and SSH |
| Optional NetBird | Remote peer reachability and SSH |
| Reboot | Required services and actual data recover |

~~~bash
ip -4 route
systemctl status mavlink-router microxrce-agent --no-pager
sudo journalctl -b -u mavlink-router -u microxrce-agent --no-pager -n 80
~~~

Follow the selected modem branch's validation checklist for network installer and quality tests. Earlier Pi 5 Ethernet and Orange Pi 6 ECM results do not validate every board or new script. Jetson remains a reference platform.
