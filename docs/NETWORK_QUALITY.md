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

This tool does not measure one-way delay, UDP application loss, available throughput, or camera/video end-to-end latency. TCP/UDP iperf3 requires an explicitly controlled reachable server and is intentionally outside the default benchmark. Do not infer flight-control suitability from ICMP results.

## Validation status

The original manual benchmark used 5, 10, 20 and 50 Hz with 60-second nominal test windows. This script automates that method and adds per-packet analysis. The new implementation must be checked on the actual target hardware; do not confuse previous manual results with results produced by this tool.
