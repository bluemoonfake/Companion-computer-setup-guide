# 03 — MAVLink Anywhere

Complete [PX4 Ethernet](02_PX4_ETHERNET.md) first. Use a free MAVLink instance and keep existing RC/GCS links unchanged.

## 1. PX4 parameters

Example instance 2; select enum labels in QGC and use a suitable MAV_2_RATE.

| Parameter | Value |
|---|---|
| MAV_2_CONFIG | Ethernet |
| MAV_2_UDP_PRT | 14556 |
| MAV_2_REMOTE_PRT | 14600 |
| MAV_2_BROADCAST | Enabled (isolated FC LAN) |
| MAV_2_MODE | Normal or Onboard, according to required streams |
| MAV_2_RADIO_CTL | Disabled |

Reboot PX4 and inspect the Ethernet instance in QGC MAVLink Console.

~~~text
mavlink status
ifconfig
~~~

## 2. Install

Review the upstream scripts before executing as root. Back up existing /etc/mavlink-router and use only one router service.

~~~bash
cd ~
git clone https://github.com/alireza787b/mavlink-anywhere.git
cd mavlink-anywhere
git rev-parse HEAD
less install_mavlink_router.sh
less configure_mavlink_router.sh
sudo ./install_mavlink_router.sh
sudo ./configure_mavlink_router.sh
~~~

Select UDP input, address 0.0.0.0 and port 14600. For a version supporting mla:

~~~bash
mla status
sudo mla input udp 0.0.0.0 14600
mla endpoint list
~~~

## 3. GCS forwarding

Replace GCS_IPV4 with the remote LAN/NetBird address; QGC listens on UDP 14550. Restrict ports to trusted interfaces, not the public Internet.

~~~bash
sudo mla endpoint add qgc GCS_IPV4 14550
mla endpoint list
~~~

Equivalent router endpoint reference (inspect the generated file; do not overwrite other endpoints):

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

## 4. Autostart and verify

~~~bash
sudo systemctl enable --now mavlink-router
systemctl status mavlink-router --no-pager
sudo ss -lunp | grep -E ':(14600|14550|14540)\b'
sudo journalctl -u mavlink-router -b -n 60 --no-pager
sudo tcpdump -ni eth0 'udp and (port 14556 or port 14600)'
~~~

Replace eth0 with the FC NIC; verify QGC heartbeat and read-only parameter response on the bench. Keep optional dashboard local-only.

Reference: [MAVLink Anywhere](https://github.com/alireza787b/mavlink-anywhere). If mla is unavailable, use the checkout's configure script and help.
