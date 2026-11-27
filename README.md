# Companion Computer Setup — Ubuntu 24.04 LTS

Ubuntu 24.04 companion computer setup for PX4: Ethernet, MAVLink Anywhere, ROS 2 Jazzy, Micro XRCE-DDS, optional 4G LTE and NetBird.

## Hardware examples

### Companion computers

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://orangepi.vn/shop/orange-pi-6-phien-ban-8gb-ram"><img src="https://orangepivn.b-cdn.net/wp-content/uploads/2026/07/orangepi6-3-247x296.webp" alt="Orange Pi 6 single-board computer" width="220"></a>
    </td>
    <td align="center" width="33%">
      <a href="https://geekworm.com/products/raspberry-pi-5-board"><img src="https://geekworm.com/cdn/shop/files/raspberrypi5-top_2048x2048.jpg?v=1705153559" alt="Raspberry Pi 5 single-board computer" width="220"></a>
    </td>
    <td align="center" width="33%">
      <a href="https://marketplace.nvidia.com/en-us/enterprise/robotics-edge/jetson-orin-nano-super-developer-kit/"><img src="https://marketplace.nvidia.com/assets/images/jetsonorin-nano-super-dev-kit-1920_1080h.jpg" alt="NVIDIA Jetson Orin Nano Super Developer Kit" width="220"></a>
    </td>
  </tr>
  <tr>
    <td align="center"><strong>Orange Pi 6</strong><br>ARM64 edge computing<br>RM520N-GL ECM bench-tested<br><a href="https://orangepi.vn/shop/orange-pi-6-phien-ban-8gb-ram">Photo / product</a></td>
    <td align="center"><strong>Raspberry Pi 5</strong><br>ARM64 companion computer<br>PX4 Ethernet bench-tested<br><a href="https://www.raspberrypi.com/products/raspberry-pi-5/">Official product</a> · <a href="https://geekworm.com/products/raspberry-pi-5-board">Photo</a></td>
    <td align="center"><strong>Jetson Orin Nano Super</strong><br>GPU-accelerated edge computing<br>Reference only; not validated<br><a href="https://marketplace.nvidia.com/en-us/enterprise/robotics-edge/jetson-orin-nano-super-developer-kit/">Photo / product</a></td>
  </tr>
</table>

Use the correct board image/BSP. Jetson requires compatible JetPack/L4T; it is a reference platform, not a validated target.

### 4G LTE modem

<p align="center"><a href="https://spotpear.com/index.php/index/product/detail/id/738.html"><img src="https://cdn.static.spotpear.com/uploads/picture/product/raspberry-pi/sim7600g-h-4g-hat-b/sim7600g-h-4g-hat-b-03.jpg" alt="SIM7600G-H 4G HAT" width="260"></a><br><strong>SIM7600G-H</strong> · LTE Cat 4 · USB QMI</p>

Use a compatible USB adapter, data SIM, power and antennas. [SIMCom product information](https://www.simcom.com/product/SIM7600X-H.html). Photo credits: linked suppliers.

## Setup

| Step | Guide |
|---|---|
| 01 | [Ubuntu 24.04](docs/01_UBUNTU_24_04.md) |
| 02 | [PX4 Ethernet](docs/02_PX4_ETHERNET.md) |
| 03 | [MAVLink Anywhere](docs/03_MAVLINK.md) |
| 04 | [ROS 2 Jazzy and DDS](docs/04_ROS2_DDS.md) |
| 05 | [SIM7600G-H 4G and Wi-Fi](docs/05_SIM7600.md) |
| 06 | [NetBird and remote access](docs/06_REMOTE_ACCESS.md) |
| 07 | [Network quality](docs/NETWORK_QUALITY.md) |
| 08 | [Validation checklist](docs/VALIDATION.md) |

~~~text
PX4 192.168.0.3/24
  | Ethernet
  | MAVLink UDP 14556 -> 14600
  | XRCE-DDS UDP -> 8888
Companion 192.168.0.2/24
  | MAVLink Anywhere -> GCS UDP 14550
  | Micro XRCE-DDS Agent -> ROS 2 Jazzy
  | Optional 4G / Wi-Fi / NetBird
~~~

## Quick start

Clone this branch on Ubuntu 24.04. The installer configures **4G QMI networking only**; follow steps 01–04 for PX4 middleware.

~~~bash
sudo apt install -y git
git clone -b setup/sim7600g-h-qmi-hotspot --single-branch https://github.com/bluemoonfake/Companion-computer-setup-guide.git
cd Companion-computer-setup-guide
sudo ./config --check
sudo ./config
~~~

Run from a local console; switching Wi-Fi can disconnect SSH. Select the GSM profile and optional auto-start Hotspot.

~~~bash
sudo ./config --status
sudo ./config --logs
~~~

## Quality test

Run on the bench, not during flight.

~~~bash
./quality --self-test
sudo ./quality --mode cellular --deep
~~~

For RF, NetBird and TCP/UDP load tests see [Network Quality](docs/NETWORK_QUALITY.md).

## Update

~~~bash
git pull --ff-only
./config --version
./quality --version
~~~

No installer rerun is needed for documentation or quality updates. No RM520N watchdog is installed on this QMI branch.

[Changelog](CHANGELOG.md) · [Validation status](docs/VALIDATION.md)
