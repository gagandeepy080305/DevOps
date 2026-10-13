# Kubernetes Exercise 3

## Objective

The objective of this exercise is to scale a Flask application on a single-node Minikube cluster using a Kubernetes **ReplicaSet**.

The app simulates a **Flash Sale** checkout service. During a flash sale, traffic can spike from 100 to 10,000 requests per minute, so a single Pod is not enough. A ReplicaSet runs multiple identical Pods, replaces any Pod that fails, and can be scaled up or down as demand changes.

* Understand ReplicaSets and Pods
* Scale the Flask app
* Observe Pod distribution and self-healing

---

## Prerequisites

* macOS (Apple Silicon)
* Colima (Docker engine) and Docker CLI
* Minikube v1.39.0
* kubectl v1.37

Minikube is configured to use the **Docker driver** with the **Docker container runtime**, so `minikube docker-env` can be used to build images directly inside the cluster.

---

## Project Files

| File | Description |
|------|-------------|
| [`app.py`](./app.py) | Flash Sale Flask app with `/`, `/buy` and `/health` endpoints |
| [`Dockerfile`](./Dockerfile) | Builds the `flashsale:1.0` image and runs the app with Gunicorn on port `5000` |
| [`flashsale-replicaset.yaml`](./flashsale-replicaset.yaml) | ReplicaSet with 3 replicas and a ClusterIP Service on port `80` |

---

## Steps Performed

### 1. Create the Flash Sale Application

Created [`app.py`](./app.py):

```python
from flask import Flask, request
import socket, time, random

app = Flask(__name__)

@app.get("/")
def homepage():
    return {
        "message": "Welcome to Big Sale!",
        "pod": socket.gethostname(),
        "ts": time.time()
    }

@app.get("/buy")
def buy():
    # simulate a flash sale checkout
    item = random.choice(["Smartphone", "Shoes", "Headphones", "Laptop"])
    user = request.args.get("user", f"user{random.randint(1,1000)}")
    return {
        "status": "success",
        "item": item,
        "user": user,
        "served_by_pod": socket.gethostname(),
        "time": time.strftime("%H:%M:%S")
    }

@app.get("/health")
def health():
    return {"status": "healthy", "pod": socket.gethostname()}
```

* `/` – welcomes users to the Big Sale
* `/buy` – simulates a checkout; picks a random product and shows which Pod served the request (`?user=<name>` sets the user)
* `/health` – used by the readiness and liveness probes

---

### 2. Create the Dockerfile

Created [`Dockerfile`](./Dockerfile):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
RUN pip install --no-cache-dir flask gunicorn
CMD ["gunicorn","-b","0.0.0.0:5000","app:app","--workers","1","--threads","2"]
```

---

### 3. Clean Up and Start Minikube with a Single Node

Removed any previous cluster and started a fresh single-node cluster:

```bash
minikube stop
minikube delete
minikube start --nodes=1
```

```
* minikube v1.39.0 on Darwin 27.0.1 (arm64)
* Using the docker driver based on user configuration
* Starting "minikube" primary control-plane node in "minikube" cluster
...
* Enabled addons: storage-provisioner, default-storageclass
* Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
```

Checked the node:

```bash
kubectl get nodes
```

```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   10s   v1.37.0
```

![Minikube Start](./Screenshots/01%20Minikube%20Start.png)

---

### 4. Create the ReplicaSet

Created [`flashsale-replicaset.yaml`](./flashsale-replicaset.yaml) with a ReplicaSet of **3 replicas** and a ClusterIP Service:

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: flashsale-rs
  labels:
    app: flashsale
spec:
  replicas: 3  ## Number of replicas (copies of flashsale app) to run
  selector:
    matchLabels:
      app: flashsale
  template:
    metadata:
      labels:
        app: flashsale
    spec:
      containers:
      - name: flashsale-container
        image: flashsale:1.0
        imagePullPolicy: Never
        ports:
        - containerPort: 5000
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 2
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 10
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: flashsale-svc
spec:
  selector:
    app: flashsale
  ports:
  - name: http
    port: 80
    targetPort: 5000
  type: ClusterIP
```

* **readinessProbe** – a Pod only receives traffic once `/health` responds.
* **livenessProbe** – Kubernetes restarts the container if `/health` stops responding.
* **resources** – each Pod requests `100m` CPU / `128Mi` memory and is capped at `500m` / `256Mi`.
* `imagePullPolicy: Never` – uses the image built inside Minikube instead of pulling from Docker Hub.

