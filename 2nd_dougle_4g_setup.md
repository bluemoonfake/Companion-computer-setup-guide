# RM520N-GL — Ubuntu 24.04 + 5G (ECM) + NetBird

> **Scope:** Quectel RM520N-GL over USB 3.0 using CDC-ECM on Ubuntu 24.04 LTS. The modem establishes the cellular data session; NetworkManager obtains an Ethernet address through DHCP.
>
> **Verified platform:** Orange Pi 6 (ARM64), Ubuntu 24.04, Linux `6.6.89-cix`, modem firmware `RM520NGLAAR03A03M4G`. Cellular-only boot, modem USB reconnection and remote SSH through NetBird were verified on this platform. Raspberry Pi 5 was not tested with this modem in this session.
>
> **Important:** This guide uses ECM, not QMI, MBIM or PPP. No separate WireGuard service or custom kernel is required. USB Wi-Fi is optional; see section 12 for automatic Hotspot/Station switching. Perform network changes from a local console or an independent management connection.

## Interactive installer (recommended)

Run from the local console: clone this branch, then run `sudo ./config --check` and `sudo ./config`. See [README](README.md) for the wizard, status and recovery. The script reuses working ECM and Station profiles, creates the missing Hotspot and installs the automatic switching service. The manual sections below remain useful for troubleshooting; do not install both watchdog implementations at once.

## 0. Requirements and hardware connection

- Ubuntu 24.04 with `sudo` access and temporary Internet access for package installation.
- RM520N-GL with a compatible USB-to-M.2 adapter, suitable power supply and cellular antennas connected according to the adapter/module documentation.
- Active data SIM and the correct APN supplied by the mobile operator.
- USB 3.0 data cable (not a charge-only cable).
- Optional: a NetBird account or an existing self-hosted NetBird deployment for remote access.

Power off before installing the SIM or changing antenna connections. Do not publish SIM identifiers, setup keys, credentials or private VPN addresses.

## 1. Install tools and identify the modem

~~~bash
sudo apt update
sudo apt install -y network-manager minicom usbutils curl iputils-ping openssh-server
sudo systemctl enable --now NetworkManager ssh

lsusb
lsusb -t
ls -l /dev/ttyUSB*
nmcli device status
ip -br link
~~~

Expected USB ID: `2c7c:0801`. On the verified system, the module enumerated at `5000M` with the `cdc_ether` driver in ECM mode. Serial AT ports were provided by the USB serial driver.

If Ubuntu uses another network renderer, configure NetworkManager for the modem first. On the tested Orange Pi image, Netplan already used NetworkManager. Do not replace an existing Netplan configuration blindly.

## 2. Verify SIM and modem configuration via AT commands

On the dedicated ECM system, ModemManager is not required. If it is installed and occupies the AT port, stop it before opening minicom. Only disable and mask it if no other modem depends on it:

~~~bash
# Dedicated ECM-only device; optional if ModemManager is installed.
sudo systemctl disable --now ModemManager.service
sudo systemctl mask ModemManager.service
~~~

Open the AT port (usually `/dev/ttyUSB2`; verify if port numbering changes):

~~~bash
sudo minicom -D /dev/ttyUSB2 -b 115200
~~~

Enter these commands **inside minicom**, not in the Linux shell:

~~~text
AT
ATI
AT+CPIN?
AT+CFUN?
AT+CEREG?
AT+COPS?
AT+CGATT?
AT+CGDCONT?
AT+QCFG="usbnet"
AT+QCFG="data_interface"
AT+QNWPREFCFG="mode_pref"
AT+QNWPREFCFG="nr5g_disable_mode"
AT+QMAPWAC?
AT+QENG="servingcell"
AT+QNWINFO
~~~

`AT` should return `OK`; `AT+CPIN?` should return `READY`. LTE registration (`CEREG` status 1 or 5) and a registered NR serving cell indicate cellular registration. Registration alone does not prove Internet connectivity.

## 3. Configure ECM and automatic cellular connection

Use the following configuration on the dedicated USB-connected RM520N-GL. Replace `YOUR_APN` with the actual data APN. Use the PDP type required by the operator; `IPV4V6` was used in the verified setup.

