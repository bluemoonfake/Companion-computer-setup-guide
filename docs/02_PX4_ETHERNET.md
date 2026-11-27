# 02 — PX4 Ethernet

Connect the Pixhawk using its supported Ethernet adapter. Disarm/remove propellers and keep the FC network separate from cellular and management links.

| Device | Address |
|---|---|
| PX4 | 192.168.0.3/24 |
| Companion | 192.168.0.2/24 |
| MAVLink PX4 → companion | UDP 14556 → 14600 |
| DDS Agent | UDP 8888 |

## 1. Companion static IP

Identify the dedicated NIC (eth0 on Pi 5, possibly enp* on Orange Pi). Check for subnet conflicts.

~~~bash
ip -br link
nmcli device status
nmcli connection show
~~~

Replace eth0 with the actual port; run locally. Create the profile only if it does not already exist.

~~~bash
IFACE=eth0
if ! nmcli connection show PX4_ETH >/dev/null 2>&1; then
  sudo nmcli connection add type ethernet ifname "$IFACE" con-name PX4_ETH
fi
sudo nmcli connection modify PX4_ETH \
  connection.interface-name "$IFACE" connection.autoconnect yes \
  ipv4.method manual ipv4.addresses 192.168.0.2/24 \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes ipv6.method disabled
sudo nmcli connection up PX4_ETH
~~~

Disable only competing profiles on this dedicated NIC. Keep auto-negotiation and the Internet default route on the uplink.

## 2. PX4 static IP

Export PX4 parameters and back up the existing SD-card network file. In QGC MAVLink Console over USB:

~~~text
cat /fs/microsd/net.cfg
ifconfig
~~~

For firmware supporting the SD-card net.cfg format, set the static IP. Check board-specific ROUTER/DNS requirements before applying.

~~~text
echo DEVICE=eth0 > /fs/microsd/net.cfg
echo BOOTPROTO=static >> /fs/microsd/net.cfg
echo IPADDR=192.168.0.3 >> /fs/microsd/net.cfg
echo NETMASK=255.255.255.0 >> /fs/microsd/net.cfg
cat /fs/microsd/net.cfg
~~~

Reboot PX4 and verify ifconfig. If the firmware uses a different network mechanism, follow its documentation instead.

## 3. Verify

~~~bash
ip -4 addr show "$IFACE"
sudo ethtool "$IFACE"
ping -I "$IFACE" -c 10 192.168.0.3
ip -4 route get 192.168.0.3
ip -4 route get 1.1.1.1
~~~

Expect a direct FC route and successful ping without changing the Internet route. See [PX4 Ethernet](https://docs.px4.io/main/en/advanced_config/ethernet_setup).
