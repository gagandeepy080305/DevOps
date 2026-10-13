# Monitoring Exercise 6

## Objective

The objective of this exercise is to build **real-time operations monitoring and alerting** for **ZAPPTTO**, a fast-paced delivery service.

A Python app simulates delivery metrics, **Prometheus** scrapes them and evaluates alert rules, **Grafana** visualizes them on a dashboard, and a **Jenkins** pipeline automates building and deploying the whole stack.

---

## Prerequisites

* macOS (Apple Silicon)
* Colima (Docker engine) and Docker CLI
* Python 3 with `prometheus-client`
* Prometheus, Grafana and Jenkins, all run as Docker containers

---

## Project Files

```
Exercise-6/
├── delivery_metrics.py        # Python script that simulates delivery metrics on port 8000
├── requirements.txt           # prometheus-client
├── Dockerfile                 # Container image for delivery_metrics.py
├── prometheus.yml             # Prometheus scrape configuration
├── alert_rules.yml            # Prometheus alert rules
├── Jenkinsfile                # Jenkins pipeline that builds and deploys the stack
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/prometheus.yml   # Prometheus data source (http://172.17.0.1:9090)
│   │   └── dashboards/dashboards.yml    # Loads dashboards from /var/lib/grafana/dashboards
│   └── dashboards/delivery-monitoring.json  # "ZAPPTTO Delivery Monitoring" dashboard (4 panels)
└── jenkins/
    ├── Dockerfile             # Jenkins LTS + Docker CLI + pipeline plugins
    └── init.groovy.d/create-delivery-job.groovy  # Creates the pipeline job from the Jenkinsfile
```

---

## Changes from the Lab Instructions

| Lab instruction | What was done instead | Why |
|-----------------|-----------------------|-----|
| No `global` block in `prometheus.yml`; the lab says the default scrape interval is 15s | Added `scrape_interval: 15s` and `evaluation_interval: 15s` | Prometheus's real default is **1 minute** for both (confirmed in [Step 9](#9-fix-the-scrape-interval)). |
| Log in to Grafana as `admin`/`admin` and add the data source and dashboard by hand | Data source and dashboard are **provisioned from files** in `grafana/`, with anonymous Admin access | Dashboards as code, and no passwords to type. Local lab only. |
| Unlock Jenkins with the initial admin password and paste the Jenkinsfile into a new job | A custom Jenkins image skips the setup wizard and creates the job from the Jenkinsfile at startup. Jenkins listens only on `127.0.0.1` | Same pipeline, no passwords needed. Local lab only. |
| `jenkins/jenkins:lts` | `jenkins/jenkins:lts-jdk21` + Docker CLI + mounted Docker socket | The stock image has no `docker` command, so the pipeline's `docker build`/`docker run` steps would fail. |
| Jenkinsfile mounts `$WORKSPACE/prometheus.yml` with `-v` | `docker create` + `docker cp` + `docker start` | The workspace is inside the Jenkins container, which the Docker engine cannot see, so bind mounts from it don't work. |
| Jenkinsfile copies files from `/path/to/your/local/files` | The Exercise-6 folder is mounted read-only into Jenkins at `/project` | Gives the *Setup Workspace* stage a real source path. |
| — | Added *Clean Up Old Containers* and *Verify Services* stages | Lets the pipeline be re-run, and checks that all services respond. |

---

## Steps Performed

### 1. Write and Run the Python Application

Created [`delivery_metrics.py`](./delivery_metrics.py). Every second it generates random delivery numbers and exposes them as Prometheus metrics on port `8000`:

| Metric | Type | Meaning |
|--------|------|---------|
| `total_deliveries` | Gauge | pending + on the way + delivered |
| `pending_deliveries` | Gauge | random 10–20 |
| `on_the_way_deliveries` | Gauge | random 5–20 |
| `average_delivery_time` | Summary | random 15–45 seconds per observation (`_sum` / `_count`) |

```bash
pip3 install prometheus-client
python3 delivery_metrics.py
```

```
[INFO] Starting the HTTP server on port 8000...
[INFO] HTTP server started. Simulating deliveries...
[DEBUG] Total deliveries: 88
[DEBUG] Pending deliveries: 19
[DEBUG] On-the-way deliveries: 17
[DEBUG] Average delivery time: 22.19 seconds
[INFO] Sleeping for 1 seconds...
[DEBUG] Total deliveries: 75
[DEBUG] Pending deliveries: 12
[DEBUG] On-the-way deliveries: 14
[DEBUG] Average delivery time: 24.03 seconds
[INFO] Sleeping for 1 seconds...
```

