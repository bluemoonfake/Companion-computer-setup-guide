# 06 — Remote access, NetBird and service operations

For a board using RM520N-GL, install and verify [05 — RM520N-GL](05_RM520N_GL.md) first (or use another trusted uplink). NetBird is optional; direct Pixhawk Ethernet does not depend on it. Follow the official Linux installer for your deployment and review the installer before running it. Use the management URL/setup key supplied by your administrator; never add secrets or private peer addresses to the repository.

~~~bash
sudo systemctl enable --now netbird
sudo netbird status
sudo netbird status --detail
ip -4 route
~~~

Enroll using the deployment's official instructions. On the GCS, verify system SSH via the companion's current overlay IPv4, not the board's previous identity. NetBird SSH Server may be disabled while OpenSSH still works through the tunnel. Keep OpenSSH keys and network access policies enabled; do not open SSH to the Internet merely to troubleshoot the overlay.

Management/Signal connected and relay availability do not prove P2P connectivity or low latency. Inspect the actual peer (Direct/P2P or Relayed), test ping from the intended remote peer and confirm the companion's default route. If daemon startup fails with 209/STDOUT, see section 8 of the RM520N guide for the verified log-directory approach. Do not reset enrollment unnecessarily.

## Autostart and recovery

Install and enable only services required on that machine. These commands are diagnostic:

~~~bash
systemctl is-active NetworkManager ssh avahi-daemon
systemctl is-active netbird ctuav-network mavlink-router microxrce-agent
systemctl is-enabled netbird ctuav-network mavlink-router microxrce-agent
sudo journalctl -b -u ctuav-network -u netbird -u mavlink-router -u microxrce-agent --no-pager -n 100
sudo ss -lntup
~~~

Missing optional services are not automatically errors. Do not run legacy hotspot-autostart or 4G reset services alongside ctuav-network. Inspect installed service units before disabling obsolete services; these may be present only on older machines. Manage only the relevant service, not the entire networking stack, when troubleshooting.

For your own ROS application, create a separate service running as a normal user with explicit WorkingDirectory, ROS environment and verified absolute executable or wrapper that sources /opt/ros/jazzy/setup.bash and the correct workspace/install/setup.bash. Set Restart=on-failure only after validating application state and safety behavior. Do not copy an old machine-specific root autostart script or create broad passwordless sudo rules. Automatic application start is outside this base repository and must be validated per project.

Use [Network Quality](NETWORK_QUALITY.md) for RTT, RF and controlled load tests, and [Validation](VALIDATION.md) for complete bench checks. Remote cellular/VPN is suitable for supervised monitoring and development when validated; do not treat it as a primary flight-control link.

Reference: [NetBird Linux installation](https://docs.netbird.io/get-started/install/linux).
