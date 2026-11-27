# 06 — NetBird and remote access

Install NetBird using the [official Linux guide](https://docs.netbird.io/get-started/install/linux) for your deployment. Keep setup keys private and do not re-enroll a connected peer.

## 1. Connect

~~~bash
sudo systemctl enable --now netbird
~~~

For a new self-hosted client only, replace the management URL. The key may briefly appear in local process arguments.

~~~bash
read -rs -p 'NetBird setup key: ' NB_SETUP_KEY; echo
sudo netbird up --management-url https://netbird.example.com:443 --setup-key "$NB_SETUP_KEY"
unset NB_SETUP_KEY
~~~

Check management, signal, overlay IP and actual peer connection type.

~~~bash
netbird status
netbird status -d
ip -br -4 addr
ip -4 route
~~~

## 2. SSH

From an authorized remote host, replace NETBIRD_IP with the companion's current overlay IPv4. Use OpenSSH and restrict TCP 22 to trusted peers.

~~~bash
ping -c 10 NETBIRD_IP
ssh ctuav@NETBIRD_IP
~~~

## 3. Startup error 209/STDOUT

Inspect the unit/logs first. If the log-directory/output configuration causes startup failure, apply this drop-in from a local console (VPN disconnects).

~~~bash
systemctl cat netbird
sudo journalctl -u netbird -b -n 50 --no-pager
ls -ld /var/log/netbird
~~~

~~~bash
sudo mkdir -p /etc/systemd/system/netbird.service.d
sudo tee /etc/systemd/system/netbird.service.d/10-startup.conf >/dev/null <<'CONF'
[Service]
LogsDirectory=netbird
StandardOutput=journal
StandardError=journal
Restart=always
RestartSec=5s
CONF
sudo systemctl daemon-reload
sudo systemctl enable netbird
sudo systemctl restart netbird
netbird status
~~~

## 4. Service checks

Only installed/required services should be active. Verify actual data flow after reboot.

~~~bash
systemctl is-active NetworkManager ssh avahi-daemon
systemctl is-active netbird ctuav-network mavlink-router microxrce-agent
systemctl is-enabled netbird ctuav-network mavlink-router microxrce-agent
sudo journalctl -b -u ctuav-network -u netbird -u mavlink-router -u microxrce-agent --no-pager -n 100
sudo ss -lntup
~~~

Use a separate non-root service for ROS applications with the correct ROS/workspace environment. Do not expose DDS/MAVLink publicly or rely on cellular as primary flight control.