~~~text
AT+QCFG="usbnet",1
AT+QCFG="data_interface",0,0
AT+CGDCONT=1,"IPV4V6","YOUR_APN"
AT+QNWPREFCFG="mode_pref",AUTO
AT+COPS=0
AT+QMAPWAC=1
AT+CFUN=1
~~~

- `usbnet=1`: CDC-ECM mode.
- `data_interface=0,0`: USB data interface configuration used on the tested adapter.
- `CGDCONT`: APN/PDP context 1.
- `mode_pref=AUTO`: automatic radio access selection, without forcing a band or 5G SA.
- `COPS=0`: automatic operator selection.
- `QMAPWAC=1`: modem-side automatic data connection.
- `CFUN=1`: full modem functionality.

Check the response to every command. If the firmware rejects any command, stop and check the applicable Quectel documentation instead of assuming the setting was applied. If NR has previously been disabled, inspect `AT+QNWPREFCFG="nr5g_disable_mode"` and, when supported, restore `AT+QNWPREFCFG="nr5g_disable_mode",0`. The verified modem reported `0`.

Restart the modem to apply USB interface changes:

~~~text
AT+CFUN=1,1
~~~

The AT port may disappear during reset. Exit minicom (Ctrl+A, then X) and allow the USB device to re-enumerate. Reopen the actual AT port and query the settings again. A reset may interrupt all cellular traffic.

~~~bash
lsusb -d 2c7c:0801
lsusb -t
nmcli device status
ip -br link
~~~

Expected: a managed Ethernet device such as `enx...`, using `cdc_ether`. Its name and MAC address can change after reboot/reconnection; do not bind the profile to a fixed interface name or MAC.

## 4. Create a persistent NetworkManager Ethernet profile

Check existing profiles before creating a new one:

~~~bash
nmcli connection show
nmcli device status
~~~

Use the verified connection name `CTUAV_cc_5G`. Create it **only if it does not exist**:

~~~bash
if ! nmcli connection show CTUAV_cc_5G >/dev/null 2>&1; then
  sudo nmcli connection add type ethernet ifname '*' con-name CTUAV_cc_5G
fi

sudo nmcli connection modify CTUAV_cc_5G \
  connection.interface-name '' \
  802-3-ethernet.mac-address '' \
  match.driver cdc_ether \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  connection.autoconnect-retries 0 \
  ipv4.method auto \
  ipv4.route-metric 100 \
  ipv6.method auto \
  ipv6.route-metric 100
~~~

The profile matches the ECM driver, not a randomly generated MAC or `enx...` name. Priority 100 selects this profile ahead of competing profiles for the same interface; route metric 100 prefers the cellular default route over higher-metric alternatives. Autoconnect retries `0` means retry indefinitely.

If more than one `cdc_ether` device exists, this match is not unique. Identify the intended modem and use an appropriate additional persistent match before enabling automatic activation. This guide was tested with one ECM modem.

If NetworkManager created another profile for the same modem, disable autoconnect on that **specific** profile after identifying it. Do not disable unrelated Ethernet or Wi-Fi profiles.

~~~bash
# Replace with the competing profile name only if one exists.
# sudo nmcli connection modify 'Wired connection 3' connection.autoconnect no
sudo nmcli -w 60 connection up CTUAV_cc_5G

nmcli -f connection,match,802-3-ethernet,ipv4,ipv6 connection show CTUAV_cc_5G
nmcli device status
ip -br -4 addr
ip -4 route
ip route get 1.1.1.1
~~~

Observed: an ECM DHCP address in `192.168.224.0/22`, gateway `192.168.225.1`, and default route metric 100. These are observed values, not addresses to configure statically.

## 5. Verify Internet and automatic reconnection

Disconnect alternative uplinks for this test only if local console access is available. Confirm the route to the Internet uses the ECM device.

~~~bash
ip route get 1.1.1.1
ping -q -c 50 -i 0.2 192.168.225.1  # use the actual ECM gateway
ping -q -c 50 -i 0.2 1.1.1.1
curl --max-time 15 -I https://example.com
~~~

Reboot the host and verify without manually activating the connection:

~~~bash
sudo reboot
~~~

