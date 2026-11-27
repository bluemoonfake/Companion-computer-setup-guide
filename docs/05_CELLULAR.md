# 05 — Cellular module selection

Use the branch matching the physical modem. The SIM7600 variants are 4G LTE, not 5G NR.

| Modem | Network stack | Setup |
|---|---|---|
| RM520N-GL | 5G NR / ECM | [setup/RM520N-GL](https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/RM520N-GL) |
| SIM7600G-H | 4G LTE / QMI | [setup/sim7600g-h-qmi-hotspot](https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/sim7600g-h-qmi-hotspot) |
| SIM7600NA-H | 4G LTE / QMI | [setup/sim7600na-h-qmi-hotspot](https://github.com/bluemoonfake/Companion-computer-setup-guide/tree/setup/sim7600na-h-qmi-hotspot) |

From a full clone, switch to the correct branch (example RM520N-GL). Run from a local console.

~~~bash
git switch setup/RM520N-GL
sudo ./config --check
sudo ./config
~~~

Use only that branch's modem commands and recovery instructions. Do not run old GPIO reset/Hotspot services or mix QMI and ECM installers.
