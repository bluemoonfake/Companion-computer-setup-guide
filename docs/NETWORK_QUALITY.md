# Network quality benchmark

## Scope

The executable quality is independent of config. It uses Linux iputils ping, iproute2 and Python 3 standard library. No modem commands, configuration changes or network restarts are performed. Root is required for rates above 5 Hz in this tool. Test on the bench, not in flight.

## Run

~~~bash
cd ~/Companion-computer-setup-guide
git pull --ff-only
./quality --self-test
sudo ./quality --mode cellular --duration 60
sudo ./quality --mode netbird --netbird PEER_IPV4 --rates 5,10,20,50 --duration 60
~~~

Or sudo ./quality for both tests; enter the remote NetBird peer when prompted. The gateway is derived from the ECM default route. The direct Internet target defaults to 1.1.1.1. The ECM interface is detected by USB ID 2c7c:0801 and cdc_ether, not a fixed MAC/interface name. NetBird defaults to wt0; use --vpn-iface for a different tunnel interface. Tests execute sequentially, with count = rate x duration. The wall-clock time may be longer because of the final reply wait.

On a Linux laptop attached to the Hotspot, copy or clone this branch and run:

~~~bash
./quality --mode local --local 192.168.50.1 --duration 20
ssh ctuav@orangepi.local
~~~

Do not test the AP gateway from the Orange Pi itself: that would measure a local address, not Wi-Fi. A reachable peer that responds to ICMP is required for a meaningful remote test; firewall ICMP filtering can appear as packet loss.

## Read the output

Each run creates a timestamped directory under quality-results/ (or --output PATH) with mode 0700. If sudo was used, read it with sudo. No credentials are intentionally collected; IP addresses and routes are recorded. Keep results out of Git and redact before sharing.

| Field | Meaning |
|---|---|
| transmitted / received | Echo packets actually sent / unique replies reported by ping |
| loss_pct | 100 x (transmitted - received) / transmitted |
| mean_ms / median_ms | Mean and median round-trip time |
| p95_ms / p99_ms | Linear-interpolated percentiles of received RTTs |
| min_ms / max_ms | Minimum and maximum received RTT |
| mdev_ms | Population standard deviation of unique received RTTs |
| mean_abs_rtt_delta_ms | Mean absolute RTT difference between consecutive received sequence numbers; gaps excluded, not RFC jitter |
| bounded_rtt_samples | Count of time<... measurements, represented using the displayed upper bound |
| measurement | COMPLETE only when full packet count and reply parser agree, ping exits normally, and route snapshots agree; otherwise INVALID |
| reference | WITHIN_REFERENCE / OUTSIDE_REFERENCE / NOT_EVALUATED |

Raw ping output (including native ping statistics), per-sequence reply/no_reply CSV, route snapshots and summary.json are retained. Percentiles exclude missing replies; high packet loss can therefore make apparent RTT percentiles misleading. Rounded displayed ping RTT values are used, so computed mean/mdev can differ slightly from native ping values, especially with duplicate replies. Invalid measurements must not be treated as loss-free. A complete zero-reply measurement is 100% loss with undefined RTTs.

Default reference limits: mean 100 ms, maximum 150 ms, mdev 20 ms, loss 0%. These are configurable screening values, not standards or flight safety approval. For example:

~~~bash
sudo ./quality --mode netbird --netbird PEER_IPV4 \
  --mean-limit 120 --max-limit 300 --mdev-limit 30 --loss-limit 1
~~~

Exit 0 means the requested measurements completed (not necessarily within reference). Exit 2 indicates invalid/skipped tests or setup errors. Exit 130 means interrupted. Check summary.json for per-test status. The offline --self-test checks parsing, loss, percentile, RTT delta and reference logic.

## Additional checks

Before and after each campaign, record:

~~~bash
sudo ctuav-net status
sudo netbird status --detail
ip -4 route
~~~

If the AT port is free, optionally use minicom on the verified RM520N AT port and capture AT+QENG="servingcell", AT+QCSQ and AT+QNWPREFCFG="nr5g_disable_mode". Do not run competing AT applications. RF indicators are snapshots, not proof of sustained radio quality. Compare RSRP, RSRQ, SINR and NSA/SA state with RTT results; follow the modem manual for units.

