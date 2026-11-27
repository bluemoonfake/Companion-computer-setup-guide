# Companion Computer Setup — Ubuntu 24.04 LTS

Ubuntu 24.04 companion computer setup for PX4: Ethernet, MAVLink Anywhere, ROS 2 Jazzy, Micro XRCE-DDS, optional 4G/5G and NetBird.

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

### Cellular modules

<table>
  <tr>
    <td align="center" width="33%"><a href="https://www.waveshare.com/product/rm520n-gl-5g-hat-with-case.htm"><img src="https://www.waveshare.com/media/catalog/product/cache/1/image/800x800/9df78eab33525d08d6e5fb8d27136e95/r/m/rm520n-gl-5g-hat-with-case-4.jpg" alt="RM520N-GL USB adapter or HAT" width="220"></a></td>
    <td align="center" width="33%"><a href="https://spotpear.com/index.php/index/product/detail/id/738.html"><img src="https://cdn.static.spotpear.com/uploads/picture/product/raspberry-pi/sim7600g-h-4g-hat-b/sim7600g-h-4g-hat-b-03.jpg" alt="SIM7600G-H USB adapter or HAT" width="220"></a></td>
    <td align="center" width="33%"><a href="https://uk.robotshop.com/products/waveshare-sim7600na-h-4g-hat-raspberry-pi-lte-cat-4-4g-support-na"><img src="https://uk.robotshop.com/cdn/shop/files/waveshare-sim7600na-h-4g-hat-for-raspberry-pi-lte-cat-4-4g-img1_1200x1200.webp?v=1749453689" alt="SIM7600NA-H USB adapter or HAT" width="220"></a></td>
  </tr>
  <tr>
    <td align="center"><strong>RM520N-GL</strong><br>5G NR / ECM<br><a href="https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/RM520N-GL">Setup branch</a></td>
    <td align="center"><strong>SIM7600G-H</strong><br>4G LTE / QMI<br><a href="https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/sim7600g-h-qmi-hotspot">Setup branch</a></td>
    <td align="center"><strong>SIM7600NA-H</strong><br>4G LTE / QMI<br><a href="https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/sim7600na-h-qmi-hotspot">Setup branch</a></td>
  </tr>
</table>

Photo credits: Orange Pi Vietnam, Geekworm, NVIDIA, Waveshare, Spotpear and RobotShop (linked originals). Use the correct USB adapter, SIM, power and antennas.

## System architecture

```mermaid
flowchart TB
    FC["Pixhawk / PX4<br/>192.168.0.3"]

    subgraph CC["Companion computer · Ubuntu 24.04 · 192.168.0.2"]
        MAV["MAVLink Anywhere<br/>mavlink-router"]
        DDS["Micro XRCE-DDS Agent"]
        ROS["ROS 2 Jazzy"]
        VPN["NetBird · wt0"]
        WIFI["Wi-Fi / Hotspot"]
        DDS <--> ROS
        MAV <-->|UDP 14550| VPN
        MAV <-.->|Optional UDP 14550| WIFI
    end

    FC <-->|Ethernet · MAVLink<br/>14556 → 14600| MAV
    FC <-->|Ethernet · DDS<br/>UDP 8888| DDS
    VPN <-->|USB · QMI / ECM| MODEM["4G / 5G modem"]
    MODEM <--> WAN["Carrier / Internet"]
    WAN <-->|NetBird tunnel| REMOTE["Remote GCS<br/>NetBird peer"]
    WIFI <-.-> LOCAL["Local GCS / SSH client"]

    classDef default stroke-width:1px,font-size:12px;
    style CC stroke-width:1px,stroke-dasharray:4 3
    linkStyle default stroke-width:1px
```

MAVLink and XRCE-DDS share one dedicated Ethernet link but use separate UDP ports. Remote GCS traffic follows the optional cellular/NetBird path; local GCS requires a configured router endpoint.

Select the modem branch for its USB mode and Wi-Fi policy.

## Setup

| Step | Guide |
|---|---|
| 01 | [Ubuntu 24.04](docs/01_UBUNTU_24_04.md) |
| 02 | [PX4 Ethernet](docs/02_PX4_ETHERNET.md) |
| 03 | [MAVLink Anywhere](docs/03_MAVLINK.md) |
| 04 | [ROS 2 Jazzy and DDS](docs/04_ROS2_DDS.md) |
| 05 | [Choose cellular module](docs/05_CELLULAR.md) |
| 06 | [NetBird and remote access](docs/06_REMOTE_ACCESS.md) |
| 07 | [Network quality](docs/NETWORK_QUALITY.md) |
| 08 | [Validation checklist](docs/VALIDATION.md) |

## Quick start

Choose the branch for your modem; all share steps 01–04 and 06. Without cellular, use main and follow the common guides.

| Module | Branch | Mode |
|---|---|---|
| RM520N-GL | [setup/RM520N-GL](https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/RM520N-GL) | 5G NR / ECM |
| SIM7600G-H | [setup/sim7600g-h-qmi-hotspot](https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/sim7600g-h-qmi-hotspot) | 4G LTE / QMI |
| SIM7600NA-H | [setup/sim7600na-h-qmi-hotspot](https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/sim7600na-h-qmi-hotspot) | 4G LTE / QMI |

~~~bash
sudo apt install -y git
git clone https://github.com/bluemoonfake/Companion-computer-setup-guide.git
cd Companion-computer-setup-guide
~~~

For cellular setup, switch to the correct branch (example RM520N-GL). Use local console access.

~~~bash
git switch setup/RM520N-GL
sudo ./config --check
sudo ./config
~~~

The installer is modem-specific, not a full OS installer. The SIM7600 branches use ModemManager/QMI, not the RM520N ECM watchdog.

## Quality test (modem branch)

~~~bash
./quality --self-test
sudo ./quality --mode cellular --deep
~~~

Run on the bench only. For optional RF and load testing, follow the selected branch's Network Quality guide.

~~~bash
git pull --ff-only
~~~

[Changelog](CHANGELOG.md) · [Validation](docs/VALIDATION.md)