Checked the metrics endpoint:

```bash
curl http://localhost:8000/metrics | grep -E "deliver|python_info"
```

```
python_info{implementation="CPython",major="3",minor="9",patchlevel="6",version="3.9.6"} 1.0
# HELP total_deliveries Total number of deliveries
# TYPE total_deliveries gauge
total_deliveries 64.0
# HELP pending_deliveries Number of pending deliveries
# TYPE pending_deliveries gauge
pending_deliveries 11.0
# HELP on_the_way_deliveries Number of deliveries on the way
# TYPE on_the_way_deliveries gauge
on_the_way_deliveries 12.0
# HELP average_delivery_time Average delivery time in seconds
# TYPE average_delivery_time summary
average_delivery_time_count 4.0
average_delivery_time_sum 105.66156930079912
```

The `/metrics` endpoint is created automatically by `start_http_server()` from `prometheus_client`.

![Run Metrics Script](./Screenshots/01%20Run%20Metrics%20Script.png)

![Metrics Endpoint](./Screenshots/02%20Metrics%20Endpoint.png)

---

### 2. Run the App, Prometheus and Grafana in Docker

Containerized the app with [`Dockerfile`](./Dockerfile), so Prometheus (in Docker) can reach it at the Docker bridge gateway `172.17.0.1:8000`:

```bash
docker build -t delivery_metrics .
docker run -d -p 8000:8000 --name delivery_metrics delivery_metrics
```

Created [`prometheus.yml`](./prometheus.yml) and [`alert_rules.yml`](./alert_rules.yml) as in the lab.

| Alert | Expression | For | Severity |
|-------|-----------|-----|----------|
| `HighPendingDeliveries` | `pending_deliveries > 10` | 15s | warning |
| `HighAverageDeliveryTime` | `(average_delivery_time_sum / average_delivery_time_count) > 30` | — | critical |

Started Prometheus with **host networking**, exactly as the lab writes it:

```bash
docker run -d --name prometheus --network=host \
  -v ./prometheus.yml:/etc/prometheus/prometheus.yml \
  -v ./alert_rules.yml:/etc/prometheus/alert_rules.yml \
  prom/prometheus
```

Started Grafana with the provisioning files (data source + dashboard) mounted:

```bash
docker run -d --name grafana -p 3000:3000 \
  -e GF_AUTH_ANONYMOUS_ENABLED=true -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin \
  -v ./grafana/provisioning:/etc/grafana/provisioning \
  -v ./grafana/dashboards:/var/lib/grafana/dashboards \
  grafana/grafana
```

```
IMAGE              STATUS          PORTS                                         NAMES
grafana/grafana    Up 10 seconds   0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp   grafana
prom/prometheus    Up 10 seconds                                                 prometheus
delivery_metrics   Up 53 seconds   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp   delivery_metrics
```

Prometheus has no published ports because it uses the host network. Colima forwards its port `9090` to the Mac automatically.

![Start Containers](./Screenshots/03%20Start%20Containers.png)

---

### 3. Verify Prometheus Targets and Alerts

```bash
curl -s localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | [.labels.job, .scrapeUrl, .health] | @tsv'
curl -s localhost:9090/api/v1/alerts | jq -r '.data.alerts[] | [.labels.alertname, .labels.severity, .state, .value] | @tsv'
```

```
delivery_service          http://172.17.0.1:8000/metrics      up
prometheus                http://localhost:9090/metrics       up

HighPendingDeliveries     warning     firing     1.4e+01
HighAverageDeliveryTime   critical    firing     3.051524640761578e+01
```

Both scrape targets are **up**, and both alerts are **firing**. Pending deliveries were 14 (> 10) and the average delivery time was 30.5s (> 30s).

![Targets and Alerts API](./Screenshots/04%20Targets%20and%20Alerts%20API.png)

**Prometheus → Status → Target health:**

![Prometheus Targets](./Screenshots/05%20Prometheus%20Targets.png)

**Prometheus → Alerts:**

![Prometheus Alerts](./Screenshots/06%20Prometheus%20Alerts.png)

**Prometheus → Query:**

![Prometheus Query](./Screenshots/07%20Prometheus%20Query.png)

---

### 4. Grafana Data Source

Grafana is at `http://localhost:3000`. The Prometheus data source was provisioned from [`grafana/provisioning/datasources/prometheus.yml`](./grafana/provisioning/datasources/prometheus.yml) with the lab's URL `http://172.17.0.1:9090`:

```yaml
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://172.17.0.1:9090
    isDefault: true
```

Grafana's *Save & Test* equivalent (`/api/datasources/uid/prometheus/health`) returned:

```
"message":"Successfully queried the Prometheus API.","status":"OK"
```

![Grafana Data Source](./Screenshots/08%20Grafana%20Data%20Source.png)

---

### 5. Grafana Dashboard

The **ZAPPTTO Delivery Monitoring** dashboard was provisioned from [`grafana/dashboards/delivery-monitoring.json`](./grafana/dashboards/delivery-monitoring.json) with the 4 panels from the lab:

| Panel | Query |
|-------|-------|
| Total Deliveries | `total_deliveries` |
| Pending Deliveries | `pending_deliveries` |
| On-the-Way Deliveries | `on_the_way_deliveries` |
| Average Delivery Time | `average_delivery_time_sum / average_delivery_time_count` |

![Grafana Dashboard](./Screenshots/09%20Grafana%20Dashboard.png)

---

### 6. Build and Start Jenkins

Checked for an existing Jenkins container (none found):

```bash
docker ps -a | grep jenkins
```

The stock `jenkins/jenkins:lts` image has no Docker CLI, so the pipeline could not run `docker build`/`docker run`. [`jenkins/Dockerfile`](./jenkins/Dockerfile) adds it:

```dockerfile
FROM jenkins/jenkins:lts-jdk21

# Docker CLI so pipeline steps can run docker commands against the Docker engine (via the mounted socket)
USER root
ARG DOCKER_VERSION=27.5.1
RUN curl -fsSL "https://download.docker.com/linux/static/stable/$(uname -m)/docker-${DOCKER_VERSION}.tgz" \
    | tar -xz -C /usr/local/bin --strip-components=1 docker/docker
USER jenkins

# Pipeline plugins
RUN jenkins-plugin-cli --plugins workflow-aggregator pipeline-stage-view

# Local lab only: skip the setup wizard and create the pipeline job from /project/Jenkinsfile at startup
ENV JAVA_OPTS=-Djenkins.install.runSetupWizard=false
COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/
```

[`create-delivery-job.groovy`](./jenkins/init.groovy.d/create-delivery-job.groovy) creates a Pipeline job from the Jenkinsfile. This is the same as *New Item → Pipeline → Pipeline script* in the web UI.

```bash
docker build -t jenkins-docker ./jenkins
docker run -d --name jenkins \
  -p 127.0.0.1:8080:8080 -p 127.0.0.1:50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock --group-add 991 \
  -v "$PWD":/project:ro \
  jenkins-docker
```

* `-p 127.0.0.1:...` – Jenkins is only reachable from this Mac
* `-v /var/run/docker.sock` + `--group-add 991` – lets the pipeline use the Docker engine (991 is the `docker` group in the Colima VM)
* `-v "$PWD":/project:ro` – the Exercise-6 folder, used by the *Setup Workspace* stage

```
Created pipeline job: delivery-monitoring-pipeline
Jenkins is fully up and running
```

![Build and Start Jenkins](./Screenshots/11%20Build%20and%20Start%20Jenkins.png)

---

### 7. Run the Jenkins Pipeline

The [`Jenkinsfile`](./Jenkinsfile) has 7 stages:

| Stage | What it does |
|-------|--------------|
| Pre-check Docker | `docker --version` and `docker info`; fails early if Docker is unavailable |
| Setup Workspace | Copies the app, Dockerfile, Prometheus/alert configs and Grafana files from `/project` into the workspace |
| Clean Up Old Containers | `docker rm -f delivery_metrics prometheus grafana` so the pipeline can be re-run |
| Build Docker Image | `docker build -t delivery_metrics .` |
| Run Application | `docker run -d -p 8000:8000 --name delivery_metrics delivery_metrics` |
| Run Prometheus & Grafana | `docker create` → `docker cp` config files → `docker start` |
| Verify Services | Checks `/metrics`, Prometheus `/-/ready` and Grafana `/api/health` |

Build **#1** finished with **SUCCESS**. The stage view below was taken at the end of the exercise and also shows builds #2 and #3 from Steps 8–9:

![Jenkins Pipeline Stage View](./Screenshots/10%20Jenkins%20Pipeline%20Stage%20View.png)

Console output for the build and deploy stages:

```
+ docker build -t delivery_metrics .
Step 1/7 : FROM python:3.11-slim
...
Successfully tagged delivery_metrics:latest
+ docker run -d -p 8000:8000 --name delivery_metrics delivery_metrics
e23479be99a084115e2797a4aaa3d6d4849a93dca535abc05178c051531adf91
+ docker create --name prometheus -p 9090:9090 prom/prometheus
+ docker cp prometheus.yml prometheus:/etc/prometheus/prometheus.yml
+ docker cp alert_rules.yml prometheus:/etc/prometheus/alert_rules.yml
+ docker start prometheus
+ docker create --name grafana -p 3000:3000 -e GF_AUTH_ANONYMOUS_ENABLED=true -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin grafana/grafana
+ docker cp grafana/provisioning/. grafana:/etc/grafana/provisioning/
+ docker cp grafana/dashboards grafana:/var/lib/grafana/
+ docker start grafana
```

![Pipeline Build and Deploy](./Screenshots/12%20Pipeline%20Build%20and%20Deploy.png)

And the *Verify Services* stage:

```
--- delivery_metrics ---
total_deliveries 87.0
pending_deliveries 12.0
on_the_way_deliveries 16.0
--- prometheus ---
Prometheus Server is Ready.
--- grafana ---
{ "database": "ok", "version": "13.2.4", ... }

NAMES              IMAGE              STATUS          PORTS
grafana            grafana/grafana    Up 2 seconds    0.0.0.0:3000->3000/tcp, :::3000->3000/tcp
prometheus         prom/prometheus    Up 2 seconds    0.0.0.0:9090->9090/tcp, :::9090->9090/tcp
delivery_metrics   delivery_metrics   Up 2 seconds    0.0.0.0:8000->8000/tcp, :::8000->8000/tcp
jenkins            jenkins-docker     Up 26 seconds   127.0.0.1:8080->8080/tcp, 127.0.0.1:50000->50000/tcp
Finished: SUCCESS
```

![Pipeline Verify Services](./Screenshots/13%20Pipeline%20Verify%20Services.png)

---

### 8. Simulate Alerts

Modified `delivery_metrics.py` to push pending deliveries far above the alert threshold:

```python
pending = random.randint(50, 100)  # Increase range to exceed alert threshold
```