---

### 5. Apply the ReplicaSet

```bash
kubectl apply -f flashsale-replicaset.yaml
```

```
replicaset.apps/flashsale-rs created
service/flashsale-svc created
```

Following the lab order, the ReplicaSet was applied **before** the image was built, so the Pods could not start yet:

```bash
kubectl get pods
```

```
NAME                 READY   STATUS              RESTARTS   AGE
flashsale-rs-kfv86   0/1     ErrImageNeverPull   0          7s
flashsale-rs-rnv5f   0/1     ErrImageNeverPull   0          7s
flashsale-rs-z6j47   0/1     ErrImageNeverPull   0          7s
```

`ErrImageNeverPull` means the image `flashsale:1.0` does not exist on the node and `imagePullPolicy: Never` prevents Kubernetes from downloading it.

---

### 6. Build the Image with Minikube's Docker Daemon

Pointed the Docker CLI at Minikube's Docker daemon and built the image:

```bash
minikube docker-env
eval $(minikube docker-env)
docker build -t flashsale:1.0 .
```

```
Step 1/5 : FROM python:3.11-slim
Step 2/5 : WORKDIR /app
Step 3/5 : COPY app.py .
Step 4/5 : RUN pip install --no-cache-dir flask gunicorn
Successfully installed blinker-1.9.0 click-8.5.0 flask-3.1.3 gunicorn-26.2.0 itsdangerous-2.2.0 jinja2-3.1.6 markupsafe-3.0.4 werkzeug-3.1.9
Step 5/5 : CMD ["gunicorn","-b","0.0.0.0:5000","app:app","--workers","1","--threads","2"]
Successfully built ecd5d157d2b8
Successfully tagged flashsale:1.0
```

![Apply ReplicaSet and Build Image](./Screenshots/02%20Apply%20ReplicaSet%20and%20Build%20Image.png)

---

### 7. Verify the Pods and ReplicaSet

Once the image was available, Kubernetes retried and all 3 Pods started:

```bash
kubectl get pods
```

```
NAME                 READY   STATUS    RESTARTS   AGE
flashsale-rs-kfv86   1/1     Running   0          29s
flashsale-rs-rnv5f   1/1     Running   0          29s
flashsale-rs-z6j47   1/1     Running   0          29s
```

```bash
kubectl get rs
```

```
NAME           DESIRED   CURRENT   READY   AGE
flashsale-rs   3         3         3       29s
```

---

### 8. Scale the ReplicaSet to 5 Replicas

Simulated the flash sale traffic spike by scaling out:

```bash
kubectl scale rs flashsale-rs --replicas=5
```

```
replicaset.apps/flashsale-rs scaled
```

---

### 9. Verify the Updated ReplicaSet and Pods

```bash
kubectl get rs
```

```
NAME           DESIRED   CURRENT   READY   AGE
flashsale-rs   5         5         5       42s
```

```bash
kubectl get pods
```

```
NAME                 READY   STATUS    RESTARTS   AGE
flashsale-rs-b9pvr   1/1     Running   0          6s
flashsale-rs-kfv86   1/1     Running   0          42s
flashsale-rs-lsps4   1/1     Running   0          6s
flashsale-rs-rnv5f   1/1     Running   0          42s
flashsale-rs-z6j47   1/1     Running   0          42s
```

Two new Pods (`b9pvr`, `lsps4`, age `6s`) were created to reach 5 replicas.

---

### 10. Delete One Pod

Simulated a Pod failure:

```bash
kubectl delete pod flashsale-rs-kfv86
```

```
pod "flashsale-rs-kfv86" deleted from default namespace
```

---

### 11. Verify Self-Healing and Pod Distribution

```bash
kubectl get pods
```

```
NAME                 READY   STATUS    RESTARTS   AGE
flashsale-rs-b9pvr   1/1     Running   0          13s
flashsale-rs-lsps4   1/1     Running   0          13s
flashsale-rs-r7mx8   1/1     Running   0          7s
flashsale-rs-rnv5f   1/1     Running   0          49s
flashsale-rs-z6j47   1/1     Running   0          49s
```

The ReplicaSet immediately created `flashsale-rs-r7mx8` to replace the deleted Pod, keeping the count at 5.

```bash
kubectl get pods -o wide
```