Check NetBird peer connection type (P2P or Relayed) and underlying uplink separately. Sequential rate tests do not establish that packet frequency caused any latency change. Repeat under comparable conditions and include long-duration tests for qualification.

The default ICMP benchmark does not measure one-way delay, UDP application loss, available throughput, or camera/video end-to-end latency. Optional iperf3 is described below and requires an explicitly controlled reachable server. Do not infer flight-control suitability from ICMP results.

## Validation status

The original manual benchmark used 5, 10, 20 and 50 Hz with 60-second nominal test windows. This script automates that method and adds per-packet analysis. The new implementation must be checked on the actual target hardware; do not confuse previous manual results with results produced by this tool.


## Advanced benchmark v0.2.0

The optional --deep profile adds a second public Internet target (default 8.8.8.8), ICMP payloads 512/1200/1400 bytes and a 600-second soak (configurable --soak-duration 10..1800). The payload sweep allows fragmentation by default and is not PMTU discovery. All tests use the verified cellular route; high latency may be caused by remote ICMP handling as well as radio/network conditions.

Progress shows unique replies, highest received sequence and most recent RTT, not actual transmitted count. Final summary reports actual transmitted/received counts. The longest consecutive missing sequence count and loss bursts describe loss in the test stream, not exact outage duration. Ten-second nominal sequence windows are exported for complete tests, plus P95 absolute adjacent RTT delta and fraction of replies above 150 ms. Incomplete tests remain INVALID.

### Optional RF monitoring

Install python3-serial and psmisc. Close minicom and other AT applications, then use --rf-port /dev/ttyUSB2 only after checking the port belongs to RM520N. The tool checks USB ID and port occupancy, opens the port exclusively, verifies ATI and logs read-only AT+QENG="servingcell" and AT+QCSQ at nominal five-second intervals (configurable --rf-interval). No band locks, APN changes, resets or scan commands. AT sampling cannot guarantee continuous observation of cell state.

rf.csv and rf-raw.jsonl contain UTC timestamps, state, RAT, LTE/NR band, channel, PCI, signal metrics and raw data. LTE SINR is deliberately recorded as raw rather than converted; NR5G-NSA and SA use documented field order. Missing/invalid readings must not be interpreted as zero signal. Observed cell-signature changes are not necessarily handovers (NSA secondary-cell release/addition can change the signature). Raw cell data is private location-related information: redact before sharing.

Reference: [Quectel RG520N/RM5x0N AT Commands Manual V1.1](https://www.quectel.com/content/uploads/2025/09/Quectel_RG520NRG525FRG5x0FRM5x0N_Series_AT_Commands_Manual_V1.1.pdf), QENG serving-cell response.

### Optional throughput and loaded latency

Use iperf3 on a controlled server you own or have permission to test. Run iperf3 -s on it; firewall the test port to trusted clients. The Orange Pi must route to the server through the RM520N ECM interface. The client refuses an unexpected route or iperf3 without --bind-dev. It runs TCP upload/download with configurable pacing cap (--tcp-mbps, default 10) and UDP upload/download at --udp-mbps 1,3,5, with --load-duration 30 nominal seconds for concurrent ping. Each iperf session runs five seconds longer than the requested ping window. --iperf-port defaults to 5201.

Each load trial stores native iperf JSON, sender/receiver summaries, UDP loss and jitter if supplied by iperf, TCP retransmissions if present, route snapshots and concurrent latency. The loaded ping is started shortly after launching iperf; timestamps and iperf intervals are retained, but overlap and saturation are not guaranteed. Compare with the unloaded cellular-internet measurement at the same target; do not claim a causal bufferbloat grade without verifying overlap and offered/achieved rate. TCP pacing cap is not a maximum-capacity test. The offered UDP bitrate is not achieved bitrate.

Reference: [ESnet iperf3 documentation](https://software.es.net/iperf/invoking.html). Load tests consume mobile data and require explicit --iperf-server; no external server is contacted automatically. No configuration changes are made. Do not test during critical operations.

v0.2.0 is not yet validated on target hardware. Run the offline self-test and short smoke test before long tests.
