# Changelog

## Quality v0.2.1
- Synchronize repository documentation and acceptance checklist.
- Add offline tests for burst loss and LTE/NR NSA parsing, plus no-service handling.
- Reject campaigns above 65535 ICMP packets per test to avoid sequence-number wrap.
- Tighten LTE field-length validation and print final per-test status.

## Quality v0.2.0
- Stream progress and preserve final transmit/receive counts.
- Replace combined fixed-count/deadline ping with fixed-count plus external timeout.
- Add multi-target RTT, payload sweep, soak, loss bursts, nominal windows.
- Add opt-in RF sampling and authorized iperf3 load tests.

## Quality v0.1.0
- ECM gateway/direct Internet, NetBird and local RTT tests; raw logs, CSV and JSON.
- Offline metric tests and configurable engineering reference thresholds.

## Installer v0.1.1
- Check dnsmasq-base for shared Hotspot, offer installation, show nmcli errors.
- Preserve existing profiles where possible.

## Installer v0.1.0
- Interactive ECM setup, optional modem AT configuration, AP/Station profile reuse, watchdog, status and backup.

Versions are independent. Hardware acceptance remains tracked in docs/VALIDATION.md.
