# 03 — MAVLink over Ethernet with MAVLink Anywhere

Prerequisite: [PX4 Ethernet](02_PX4_ETHERNET.md). The historical Pi 5 link used PX4 192.168.0.3:14556 and companion 192.168.0.2:14600; bidirectional MAVLink and forwarding to GCS UDP 14550 were observed. The exact historical router configuration and upstream package revision were not recovered; the following is a documented reconstruction using current MAVLink Anywhere commands.

## 1. Configure PX4

In QGroundControl Parameters, select a free MAVLink instance (example instance 2); keep independent RC/GCS serial links untouched. Check actual firmware enum labels. Example Ethernet setup:

| Parameter | Reference value |
|---|---|
| MAV_2_CONFIG | Ethernet (1000) |
| MAV_2_UDP_PRT | 14556 |
| MAV_2_REMOTE_PRT | 14600 |
| MAV_2_BROADCAST | Enabled (1) on the isolated FC link |
| MAV_2_MODE | Normal (0) for GCS telemetry or Onboard (2) when required |
| MAV_2_RADIO_CTL | Disabled (0) for Ethernet |

The port pair is recovered from prior testing; instance number, mode and throttling are example choices, not recovered exact parameters. Set a suitable MAV_2_RATE for required streams; inspect actual message rates rather than maximizing traffic indiscriminately. Reboot PX4 and verify in QGC MAVLink Console:

~~~text
mavlink status
ifconfig
~~~

Check the Ethernet instance, local port, remote port and traffic counters. Ensure UDP 14600 is not occupied by a second router.

## 2. Install MAVLink Anywhere (upstream)

~~~bash
cd ~
git clone https://github.com/alireza787b/mavlink-anywhere.git
cd mavlink-anywhere
git rev-parse HEAD
less install_mavlink_router.sh
less configure_mavlink_router.sh
sudo ./install_mavlink_router.sh
sudo ./configure_mavlink_router.sh --help
~~~

Review upstream scripts before running with sudo. The installer builds/installs mavlink-routerd and may install dependencies. Keep one router service. If there is an existing configuration, back up /etc/mavlink-router and inspect /etc/default/mavlink-router before changing input or routes. Do not run a second mavlink-router instance on the same ports.

Choose UDP input in the interactive configuration; bind 0.0.0.0:14600 for the isolated-link broadcast setup. Alternatively, if the checkout supports the documented headless arguments:

~~~bash
sudo ./configure_mavlink_router.sh --headless \
  --input-type udp --input-address 0.0.0.0 --input-port 14600 \
  --endpoints "127.0.0.1:14540" --skip-dashboard
~~~

This is an initial configuration example, not an update command for a production route set. Local MAVSDK output 14540 is optional. For existing installations with the mla CLI (upstream README currently documents it), use:

~~~bash
mla help
mla status
sudo mla input udp 0.0.0.0 14600
mla endpoint list
~~~

If your pinned upstream version does not provide mla, use its documented configure script and service helper instead. Record the installed revision; do not assume all versions have identical CLI flags.

## 3. Ground station / NetBird output

Get the remote GCS's actual address on a trusted LAN or NetBird overlay. On the Pi, add an explicit route (replace GCS_IPV4 with the real remote IPv4). Do not commit fleet addresses or use the Pi's own NetBird address as the destination.

~~~bash
sudo mla endpoint add qgc GCS_IPV4 14550
mla endpoint list
sudo systemctl status mavlink-router --no-pager
~~~

In QGC enable a UDP communication link listening on 14550. Avoid sending the same vehicle stream to the same GCS twice. The optional local router GCS listener on 14550 is different from the explicit remote endpoint; do not confuse local and remote ports.

A direct configuration equivalent for inspection (not a replacement of the upstream-generated file):

~~~ini
[UdpEndpoint px4_eth]
Mode = Server
Address = 0.0.0.0
Port = 14600

[UdpEndpoint gcs]
Mode = Normal
Address = GCS_IPV4
Port = 14550
~~~

Review the actual main.conf and effective service settings; use upstream validation and backups when editing. Restrict incoming MAVLink to the trusted FC/management interfaces using existing firewall policy. Do not expose the unauthenticated MAVLink socket to the public Internet. Keep the optional web dashboard loopback-only; SSH tunnel if needed.

## 4. Verify and troubleshoot

~~~bash
sudo ss -lunp | grep -E ':(14600|14550|14540)\b'
sudo journalctl -u mavlink-router -b -n 60 --no-pager
sudo tcpdump -ni eth0 'udp and (port 14556 or port 14600)'
~~~

Substitute the actual FC interface for eth0. Verify FC outbound packets 14556 to destination 14600 and router return traffic on the FC link; verify GCS heartbeat reception and a read-only parameter request/response on the bench. Do not test arming or motion. If using NetBird, verify overlay reachability and peer connection type independently; avoid relying on the cellular link as primary flight control.

~~~bash
sudo systemctl enable mavlink-router
systemctl is-enabled mavlink-router
systemctl is-active mavlink-router
~~~

After reboot verify the local FC link and GCS independently. If no packets arrive, check the PX4 instance/port pair, firewall and NIC; if packets arrive without vehicle discovery, inspect routing endpoints and QGC UDP listener.

Optional UART alternative: select the real serial device, confirm voltage and TX/RX/GND wiring, disable any serial console for that specific UART only, use the same baud rate in PX4 and router, and give the service account dialout access. Do not use the same UART for DDS and MAVLink. On Pi 5 device names depend on overlays; do not assume ttyAMA0 or ttyAMA10 without inspection.

References: [MAVLink Anywhere](https://github.com/alireza787b/mavlink-anywhere), [upstream CLI reference](https://github.com/alireza787b/mavlink-anywhere/blob/main/docs/CLI-REFERENCE.md), [PX4 Ethernet setup](https://docs.px4.io/main/en/advanced_config/ethernet_setup).