After boot:

~~~bash
systemctl is-enabled NetworkManager
nmcli device status
ip -4 route
ping -q -c 10 1.1.1.1
~~~

With local access, unplug/reconnect the modem USB adapter and repeat the checks. The verified profile recovered even when the Ethernet interface name and DHCP address changed. No manual `nmcli connection up` was required on the observed reconnects/reboots.

## 6. Verify 5G radio parameters

~~~bash
sudo minicom -D /dev/ttyUSB2 -b 115200
~~~

~~~text
AT+QENG="servingcell"
AT+QNWINFO
AT+QCSQ
AT+CSQ
AT+CGPADDR
AT+QNWPREFCFG="mode_pref"
AT+QNWPREFCFG="nr5g_disable_mode"
~~~

Observed example (26 November 2026):

| Parameter | LTE anchor | NR secondary |
|---|---:|---:|
| Mode | FDD LTE | 5G NSA / TDD |
| Band | B3 | n41 |
| RSRP | -63 dBm | -63 dBm |
| RSRQ | -11 dB | -10 dB |
| SINR | 9 (raw reported value) | 27 dB |
| Channel | 1700 | 502110 |

`AT+CSQ` returned `31,99`. The modem reported a valid IPv4/IPv6 PDP context and `mode_pref=AUTO`. Strong signal does not guarantee low latency, low network load or 5G SA. Actual bands and addresses depend on coverage and subscription. Do not lock bands just to reproduce these results.

## 7. Set up NetBird for headless remote access (optional)

