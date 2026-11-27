# 04 — ROS 2 Jazzy and Micro XRCE-DDS

Reference: Ubuntu 24.04, PX4 v1.17, Agent v2.4.3, DDS domain 42. Match Agent/client versions and px4_msgs to the actual firmware.

## 1. ROS 2 Jazzy

Use the maintained ROS apt source on a clean image; do not add duplicate sources on an existing ROS installation.

~~~bash
sudo apt update
sudo apt install -y locales software-properties-common curl ca-certificates jq
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
sudo add-apt-repository universe
~~~

If ros2-apt-source is not installed:

~~~bash
ROS_APT_SOURCE_VERSION=$(curl -fsSL \
  https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | jq -er .tag_name)
test -n "$ROS_APT_SOURCE_VERSION" &&
  curl -fL -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/$ROS_APT_SOURCE_VERSION/ros2-apt-source_$ROS_APT_SOURCE_VERSION.noble_all.deb"
~~~

Verify the downloaded package, then install Jazzy Base and development tools.

~~~bash
dpkg-deb -I /tmp/ros2-apt-source.deb
sudo apt install /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools \
  python3-colcon-common-extensions python3-rosdep
grep -qxF 'source /opt/ros/jazzy/setup.bash' ~/.bashrc || \
  echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
source /opt/ros/jazzy/setup.bash
~~~

Initialize rosdep once (skip init if already initialized).

~~~bash
sudo rosdep init
rosdep update
~~~

## 2. Agent v2.4.3

Use the compatible v2.x Agent for the reference PX4 release; stop any old Agent before switching versions.

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

## 3. px4_msgs

For stock PX4 v1.17 use release/1.17; for custom firmware use its exact message definitions.

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

## 4. PX4 Ethernet DDS

After [Ethernet setup](02_PX4_ETHERNET.md), configure QGC parameters while disarmed. Use firmware enum labels.

| Parameter | Value |
|---|---|
| UXRCE_DDS_CFG | Ethernet |
| UXRCE_DDS_PRT | 8888 |
| UXRCE_DDS_AG_IP | -1062731774 (192.168.0.2) |
| UXRCE_DDS_DOM_ID | 42 |
| UXRCE_DDS_PTCFG | Localhost (companion-local graph) |
| UXRCE_DDS_SYNCT | Enabled |

For another Agent IPv4, compute its signed integer:

~~~bash
python3 -c 'import ipaddress; print(int.from_bytes(ipaddress.IPv4Address("192.168.0.2").packed, "big", signed=True))'
~~~

Reboot PX4 and check the client in QGC Console.

~~~text
uxrce_dds_client status
~~~

## 5. Manual test

Stop any existing Agent first; only one process may bind UDP 8888.

~~~bash
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
MicroXRCEAgent udp4 -p 8888 -v 4
~~~

Open another terminal with matching domain, discovery settings and message overlay.

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

Expect session establishment and actual changing data; match the actual topic namespace and QoS.

## 6. Autostart

Stop the manual Agent. Inspect/back up any existing unit and drop-ins; remove old serial-only dependencies and conflicting ExecStart overrides.

~~~bash
command -v MicroXRCEAgent
sudo systemctl cat microxrce-agent.service
sudo ss -lunp | grep ':8888'
sudoedit /etc/systemd/system/microxrce-agent.service
~~~

Replace YOUR_USERNAME with your existing non-root account and verify the binary path. The service uses that user's primary group by default.

~~~ini
[Unit]
Description=PX4 Micro XRCE-DDS Agent (UDP)
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
Environment=ROS_DOMAIN_ID=42
Environment=ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ExecStart=/usr/local/bin/MicroXRCEAgent udp4 -p 8888 -v 4
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
~~~

Enable and verify. Restrict UDP 8888 to the FC LAN; DDS domain/discovery settings are not authentication.

~~~bash
sudo systemctl daemon-reload
sudo systemctl enable --now microxrce-agent.service
sudo systemctl status microxrce-agent.service --no-pager
sudo journalctl -u microxrce-agent.service -b -n 80 --no-pager
sudo ss -lunp | grep ':8888'
sudo tcpdump -ni eth0 'udp port 8888'
~~~

Replace eth0 with the FC NIC. Verify both MAVLink and DDS again after reboot.

References: [ROS Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) · [PX4 uXRCE-DDS](https://docs.px4.io/v1.17/en/middleware/uxrce_dds) · [Agent](https://github.com/eProsima/Micro-XRCE-DDS-Agent) · [px4_msgs](https://github.com/PX4/px4_msgs).