Re-ran the pipeline (build **#2**). The *Build Docker Image* stage rebuilt the image with the new code (`Step 5/7 : COPY delivery_metrics.py .` was no longer cached), and *Verify Services* reported `pending_deliveries 69.0`.

---

### 9. Fix the Scrape Interval

While waiting for data after build #2, Prometheus had collected only 9 samples in about 8.5 minutes, so it was scraping once a **minute**, not every 15s. Prometheus's live configuration confirmed it:

```bash
curl -s localhost:9090/api/v1/status/config | jq -r .data.yaml | head -4
```

```
global:
  scrape_interval: 1m
  scrape_timeout: 10s
  evaluation_interval: 1m
```

The lab's note says the default interval is 15s, but that value only comes from the sample config shipped in the `prom/prometheus` image. Our `prometheus.yml` replaces that file, so Prometheus's built-in default of **1m** applies. With a 1m evaluation interval, `for: 15s` effectively means "two evaluations a minute apart".

Added a `global` block to [`prometheus.yml`](./prometheus.yml):

```yaml
global:
  scrape_interval: 15s      # Prometheus default is 1m when not set
  evaluation_interval: 15s  # how often alert rules are evaluated (default 1m)
```

Re-ran the pipeline (build **#3**, still with pending at 50–100). Prometheus then reported `scrape_interval: 15s` and `evaluation_interval: 15s`.

![Prometheus Default Scrape Interval](./Screenshots/14%20Prometheus%20Default%20Scrape%20Interval.png)

---

### 10. Verify the Simulated Alerts

About 3 minutes after build #3:

```bash
curl -s localhost:8000/metrics | grep -E '^(total|pending|on_the_way)_deliveries'
curl -s localhost:9090/api/v1/alerts | jq -r '.data.alerts[] | [.labels.alertname, .labels.severity, .state, .value] | @tsv'
```

```
total_deliveries 109.0
pending_deliveries 63.0
on_the_way_deliveries 5.0

HighPendingDeliveries     warning     firing     7.4e+01
HighAverageDeliveryTime   critical    firing     3.01686667188679e+01
```

`HighPendingDeliveries` is firing with a value of **74**, far above the threshold of 10. Before the change it fired at 14.

![Simulated Alerts Metrics](./Screenshots/15%20Simulated%20Alerts%20Metrics.png)

**Prometheus → Alerts:**

![Simulated Alerts Prometheus](./Screenshots/16%20Simulated%20Alerts%20Prometheus.png)

**Grafana dashboard:** pending deliveries now range between 50 and 100:

![Simulated Alerts Grafana](./Screenshots/17%20Simulated%20Alerts%20Grafana.png)

After this run, `delivery_metrics.py` was set back to `random.randint(10, 20)`, so the file in this folder matches the lab's original version.

---

## Screenshots

| # | Screenshot | Shows |
|---|-----------|-------|
| 1 | [Run Metrics Script](./Screenshots/01%20Run%20Metrics%20Script.png) | `delivery_metrics.py` printing simulated metrics, and `curl /metrics` |
| 2 | [Metrics Endpoint](./Screenshots/02%20Metrics%20Endpoint.png) | `http://localhost:8000/metrics` in the browser |
| 3 | [Start Containers](./Screenshots/03%20Start%20Containers.png) | App, Prometheus (host network) and Grafana containers starting |
| 4 | [Targets and Alerts API](./Screenshots/04%20Targets%20and%20Alerts%20API.png) | Both targets `up`, both alerts `firing` |
| 5 | [Prometheus Targets](./Screenshots/05%20Prometheus%20Targets.png) | Status → Target health, `delivery_service` and `prometheus` UP |
| 6 | [Prometheus Alerts](./Screenshots/06%20Prometheus%20Alerts.png) | `delivery_alerts` group with both alerts FIRING |
| 7 | [Prometheus Query](./Screenshots/07%20Prometheus%20Query.png) | Current values of the three delivery gauges |
| 8 | [Grafana Data Source](./Screenshots/08%20Grafana%20Data%20Source.png) | Provisioned Prometheus data source at `http://172.17.0.1:9090` |
| 9 | [Grafana Dashboard](./Screenshots/09%20Grafana%20Dashboard.png) | ZAPPTTO Delivery Monitoring dashboard with 4 panels |
| 10 | [Jenkins Pipeline Stage View](./Screenshots/10%20Jenkins%20Pipeline%20Stage%20View.png) | All 7 stages green for builds #1–#3 |
| 11 | [Build and Start Jenkins](./Screenshots/11%20Build%20and%20Start%20Jenkins.png) | Building the Jenkins image and starting the container |
| 12 | [Pipeline Build and Deploy](./Screenshots/12%20Pipeline%20Build%20and%20Deploy.png) | Console output of the build/run/deploy stages |
| 13 | [Pipeline Verify Services](./Screenshots/13%20Pipeline%20Verify%20Services.png) | Verify stage output and `Finished: SUCCESS` |
| 14 | [Prometheus Default Scrape Interval](./Screenshots/14%20Prometheus%20Default%20Scrape%20Interval.png) | Live config showing the 1m default |
| 15 | [Simulated Alerts Metrics](./Screenshots/15%20Simulated%20Alerts%20Metrics.png) | Pending deliveries above 50 and the firing alert |
| 16 | [Simulated Alerts Prometheus](./Screenshots/16%20Simulated%20Alerts%20Prometheus.png) | Alerts page after the simulation |
| 17 | [Simulated Alerts Grafana](./Screenshots/17%20Simulated%20Alerts%20Grafana.png) | Dashboard with pending deliveries at 50–100 |

---

## Q&A

**Q1: How does Prometheus get the metrics from the Python app?**
`start_http_server(8000)` exposes all metrics at `/metrics`. Prometheus sends an HTTP GET to every target listed in `scrape_configs` at each `scrape_interval`.

**Q2: What is the difference between a Gauge and a Summary?**
A Gauge is a single value that can go up or down (pending deliveries). A Summary records observations and exposes `_count` and `_sum`, so the average is `_sum / _count`.

**Q3: Why is `172.17.0.1` used as the target address?**
It is the Docker bridge gateway, the Docker host as seen from inside a container. Prometheus in a container reaches the app's published port `8000` through it, and Grafana reaches Prometheus on `9090` the same way.

**Q4: What does `for: 15s` do in an alert rule?**
The condition must stay true for 15 seconds before the alert goes from *pending* to *firing*. This avoids alerting on short spikes. It is checked at every `evaluation_interval`.

**Q5: What does the Jenkins pipeline add?**
It automates the whole setup: check Docker, collect the files, build the app image, run the app, Prometheus and Grafana, and verify they respond. The stack can be rebuilt with one click, as builds #2 and #3 did after the code and config changes.

---

## Result

Successfully built a **real-time delivery monitoring stack**:

* A Python app exposing delivery metrics on `/metrics`
* **Prometheus** scraping it and firing `HighPendingDeliveries` and `HighAverageDeliveryTime` alerts
* A **Grafana** dashboard with total, pending, on-the-way deliveries and average delivery time
* A **Jenkins pipeline** that builds and deploys the whole stack, run successfully 3 times

Raising pending deliveries to 50–100 was immediately visible in the metrics, the Prometheus alerts and the Grafana dashboard.
