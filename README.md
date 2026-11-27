# Companion Computer Setup — RM520N-GL

Interactive installer for Quectel RM520N-GL on Orange Pi 6 / Ubuntu 24.04 (ARM64). Other boards are not hardware-validated.

## Quick start

Run from a local console (or independent recovery link), not through the Wi-Fi adapter that will be switched.

~~~bash
git clone --branch setup/RM520N-GL --single-branch https://github.com/bluemoonfake/Companion-computer-setup-guide.git
cd Companion-computer-setup-guide
sudo ./config --check
sudo ./config
~~~

If Git is missing: sudo apt install git. For an existing checkout, switch to the branch and pull with --ff-only before running the installer. Do not overwrite local changes.

The setup wizard detects USB modem 2c7c:0801, CDC-ECM and USB Wi-Fi interfaces, checks NetworkManager/AP capability, and asks you to select cellular-only or cellular + Wi-Fi switching. It reuses the existing CTUAV_cc_5G and saved Station profile when possible. For a new Hotspot it asks for SSID (default CTUAV_cc_5G) and a WPA2 password; it does not publish credentials. Saved WPA2 credentials are passed to nmcli during profile creation and can briefly be visible to privileged/local processes; use a trusted local console.

If the ECM interface is missing, the wizard offers explicit AT configuration (select a verified AT port, provide APN, confirm modem reset). Existing ECM sessions are not reset. If ModemManager owns the modem, stop and resolve it manually using the detailed guide. The wizard does not change the kernel, install a Wi-Fi driver, change the network renderer, or enroll/reset NetBird automatically. For those optional/manual steps see the detailed guide.

## Hotspot dependency (v0.1.1)

Ubuntu images may omit dnsmasq-base. NetworkManager requires the dnsmasq binary to provide DHCP and DNS in IPv4 shared mode. The installer now checks this before changing Wi-Fi profiles and offers installation; cellular-only mode does not require this package. The read-only check warns if it is missing. The watchdog logs nmcli activation errors instead of silently discarding them.

For an existing v0.1.0 installation with AP activation failure and journal message "Could not find dnsmasq binary", run from the local console:

~~~bash
sudo systemctl stop ctuav-network.service
sudo apt update
sudo apt install -y dnsmasq-base
sudo systemctl restart ctuav-network.service
sudo ctuav-net status
~~~

To update the installed CLI and watchdog to v0.1.1, pull the branch and rerun the wizard, reusing existing profiles. No driver change is required to resolve this missing-package error.

## Diagnostics and operation

~~~bash
sudo ./config --check
sudo ctuav-net status
sudo ctuav-net logs
sudo ./config --version
~~~

The status command reports real device/profile states, routes and NetBird status if installed. A diagnostic warning is not a claim that hardware failed. Redact IPs/SSID/private information before sharing output.

| Modem USB | USB Wi-Fi | Policy |
|---|---|---|
| Present | Present | AP, shared IPv4 via cellular when available |
| Absent | Present | Station; if activation fails, sticky fallback AP |
| Present | Absent | 5G only |
| Absent | Absent | No change to other interfaces |

USB presence is checked every 2 seconds with 3 matching observations. This is not Internet/coverage failover. A Wi-Fi adapter replacement requires rerunning setup. STA/AP activation can interrupt existing SSH sessions.

The installer saves a root-only backup under /var/backups/ctuav-network before profile changes. It does not automatically restore modem NVRAM or roll back all network changes. On failure, inspect output and recover from the console:

~~~bash
sudo systemctl stop ctuav-network.service
nmcli connection show
# Substitute the saved Station UUID:
sudo nmcli con mod uuid UUID connection.autoconnect yes
sudo nmcli con up uuid UUID
~~~

To resume after reviewing configuration: sudo systemctl enable --now ctuav-network.service.

For manual setup, measured 5G results, NetBird, driver troubleshooting and recovery, see [RM520N-GL detailed setup](2nd_dougle_4g_setup.md). The other legacy documents are retained for reference; do not run the legacy hotspot or 4G reset scripts together with this watchdog.

## Validation

Version 0.1.1 is an initial installer implementation, not a hardware-qualified release. The earlier manual ECM/AP/STA configurations were tested on Orange Pi 6. The new executable, automatic AT path, fallback AP and end-to-end installation require on-device validation. Do not use it as a safety-critical control link.

CLI workflow inspired by [MAVLink Anywhere](https://github.com/alireza787b/mavlink-anywhere); this is an independent implementation, not a dependency on that project.