```
NAME                 READY   STATUS    RESTARTS   AGE   IP           NODE       NOMINATED NODE   READINESS GATES
flashsale-rs-b9pvr   1/1     Running   0          13s   10.244.0.6   minikube   <none>           <none>
flashsale-rs-lsps4   1/1     Running   0          13s   10.244.0.7   minikube   <none>           <none>
flashsale-rs-r7mx8   1/1     Running   0          7s    10.244.0.8   minikube   <none>           <none>
flashsale-rs-rnv5f   1/1     Running   0          49s   10.244.0.3   minikube   <none>           <none>
flashsale-rs-z6j47   1/1     Running   0          49s   10.244.0.5   minikube   <none>           <none>
```

All 5 Pods run on the single `minikube` node, each with its own IP.

![Scale and Self-Healing](./Screenshots/03%20Scale%20and%20Self-Healing.png)

---

### 12. Observe Load Distribution

Sent 10 `/buy` requests to the `flashsale-svc` Service from a temporary `curl` Pod inside the cluster:

```bash
kubectl run load-test --restart=Never --image=curlimages/curl -- sh -c 'for i in $(seq 1 10); do curl -s http://flashsale-svc/buy; echo; done'
kubectl logs load-test
```

```
{"item":"Shoes","served_by_pod":"flashsale-rs-lsps4","status":"success","time":"11:28:57","user":"user313"}
{"item":"Shoes","served_by_pod":"flashsale-rs-rnv5f","status":"success","time":"11:28:57","user":"user884"}
{"item":"Shoes","served_by_pod":"flashsale-rs-z6j47","status":"success","time":"11:28:57","user":"user592"}
{"item":"Smartphone","served_by_pod":"flashsale-rs-r7mx8","status":"success","time":"11:28:57","user":"user712"}
{"item":"Smartphone","served_by_pod":"flashsale-rs-r7mx8","status":"success","time":"11:28:57","user":"user87"}
{"item":"Laptop","served_by_pod":"flashsale-rs-lsps4","status":"success","time":"11:28:57","user":"user961"}
{"item":"Smartphone","served_by_pod":"flashsale-rs-lsps4","status":"success","time":"11:28:57","user":"user15"}
{"item":"Headphones","served_by_pod":"flashsale-rs-z6j47","status":"success","time":"11:28:57","user":"user895"}
{"item":"Shoes","served_by_pod":"flashsale-rs-b9pvr","status":"success","time":"11:28:57","user":"user139"}
{"item":"Shoes","served_by_pod":"flashsale-rs-r7mx8","status":"success","time":"11:28:57","user":"user100"}
```

The `served_by_pod` field shows that the Service spread the 10 requests across **all 5 Pods**:

| Pod | Requests served |
|-----|-----------------|
| flashsale-rs-lsps4 | 3 |
| flashsale-rs-r7mx8 | 3 |
| flashsale-rs-z6j47 | 2 |
| flashsale-rs-rnv5f | 1 |
| flashsale-rs-b9pvr | 1 |

![Load Distribution](./Screenshots/04%20Load%20Distribution.png)

---

### 13. Describe the ReplicaSet

```bash
kubectl describe rs flashsale-rs
```

```
Name:         flashsale-rs
Namespace:    default
Selector:     app=flashsale
Labels:       app=flashsale
Replicas:     5 current / 5 desired
Pods Status:  5 Running / 0 Waiting / 0 Succeeded / 0 Failed
...
Events:
  Type    Reason            Age   From                   Message
  ----    ------            ----  ----                   -------
  Normal  SuccessfulCreate  84s   replicaset-controller  Created pod: flashsale-rs-z6j47
  Normal  SuccessfulCreate  84s   replicaset-controller  Created pod: flashsale-rs-rnv5f
  Normal  SuccessfulCreate  84s   replicaset-controller  Created pod: flashsale-rs-kfv86
  Normal  SuccessfulCreate  48s   replicaset-controller  Created pod: flashsale-rs-b9pvr
  Normal  SuccessfulCreate  48s   replicaset-controller  Created pod: flashsale-rs-lsps4
  Normal  SuccessfulCreate  42s   replicaset-controller  Created pod: flashsale-rs-r7mx8
```

The events show the full history: 3 initial Pods, 2 added by scaling, and 1 replacement after the deletion.

![Describe ReplicaSet](./Screenshots/05%20Describe%20ReplicaSet.png)

---

### 14. Access the Application

Forwarded the Service to the local machine and opened the endpoints in the browser:

```bash
kubectl port-forward svc/flashsale-svc 8080:80
```

