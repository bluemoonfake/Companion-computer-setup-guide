# 02 — Dedicated PX4 Ethernet

Use a wired flight-controller LAN separate from cellular, Wi-Fi hotspot, and NetBird. The reference addresses and UDP port pair reproduce the earlier Raspberry Pi 5 / PX4 bench setup. They are not mandatory for other deployments.

| Endpoint | IPv4 / port |
|---|---|
| Pixhawk Ethernet | 192.168.0.3/24 |
| Companion Ethernet | 192.168.0.2/24 |
| PX4 MAVLink local UDP | 14556 |
| Companion MAVLink listener | 14600 |
| Micro XRCE-DDS Agent | 192.168.0.2:8888 UDP |
| Optional GCS listener | UDP 14550 on ground station |
| Optional RM520N hotspot gateway | 192.168.50.1/24 |

Ensure these subnets do not overlap existing routes, LANs or camera interfaces. Keep the FC link isolated; do not bridge it into a public uplink. Use the flight-controller vendor's Ethernet adapter/pinout, not arbitrary RJ45 wiring; USB power or an appropriate independent power supply for the FC remains necessary. Disarm, remove propellers and use a bench setup.

## 1. Ubuntu Ethernet profile

Find the dedicated physical NIC; Pi 5 used eth0, Orange Pi 6 may use enp*.

~~~bash
ip -br link
nmcli device status
nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
~~~

Use the local console. Substitute the actual port. If PX4_ETH already exists, verify its type and interface, then modify instead of creating a duplicate. If Netplan generated a conflicting DHCP profile, fix its source configuration or disable only that competing profile; do not disable the cellular or management connection.

~~~bash
IFACE=eth0
sudo nmcli connection add type ethernet ifname "$IFACE" con-name PX4_ETH \
  ipv4.method manual ipv4.addresses 192.168.0.2/24 \
  ipv4.never-default yes ipv6.method disabled connection.autoconnect yes
sudo nmcli connection up PX4_ETH
~~~

For an existing dedicated profile:

~~~bash
sudo nmcli connection modify PX4_ETH \
  ipv4.method manual ipv4.addresses 192.168.0.2/24 \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv6.method disabled connection.autoconnect yes
sudo nmcli connection up PX4_ETH
~~~

Check and preserve the Internet default route on the management uplink.

~~~bash
ip -4 addr show "$IFACE"
ip -4 route
ip -4 route get 192.168.0.3
sudo ethtool "$IFACE"
~~~

Leave auto-negotiation enabled unless the actual FC hardware documentation requires otherwise. Do not reuse old camera-specific 10 Mbps settings.

## 2. PX4 network configuration

Check supported hardware/firmware and export the original PX4 parameters using QGroundControl. In QGC MAVLink Console over USB, inspect the current SD-card network file and interface:

~~~text
cat /fs/microsd/net.cfg
ifconfig
~~~

If using the PX4 documented SD-card network configuration, back up the old file first if present. Set a static address; for this isolated subnet the peer is not required as an Internet router. The sample below is a proposed reconstruction from PX4's documented format, not an exact recovered prior file. If the board requires ROUTER/DNS fields, use the board documentation and actual local routing configuration; do not invent an Internet gateway. On boards supporting netman, consult its own help and the firmware guide.

~~~text
echo DEVICE=eth0 > /fs/microsd/net.cfg
echo BOOTPROTO=static >> /fs/microsd/net.cfg
echo IPADDR=192.168.0.3 >> /fs/microsd/net.cfg
echo NETMASK=255.255.255.0 >> /fs/microsd/net.cfg
cat /fs/microsd/net.cfg
~~~

Reboot PX4 while disarmed, then check ifconfig again. If the firmware uses another network mechanism, do not overwrite its configuration blindly.

## 3. Verify before installing middleware

~~~bash
ping -I "$IFACE" -c 10 192.168.0.3
ip neigh show dev "$IFACE"
ip -4 route get 1.1.1.1
~~~

Historical Pi 5 bench result (2026-10-16, recovered from prior setup notes): 10/10 replies, 0% loss, mean RTT approximately 0.210 ms. The route and addresses were verified in that session. Repeat on the target board and after reboot. If ping fails, check carrier, netmask, static address and duplicate DHCP profiles; do not assume DDS or MAVLink is broken until basic connectivity works.

Continue with [03 — MAVLink](03_MAVLINK.md) and [04 — ROS 2/DDS](04_ROS2_DDS.md). They use different UDP ports on the same Ethernet link and do not forward each other's protocol.

Reference: [PX4 Ethernet setup](https://docs.px4.io/main/en/advanced_config/ethernet_setup).
