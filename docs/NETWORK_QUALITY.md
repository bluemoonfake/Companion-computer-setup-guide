# Network quality

Select the correct modem branch from [05 — Cellular](05_CELLULAR.md) first. The main branch contains common documentation only.

~~~bash
./quality --self-test
sudo ./quality --mode cellular --deep --duration 10 --soak-duration 30
sudo ./quality --mode cellular --deep
~~~

See the selected branch's Network Quality guide for RF, NetBird and controlled iperf3 tests. Run on the bench only; reference thresholds do not establish flight suitability.