Install the CLI using the [official Linux installation guide](https://docs.netbird.io/get-started/install/linux). Use the installation commands for your existing NetBird deployment. Then:

~~~bash
sudo systemctl enable --now netbird
~~~

For a new client, register once with your approved NetBird deployment. Example for a self-hosted deployment:

~~~bash
# Replace the URL with your deployment's management URL.
# Enter the setup key privately; do not commit it or paste it into logs.
read -rs -p 'NetBird setup key: ' NB_SETUP_KEY; echo
sudo netbird up --management-url https://netbird.example.com:443 --setup-key "$NB_SETUP_KEY"
unset NB_SETUP_KEY
~~~

The example keeps the key out of shell history, but command-line arguments may be briefly visible to privileged/local processes. Follow your organization's enrollment policy. Do not re-enroll an already connected client.

~~~bash
netbird status
netbird status -d
ip -br -4 addr
~~~

Verify that Management and Signal are connected and `wt0` has its assigned VPN address. Allow TCP 22 from authorized peers in the host firewall and NetBird access policy as appropriate. Use OpenSSH, not the optional NetBird SSH server.

From an authorized remote machine:

~~~bash
ping -c 10 <NETBIRD_IP>
ssh <LINUX_USER>@<NETBIRD_IP>
~~~

Replace the placeholders before running. No separate `wg0` tunnel is needed. The tested Orange Pi used NetBird's Userspace interface; no kernel modification was necessary.

## 8. Fix NetBird startup error 209/STDOUT

Observed failure after reboot:

~~~text
status=209/STDOUT
/var/run/netbird.sock: no such file or directory
~~~

The original service sent stdout/stderr to files under `/var/log/netbird`. A missing or inaccessible log path can prevent systemd from launching the daemon. Inspect the unit and logs before changing anything:

~~~bash
systemctl cat netbird
sudo journalctl -u netbird -b -n 50 --no-pager
ls -ld /var/log/netbird
~~~

Recommended persistent equivalent of the tested service changes: use a systemd drop-in rather than editing the vendor unit directly. Execute from local console; restarting NetBird disconnects VPN SSH.

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

systemctl show netbird -p LogsDirectory -p StandardOutput -p StandardError -p Restart -p RestartUSec
systemctl is-active netbird
netbird status
~~~

Expected: `LogsDirectory=netbird`, both outputs `journal`, `Restart=always`, `RestartUSec=5s`. The client can also maintain its own `/var/log/netbird/client.log`.

Reboot and verify remote SSH without running `netbird up` again. On the tested machine, boot and SSH succeeded after the output/restart changes. `LogsDirectory=netbird` was subsequently confirmed in the loaded service configuration; a separate reboot with that final setting was not captured. The drop-in is the recommended packaging of those settings, not a separately tested installation. A 5-second restart delay does not guarantee network recovery within 5 seconds.

## 9. Benchmark NetBird over 5G

On the remote Linux client, set `PEER` to the modem host's actual NetBird address:

~~~bash
PEER='REPLACE_WITH_NETBIRD_IP'
for spec in '300 0.2' '600 0.1' '1200 0.05' '3000 0.02'; do
  read -r count interval <<< "$spec"
  date -Is
  ping -q -c "$count" -i "$interval" "$PEER"
done | tee netbird_5g_test.log
~~~

On the cellular host, measure Internet connectivity separately:

~~~bash
ping -D -c 1200 -i 0.2 1.1.1.1 | tee internet_5g_test.log
netbird status -d
~~~

Observed NetBird results (26 November 2026; client v0.83.2 on Orange Pi, v0.80.0 on remote Linux host):

| Target send rate | Sent/received | Min RTT (ms) | Avg RTT (ms) | Max RTT (ms) | mdev (ms) | Loss |
|---|---:|---:|---:|---:|---:|---:|
| 5 Hz | 300/300 | 73.804 | 95.838 | 232.573 | 18.062 | 0% |
| 10 Hz | 600/600 | 71.408 | 114.253 | 500.964 | 62.249 | 0% |
| 20 Hz | 1200/1200 | 71.433 | 182.558 | 1396.326 | 178.383 | 0% |
| 50 Hz | 3000/3000 | 67.402 | 89.124 | 264.428 | 13.500 | 0% |

All 5,100 VPN probes were received. Direct Internet test: 1,179/1,200 replies (1.75% loss), average 76.127 ms, maximum 809.427 ms. Local ECM gateway test: 50/50 replies, average 1.337 ms.

NetBird reported `Connection type: Relayed` and relay transport `ws` (WebSocket over TCP). P2P ICE retries were exhausted; the QUIC attempt was aborted after WebSocket connected. This does not prove UDP 443 was blocked. The tests were sequential, with different network conditions, and do not demonstrate that higher packet rates cause lower latency. These ICMP results are not a throughput or end-to-end video latency benchmark.

## 10. Troubleshooting

| Symptom | Check / action |
|---|---|
| No USB modem | Check adapter power, USB data cable and `lsusb`. |
| No `enx...` ECM interface | Query `AT+QCFG="usbnet"`; verify `cdc_ether` in `lsusb -t`; reset modem if required. |
| AT port busy | Close other terminal programs; check ModemManager if installed. |
| Registered but no Internet | Check APN, context 1, `QMAPWAC`, DHCP and `ip route get 1.1.1.1`. |
| Works until reboot or USB replug | Check autoconnect, `match.driver`, fixed interface/MAC binding and competing profiles. |
| NetBird socket missing | Check service status and journal; investigate error `209/STDOUT` using section 8. |
| High VPN latency | Compare ECM gateway, direct Internet and VPN RTT; inspect ICE and relay transport using `netbird status -d`. |
| P2P fails / WebSocket selected | Inspect `/var/log/netbird/client.log`, NAT traversal and the authorized NetBird server configuration. Do not disable the working relay before confirming alternatives. |

Useful diagnostics:

~~~bash
sudo journalctl -u NetworkManager -b -n 100 --no-pager
sudo journalctl -u netbird -b -n 100 --no-pager
sudo tail -n 200 /var/log/netbird/client.log
netbird status -d
~~~

## 11. Validation status

- [x] USB ECM enumeration and cellular Internet connection.
- [x] Automatic modem/profile reconnection after reboot and USB replug.
- [x] 5G NSA registration (LTE B3 + NR n41).
- [x] Cellular-only operation without USB Wi-Fi.
- [x] NetBird remote SSH and automatic reconnection after host reboot.
- [x] NetBird ICMP test: 5,100/5,100 replies over the four runs.
- [ ] Reboot test with final LogsDirectory setting / recommended drop-in.
- [ ] Direct P2P or QUIC relay performance verification.
- [ ] Recovery after radio coverage loss, sustained transfer and long-duration tests.

The cellular configuration is operational on the tested platform. The VPN showed latency spikes exceeding one second; do not treat this result as qualification for a safety-critical primary control link. The 5G-only validation excludes USB Wi-Fi; optional development-mode Wi-Fi switching is documented separately in section 12. No standalone WireGuard or kernel replacement is required.


## 12. Optional USB Wi-Fi — automatic AP / Station switching

For development and bench access, a USB Wi-Fi adapter can be added without changing the RM520N-GL ECM profile or NetBird. In cellular-only deployment, the adapter is not required.

### 12.1. Operating modes

| RM520N-GL USB presence | USB Wi-Fi | Expected behavior |
|---|---|---|
| Present | Absent | Cellular Internet + NetBird only. |
| Present | Present | Wi-Fi AP (hotspot), IPv4 Internet sharing through cellular when the cellular route is available. |
| Absent | Present, infrastructure SSID available | Wi-Fi Station (client); use infrastructure Wi-Fi for Internet. |
| Absent | Present, Station activation fails | Fall back to a local hotspot; Internet requires another working uplink. |
| Absent | Absent | No cellular or USB Wi-Fi connection; other interfaces are untouched. |

This policy detects **physical USB presence**, not signal strength or Internet reachability. A modem that remains plugged in but loses cellular coverage does not trigger Station mode. The fallback hotspot is retained until modem presence changes, the Wi-Fi adapter disappears/reappears, or the watchdog restarts. No periodic Station retry is performed while the fallback is active.

### 12.2. Identify the USB Wi-Fi adapter

Tested adapter: TP-Link USB Wi-Fi, Realtek RTL8822BU, USB ID `2357:0138`. This ID is specific to the tested hardware revision.

Use a local console before switching Wi-Fi modes or replacing the driver; SSH over Wi-Fi may disconnect.

~~~bash
sudo apt install -y dnsmasq-base iw avahi-daemon libnss-mdns
sudo systemctl enable --now avahi-daemon

lsusb
lsusb -t
iw dev
nmcli device status
~~~

Set the actual USB Wi-Fi interface name for subsequent commands in the same shell:

~~~bash
read -r -p 'USB Wi-Fi interface (wlx...): ' WIFI_IF
nmcli -f WIFI-PROPERTIES.AP device show "$WIFI_IF"
readlink -f "/sys/class/net/$WIFI_IF/device/driver"
~~~

AP support is required. Do not select the cellular ECM interface or an unrelated Wi-Fi adapter.

**Optional driver correction for the tested Orange Pi 6 image only.** On Linux `6.6.89-cix`, the alternate `88x2bu` driver was already supplied by the image; the system initially used `rtw88_8822bu`. Intermittent mDNS over AP mode was observed with the original driver. The following configuration was verified with the alternate driver after reboot:

~~~bash
modinfo 88x2bu
modinfo -F vermagic 88x2bu
modinfo -F alias 88x2bu
modinfo -p 88x2bu
~~~

Proceed only if the module is installed, its vermagic matches the running kernel, its aliases support the actual adapter, and both named parameters are available. Do not blacklist a working driver on a different board or image. Ensure an independent connection or local console for recovery.

~~~bash
sudo tee /etc/modprobe.d/99-ctuav-wifi.conf >/dev/null <<'CONF'
# CTUAV TP-Link RTL8822BU Wi-Fi configuration
blacklist rtw88_8822bu
options 88x2bu rtw_power_mgnt=0 rtw_ips_mode=0
CONF
sudo reboot
~~~

After reboot, set `WIFI_IF` again and verify:

~~~bash
read -r -p 'USB Wi-Fi interface (wlx...): ' WIFI_IF
readlink -f "/sys/class/net/$WIFI_IF/device/driver"
cat /sys/module/88x2bu/parameters/rtw_power_mgnt
cat /sys/module/88x2bu/parameters/rtw_ips_mode
~~~

Expected on the tested image: driver path ending in `rtl88x2bu`, both values `0`. No out-of-tree module compilation or kernel replacement was needed. To revert this driver override, remove only the above modprobe file and reboot from local access. This driver change is optional and is unrelated to the cellular-only latency benchmark.

### 12.3. Create Hotspot and Station profiles

The existing cellular Ethernet connection remains `CTUAV_cc_5G`. The Wi-Fi AP connection is `CTUAV_Hotspot`, with SSID `CTUAV_cc_5G`. The Station profile can use an existing infrastructure Wi-Fi connection (set its exact name below), or create one named `CTUAV_Station`.

Choose a non-overlapping hotspot subnet if `192.168.50.0/24` conflicts with existing local/VPN routes. The tested subnet was `192.168.50.0/24`.

~~~bash
AP_PROFILE=CTUAV_Hotspot
AP_SSID=CTUAV_cc_5G

if ! nmcli connection show "$AP_PROFILE" >/dev/null 2>&1; then
  read -rs -p 'Hotspot password (8-63 chars): ' AP_PSK; echo
  sudo nmcli device wifi hotspot ifname "$WIFI_IF" \
    con-name "$AP_PROFILE" ssid "$AP_SSID" \
    band bg channel 6 password "$AP_PSK"
  unset AP_PSK
fi

sudo nmcli connection modify "$AP_PROFILE" \
  connection.interface-name "$WIFI_IF" \
  802-11-wireless.mode ap \
  802-11-wireless.ssid "$AP_SSID" \
  802-11-wireless.band bg \
  802-11-wireless.channel 6 \
  ipv4.method shared \
  ipv4.addresses 192.168.50.1/24 \
  ipv6.method disabled \
  connection.autoconnect no

nmcli connection show
~~~

If a suitable Station profile already exists, use it. Otherwise create a profile by connecting to the infrastructure access point while it is in range (NetworkManager prompts for credentials):

~~~bash
read -r -p 'Existing Station profile name (or CTUAV_Station): ' STA_PROFILE
if ! nmcli connection show "$STA_PROFILE" >/dev/null 2>&1; then
  read -r -p 'Infrastructure Wi-Fi SSID: ' STA_SSID
  sudo nmcli --ask device wifi connect "$STA_SSID" \
    ifname "$WIFI_IF" name "$STA_PROFILE"
fi

sudo nmcli connection modify "$STA_PROFILE" \
  connection.interface-name "$WIFI_IF" \
  802-11-wireless.mode infrastructure \
  ipv4.method auto \
  ipv4.route-metric 600 \
  ipv6.route-metric 600 \
  connection.autoconnect no

nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
~~~

Disable autoconnect only for any additional profiles that compete for this same USB Wi-Fi interface. Do not disable autoconnect for `CTUAV_cc_5G` (ECM). The watchdog, not NetworkManager's Wi-Fi autoconnect priority, chooses between these two Wi-Fi profiles. The cellular default route retains metric 100.

The hotspot password is prompted interactively and must never be committed. It may briefly appear in local process arguments when creating the profile; configure credentials using an approved local method where required.

### 12.4. Install the automatic switching watchdog

The following script is a **portable reconstruction of the tested watchdog behavior**, not a byte-for-byte export of the original installed script. It uses the same USB ID, debounce, timeout and sticky fallback policy, and obtains the AP/Station UUIDs from the actual NetworkManager profile names at service startup. Validate the reconstructed script on a local console before headless deployment.

Store the device-specific values in a root-owned environment file. Run in the same shell where `WIFI_IF`, `AP_PROFILE` and `STA_PROFILE` were set:

~~~bash
# Verify the selected interface and UUIDs before writing the config.
ip link show "$WIFI_IF"
AP_UUID=$(nmcli -g connection.uuid connection show "$AP_PROFILE")
STA_UUID=$(nmcli -g connection.uuid connection show "$STA_PROFILE")
printf 'AP=%s\nStation=%s\n' "$AP_UUID" "$STA_UUID"
~~~

Do not proceed unless both UUIDs are non-empty and different. If a Wi-Fi adapter is replaced or profiles are recreated, regenerate the file below.

~~~bash
sudo tee /etc/default/ctuav-network >/dev/null <<CONF
WIFI_IF=$WIFI_IF
AP_UUID=$AP_UUID
STA_UUID=$STA_UUID
MODEM_USB_ID=2c7c:0801
CONF
~~~

Install the watchdog:

~~~bash
sudo tee /usr/local/bin/ctuav-network-watchdog.sh >/dev/null <<'SCRIPT'
#!/usr/bin/env bash
set -u
export LC_ALL=C

: "${WIFI_IF:?Missing WIFI_IF}"
: "${AP_UUID:?Missing AP_UUID}"
: "${STA_UUID:?Missing STA_UUID}"
MODEM_USB_ID="${MODEM_USB_ID:-2c7c:0801}"

CHECK_INTERVAL=2
CONFIRM_COUNT=3
STA_TIMEOUT=20
AP_TIMEOUT=30
RETRY_DELAY=15

stable=""
candidate=""
count=0
fallback=0
wifi_seen=0

log() { printf '%s\n' "$*"; }
modem_present() { lsusb -d "$MODEM_USB_ID" >/dev/null 2>&1; }

active_uuid() {
    nmcli --wait 5 -t -f UUID,DEVICE connection show --active |
        awk -F: -v dev="$WIFI_IF" '$2 == dev {print $1; exit}'
}

is_active() {
    local state
    state=$(nmcli --wait 5 -g GENERAL.STATE device show "$WIFI_IF" 2>/dev/null) || return 1
    [[ "${state%% *}" == 100 && "$(active_uuid)" == "$1" ]]
}

activate_profile() {
    nmcli --wait "$2" connection up uuid "$1" ifname "$WIFI_IF"
}

log "Network Watchdog started"
while true; do
    if [[ ! -d "/sys/class/net/$WIFI_IF" ]]; then
        if (( wifi_seen )); then log "USB Wi-Fi removed"; fi
        wifi_seen=0
        stable=""
        candidate=""
        count=0
        fallback=0
        sleep "$CHECK_INTERVAL"
        continue
    fi
    wifi_seen=1

    if modem_present; then observed=present; else observed=absent; fi
    if [[ "$observed" == "$candidate" ]]; then
        if (( count < CONFIRM_COUNT )); then count=$((count + 1)); fi
    else
        candidate="$observed"
        count=1
    fi

    # Do not change profiles until three consecutive observations agree.
    if (( count < CONFIRM_COUNT )); then
        sleep "$CHECK_INTERVAL"
        continue
    fi
    if [[ "$stable" != "$candidate" ]]; then
        stable="$candidate"
        fallback=0
        log "Modem state: $stable"
    fi

    if [[ "$stable" == present ]]; then
        if ! is_active "$AP_UUID"; then
            log "Modem detected: switching to AP mode"
            if activate_profile "$AP_UUID" "$AP_TIMEOUT"; then
                log "Hotspot active: CTUAV_cc_5G"
            else
                log "Hotspot activation failed; retrying"
                sleep "$RETRY_DELAY"
            fi
        fi
    elif (( fallback == 0 )); then
        if ! is_active "$STA_UUID"; then
            log "Modem removed: switching to Station mode"
            if activate_profile "$STA_UUID" "$STA_TIMEOUT"; then
                log "Station connected"
            else
                log "Station activation failed; falling back to AP"
                fallback=1
                if activate_profile "$AP_UUID" "$AP_TIMEOUT"; then
                    log "Fallback hotspot active"
                else
                    sleep "$RETRY_DELAY"
                fi
            fi
        fi
    elif ! is_active "$AP_UUID"; then
        if activate_profile "$AP_UUID" "$AP_TIMEOUT"; then
            log "Fallback hotspot active"
        else
            sleep "$RETRY_DELAY"
        fi
    fi
    sleep "$CHECK_INTERVAL"
done
SCRIPT
sudo chmod 755 /usr/local/bin/ctuav-network-watchdog.sh
sudo bash -n /usr/local/bin/ctuav-network-watchdog.sh
~~~

The UUIDs are read from the environment file, not copied from another machine. The watchdog never restarts NetworkManager or NetBird. If the USB Wi-Fi adapter is absent, it waits without modifying the cellular Ethernet profile. A blocking NetworkManager activation can delay detection of another USB change until the activation returns.

### 12.5. Start on boot with systemd

~~~bash
sudo tee /etc/systemd/system/ctuav-network.service >/dev/null <<'UNIT'
[Unit]
Description=CTUAV 5G / USB Wi-Fi Network Watchdog
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
EnvironmentFile=/etc/default/ctuav-network
ExecStart=/usr/local/bin/ctuav-network-watchdog.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now ctuav-network.service
systemctl is-enabled ctuav-network.service
systemctl is-active ctuav-network.service
sudo journalctl -u ctuav-network.service -f
~~~

Use `Ctrl+C` to exit the journal view (the service continues running). If replacing an existing running service, restart it explicitly from local console after reviewing the config.

### 12.6. Verify mode changes and local SSH

~~~bash
nmcli device status
nmcli connection show --active
ip -br -4 addr
ip -4 route
sudo journalctl -u ctuav-network.service -b --no-pager
~~~

- With both adapters plugged in: connect a laptop to the hotspot; verify SSH to `192.168.50.1` and, when cellular Internet is working, Internet sharing.
- Unplug only the RM520N-GL: the Wi-Fi adapter should join the infrastructure SSID. Reconnect the laptop to that network. Use the DHCP address or `orangepi6.local` if mDNS is available.
- Plug RM520N-GL back in: reconnect the laptop to the hotspot and verify SSH and Internet access again.
- Boot with only the RM520N-GL installed: verify `CTUAV_cc_5G` and NetBird without USB Wi-Fi.
- Test Station-unavailable fallback separately in a controlled environment; confirm local AP access, not necessarily Internet.

Examples from the laptop (replace the username/hostname if needed):

~~~bash
ssh orangepi@192.168.50.1
# When both devices are connected to the same infrastructure Wi-Fi:
ssh orangepi@orangepi6.local
~~~

mDNS requires local multicast connectivity and an appropriate resolver on both hosts. Wi-Fi clients may take additional time to reconnect; the service's activation log does not measure end-to-end SSH downtime.

**Observed validation on 26 November 2026 (original watchdog):**

| Test | Observation | Status |
|---|---|---|
| Both adapters at boot | Hotspot activated; local SSH and cellular Internet sharing worked. | PASS |
| Modem removed | Station connected 7 s and 12 s after confirmed absence in two observed transitions. | PASS |
| Modem reinserted | Hotspot active 6 s after confirmed presence in the observed transition. | PASS |
| No USB Wi-Fi | Cellular-only boot and NetBird SSH worked. | PASS |
| Station unavailable | Fallback branch implemented; no completed test record available. | Pending |
| Modem present but radio coverage lost | Not a trigger for this USB-presence policy; recovery behavior not validated. | Pending |
| Reconstructed script in this guide | Requires local validation; historical timings apply to the original installed script. | Pending |

These Wi-Fi tests are separate from the 5G-only NetBird latency benchmark in section 9.

### 12.7. Manual switching and rollback

For manual Wi-Fi control, first stop the watchdog. Otherwise it may restore the automatic policy.

~~~bash
sudo systemctl stop ctuav-network.service

# Manual hotspot:
sudo nmcli connection up CTUAV_Hotspot
# OR manual Station (use the actual Station profile name):
sudo nmcli connection up "$STA_PROFILE"

# Restore automatic switching:
sudo systemctl start ctuav-network.service
~~~

To permanently remove automatic switching while retaining the profiles:

~~~bash
sudo systemctl disable --now ctuav-network.service
sudo nmcli connection modify CTUAV_Hotspot connection.autoconnect no
sudo nmcli connection modify "$STA_PROFILE" connection.autoconnect yes
sudo nmcli connection up "$STA_PROFILE"
~~~

Run rollback locally. This does not alter ECM, NetBird, or unrelated profiles. For cellular-only operation, simply remove the USB Wi-Fi adapter; no manual switch or service disable is required.

## References

- [Quectel RM520N-GL adapter setup and ECM commands](https://www.waveshare.com/wiki/RM520N-GL)
- [NetworkManager 1.46 connection settings](https://networkmanager.dev/docs/api/1.46/nm-settings-nmcli.html)
- [NetBird Linux installation](https://docs.netbird.io/get-started/install/linux)
- [NetBird CLI reference](https://docs.netbird.io/get-started/cli)