* `http://localhost:8080/` → `{"message": "Welcome to Big Sale!", "pod": "flashsale-rs-z6j47", ...}`
* `http://localhost:8080/buy?user=gagan` → `{"status": "success", "user": "gagan", "served_by_pod": "flashsale-rs-z6j47", ...}`
* `http://localhost:8080/health` → `{"status": "healthy", ...}`

`kubectl port-forward` connects to a single Pod, so all browser requests show the same Pod. The load-distribution test in Step 12 goes through the Service's load balancing instead.

![Flash Sale Home](./Screenshots/06%20Flash%20Sale%20Home.png)

---

## Screenshots

### 1. Minikube Start

![Minikube Start](./Screenshots/01%20Minikube%20Start.png)

> Shows `minikube start --nodes=1` creating a single-node cluster and `kubectl get nodes` showing the `minikube` node as `Ready`.

---

### 2. Apply ReplicaSet and Build Image

![Apply ReplicaSet and Build Image](./Screenshots/02%20Apply%20ReplicaSet%20and%20Build%20Image.png)

> Shows the ReplicaSet being applied, the Pods in `ErrImageNeverPull` before the image existed, the image being built inside Minikube with `docker build -t flashsale:1.0 .`, and all 3 Pods `Running` afterwards.

---

### 3. Scale and Self-Healing

![Scale and Self-Healing](./Screenshots/03%20Scale%20and%20Self-Healing.png)

> Shows `kubectl scale rs flashsale-rs --replicas=5` adding 2 Pods, deleting `flashsale-rs-kfv86`, the ReplicaSet replacing it with `flashsale-rs-r7mx8`, and all 5 Pods on the `minikube` node.

---

### 4. Load Distribution

![Load Distribution](./Screenshots/04%20Load%20Distribution.png)

> Shows 10 `/buy` requests sent through `flashsale-svc`, served by all 5 Pods.

---

### 5. Describe ReplicaSet

![Describe ReplicaSet](./Screenshots/05%20Describe%20ReplicaSet.png)

> Shows the ReplicaSet details (5 current / 5 desired, probes, resource limits) and the `SuccessfulCreate` events for every Pod.

---

### 6. Flash Sale Home Page

![Flash Sale Home](./Screenshots/06%20Flash%20Sale%20Home.png)

> `http://localhost:8080/` returning `Welcome to Big Sale!` with the Pod name.

---

### 7. Flash Sale Buy Endpoint

![Flash Sale Buy](./Screenshots/07%20Flash%20Sale%20Buy.png)

> `http://localhost:8080/buy?user=gagan` returning a successful checkout with `served_by_pod`.

---

### 8. Flash Sale Health Endpoint

![Flash Sale Health](./Screenshots/08%20Flash%20Sale%20Health.png)

> `http://localhost:8080/health` returning `healthy`. This is the endpoint used by the readiness and liveness probes.

---

## Q&A

**Q1: What is the initial number of replicas in the ReplicaSet?**
3

**Q2: How many Pods are running after applying the ReplicaSet configuration?**
3 (once the image was built).

**Q3: What happens when you scale the ReplicaSet to 5 replicas?**
Kubernetes creates 2 additional Pods (`flashsale-rs-b9pvr` and `flashsale-rs-lsps4`) to reach the desired count of 5.

**Q4: What happens when you delete one Pod?**
The ReplicaSet automatically creates a replacement Pod (`flashsale-rs-r7mx8`), keeping 5 replicas running.

**Q5: How does Kubernetes maintain the desired number of replicas?**
The ReplicaSet controller continuously compares the number of running Pods with the desired count and creates or deletes Pods to close the gap.

**Q6: How many nodes are running?**
1 (`minikube`).

**Q7: Where are the Pods running with respect to nodes?**
All 5 Pods run on the single `minikube` node.

---

## Key Observations

* **Pod distribution** – each Pod is an identical worker; scaling creates clones of the app.
* **Resiliency** – when a Pod was deleted, the ReplicaSet replaced it within seconds.
* **Load balancing** – the Service spread requests across all 5 Pods.
* **Efficiency** – Pods can be added when demand spikes and removed when it drops, instead of over-provisioning servers.

---

## Result

Successfully built the **Flash Sale Flask image** inside Minikube, deployed it as a **Kubernetes ReplicaSet** with 3 replicas, **scaled it to 5**, and confirmed **self-healing** when a Pod was deleted.

The load test confirmed that the **ClusterIP Service** distributes requests across all Pods, and the app was reachable in the browser through `kubectl port-forward`.
