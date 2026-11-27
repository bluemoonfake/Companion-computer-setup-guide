# 04 — ROS 2 Jazzy and Micro XRCE-DDS over Ethernet

Ubuntu 24.04 Noble, ROS 2 Jazzy, PX4 v1.17 reference. PX4's uXRCE-DDS client exchanges messages with the Agent; the Agent exposes ROS 2/DDS topics on the companion. MAVLink routing is independent and remains on UDP 14600. The earlier Pi 5 test used UDP 8888: the Agent reported session established from 192.168.0.3 and participant creation, and /fmu/in/* and /fmu/out/* were visible. The exact installed Agent version and px4_msgs commit were not recovered. The installation below follows the PX4 v1.17 and ROS Jazzy documentation rather than claiming to reproduce those exact versions.

## 1. Install ROS 2 Jazzy

For a new Ubuntu 24.04 installation, configure the ROS apt source using the maintained ros2-apt-source package. On an existing ROS installation, inspect existing apt source files first; do not add a conflicting legacy ros2.list/key configuration. See the official migration instructions when replacing an old source.

~~~bash
sudo apt update
sudo apt install -y locales software-properties-common curl ca-certificates jq
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
sudo add-apt-repository universe
~~~

For a clean machine without ros2-apt-source:

~~~bash
ROS_APT_SOURCE_VERSION=$(curl -fsSL \
  https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | jq -er .tag_name)
test -n "$ROS_APT_SOURCE_VERSION" &&
  curl -fL -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/$ROS_APT_SOURCE_VERSION/ros2-apt-source_$ROS_APT_SOURCE_VERSION.noble_all.deb" 
~~~

Use the correct asset name (the release tag and .noble_all.deb suffix). In Bash the variable followed by a period terminates normally. Confirm the download completed and the package is correct before installing:

~~~bash
dpkg-deb -I /tmp/ros2-apt-source.deb
sudo apt install /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools \
  python3-colcon-common-extensions python3-rosdep
source /opt/ros/jazzy/setup.bash
ros2 doctor --report
~~~

Use ros-jazzy-desktop only if graphical tools/RViz are needed. To initialize rosdep once (skip init if already initialized), run sudo rosdep init, then rosdep update as the normal user. Add source /opt/ros/jazzy/setup.bash to ~/.bashrc once, not every run.

## 2. Install Micro XRCE-DDS Agent (standalone)

For PX4 v1.17 use Agent v2.4.3 with Jazzy; do not substitute v3.x for a PX4 v2.x client. On an existing installation, check binary paths and service before replacing anything.

~~~bash
sudo apt install -y git build-essential cmake
mkdir -p ~/src
cd ~/src
git clone --branch v2.4.3 --depth 1 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git
cd Micro-XRCE-DDS-Agent
cmake -S . -B build
cmake --build build -j2
sudo cmake --install build
sudo ldconfig
command -v MicroXRCEAgent
~~~

Increase parallel build jobs only if RAM and cooling allow. Record source revision with git rev-parse HEAD. An alternative is to build the same tag in a Jazzy colcon workspace following the PX4 guide. Do not install both and accidentally run two Agents on 8888. A historical snap command was micro-xrce-dds-agent udp4 -p 8888; this guide standardizes on the standalone binary, not the moving snap channel.

## 3. Match px4_msgs to the flight controller

Read the PX4 version/commit (QGC or ver all on the FC). For stock PX4 v1.17 select release/1.17; if a custom firmware changes messages, use definitions from its exact source revision instead. Do not clone a random main branch for a release build.

~~~bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/px4_ros_ws/src
cd ~/px4_ros_ws/src
git clone --branch release/1.17 https://github.com/PX4/px4_msgs.git
cd ~/px4_ros_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select px4_msgs
source install/setup.bash
ros2 interface show px4_msgs/msg/VehicleOdometry
~~~

If the installed firmware is not v1.17, select its corresponding message branch or exact custom message definitions before building. Record both revisions. Do not mix conflicting overlays.

## 4. Configure PX4 DDS over Ethernet

After [02 — PX4 Ethernet](02_PX4_ETHERNET.md) works, use QGC Parameters (while disarmed):

| Parameter | Reference value |
|---|---|
| UXRCE_DDS_CFG | Ethernet |
| UXRCE_DDS_PRT | 8888 |
| UXRCE_DDS_AG_IP | 192.168.0.2 represented as signed int32 (-1062731774) |
| UXRCE_DDS_DOM_ID | 42 for the local-domain example (or 0 consistently on both ends) |
| UXRCE_DDS_PTCFG | Localhost for a companion-only DDS graph; verify enum in firmware |
| UXRCE_DDS_SYNCT | Enabled for normal real-hardware use |

Compute signed integer for any alternate IP on Ubuntu:

~~~bash
python3 -c 'import ipaddress; print(int.from_bytes(ipaddress.IPv4Address("192.168.0.2").packed, "big", signed=True))'
~~~

Use QGC enum labels rather than guessing numeric values. Domain 42 and LOCALHOST were recovered from a prior service configuration; this is a recommended companion-local profile, not proof the earlier Ethernet session used that domain. PX4 domain and ROS node domain must match. Restricting ROS discovery with ROS_AUTOMATIC_DISCOVERY_RANGE alone does not enforce the PX4 participant's visibility; configure UXRCE_DDS_PTCFG as well and validate. No public DDS exposure. Keep MAVLink Ethernet when both services are required.

Reboot PX4 and inspect uxrce_dds_client status in QGC MAVLink Console. If doing a temporary bench session, avoid starting another client over the same transport when one is already active.

## 5. First manual Agent test

Stop any existing Agent service temporarily before manual testing. Use the same domain and discovery environment in Agent and ROS terminals:

~~~bash
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
MicroXRCEAgent udp4 -p 8888 -v 4
~~~

In another terminal:

~~~bash
source /opt/ros/jazzy/setup.bash
source ~/px4_ros_ws/install/setup.bash
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 daemon stop
ros2 topic list -t
ros2 topic info /fmu/out/vehicle_odometry -v
ros2 topic echo /fmu/out/vehicle_odometry --qos-reliability best_effort --qos-durability volatile
~~~

Use actual topic names from the list (a namespace may prefix them). Expect session established, topic creation, then actual read-only data with changing timestamps. Topic discovery alone is not proof of data flow. QoS must match the PX4 publisher. Do not send flight-control commands merely to test connectivity.

## 6. Autostart with systemd

After manual test, stop the foreground Agent (Ctrl+C). Check for existing snap or serial agents, duplicate services, and paths:

~~~bash
command -v MicroXRCEAgent
sudo systemctl cat microxrce-agent.service
sudo ss -lunp | grep ':8888'
~~~

If the previous service was serial (historically /dev/ttyAMA0 at 921600, with a domain drop-in), inspect and back up the unit and drop-ins. Replace the serial service definition with an Ethernet-only unit, removing stale serial device dependencies and any overriding serial ExecStart. Use sudo systemctl edit --full microxrce-agent.service for an existing unit or create /etc/systemd/system/microxrce-agent.service on a fresh installation. Do not edit random vendor files. Example for standalone binary at /usr/local/bin/MicroXRCEAgent; replace ctuav with the existing normal service user and verify the actual binary path.

~~~ini
[Unit]
Description=PX4 Micro XRCE-DDS Agent (UDP)
After=network.target

[Service]
Type=simple
User=ctuav
Group=ctuav
Environment=ROS_DOMAIN_ID=42
Environment=ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ExecStart=/usr/local/bin/MicroXRCEAgent udp4 -p 8888 -v 4
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
~~~

If there are existing drop-ins, review them with systemctl cat. Retain matching domain/discovery settings, remove or edit conflicting ExecStart overrides and UART-only dependencies. Systemd does not support clearing all dependency types with empty drop-in assignments; edit the full unit when migrating from serial. The standalone Agent does not require sourcing a ROS overlay; your ROS nodes do. If running the workspace-built Agent, use its verified executable/environment instead.

~~~bash
sudo systemctl daemon-reload
sudo systemctl enable --now microxrce-agent.service
sudo systemctl status microxrce-agent.service --no-pager
sudo journalctl -u microxrce-agent.service -b -n 80 --no-pager
sudo ss -lunp | grep ':8888'
~~~

UDP Agent may listen on all interfaces; allow input from the dedicated FC network only under the existing firewall policy. ROS domain ID is not an authentication or encryption mechanism. Keep DDS local unless an explicitly secured design requires remote discovery.

## 7. Troubleshoot and verify reboot

~~~bash
ip route get 192.168.0.3
sudo tcpdump -ni eth0 'udp port 8888'
sudo systemctl show microxrce-agent -p ExecStart -p Environment
~~~

Use actual NIC. If there is no UDP traffic, check PX4 client/IP/port and carrier. If a session exists but topics do not, check Agent major version, participant/domain and message definitions. If topics exist but no samples, inspect QoS, namespace, publisher rate and timestamps. Reboot both devices on the bench and verify MAVLink and DDS simultaneously.

References: [ROS 2 Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html), [ROS apt source](https://github.com/ros-infrastructure/ros-apt-source), [PX4 v1.17 uXRCE-DDS](https://docs.px4.io/v1.17/en/middleware/uxrce_dds), [px4_msgs](https://github.com/PX4/px4_msgs), [Agent source](https://github.com/eProsima/Micro-XRCE-DDS-Agent).
