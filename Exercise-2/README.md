# Kubernetes Exercise 2

## Objective

The objective of this exercise is to deploy a **Python Flask application** on a single-node Kubernetes cluster using Minikube, `kubectl` and a YAML manifest.

The Flask image is built directly inside Minikube's Docker daemon, deployed as a Kubernetes **Deployment**, and exposed through a **NodePort Service**.

---

## Prerequisites

* Windows 11 with WSL (Ubuntu)
* Docker Desktop
* Minikube
* kubectl

Minikube is configured to use the **Docker driver**.

---

## Project Files

| File | Description |
|------|-------------|
| [`app.py`](./app.py) | Flask application that returns `Hello from Flask on Kubernetes!` on port `15000` |
| [`Dockerfile`](./Dockerfile) | Builds the `flask-app` image from `python:3.8-slim` |
| [`flask-deployment.yaml`](./flask-deployment.yaml) | Kubernetes Deployment and NodePort Service for the Flask app |

---

## Steps Performed

### 1. Start Minikube

Started the local Kubernetes cluster:

```bash
minikube start
```

---

### 2. Create the Flask Application

Created [`app.py`](./app.py):

```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from Flask on Kubernetes!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=15000)
```

---

### 3. Create the Dockerfile

Created [`Dockerfile`](./Dockerfile):

```dockerfile
FROM python:3.8-slim
WORKDIR /app
COPY . /app
RUN pip install flask
CMD ["python", "app.py"]
```

---

### 4. Build the Docker Image with Minikube's Docker Daemon

Pointed the Docker CLI at Minikube's Docker daemon and built the image inside the cluster, so Kubernetes can use it without pulling from a registry:

```bash
minikube docker-env
eval $(minikube docker-env)
docker build -t flask-app .
```

---

### 5. Create the Kubernetes Deployment

Created [`flask-deployment.yaml`](./flask-deployment.yaml) with a Deployment for the Flask app:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flask-app
  template:
    metadata:
      labels:
        app: flask-app
    spec:
      containers:
      - name: flask-app
        image: flask-app:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 15000
```

`imagePullPolicy: Never` makes Kubernetes use the local `flask-app:latest` image built in Step 4 instead of pulling it from Docker Hub.

Applied the manifest:

```bash
kubectl apply -f flask-deployment.yaml
```

---

### 6. Check Deployment Status

```bash
kubectl get deployments
```

```
NAME        READY   UP-TO-DATE   AVAILABLE   AGE
flask-app   1/1     1            1           9s
```

The `flask-app` deployment is ready with `1/1` replicas available.

---

### 7. Verify the Pods Created by the Deployment

```bash
kubectl get pods -l app=flask-app
```

```
NAME                         READY   STATUS    RESTARTS   AGE
flask-app-6d58f88547-mw8k5   1/1     Running   0          19s
```

The Pod is in the `Running` state.

---

### 8. Describe the Deployment

```bash
kubectl describe deployment flask-app
```

```
Name:                   flask-app
Namespace:              default
CreationTimestamp:      Sat, 12 Sep 2026 14:51:42 +0000
Labels:                 <none>
Annotations:            deployment.kubernetes.io/revision: 1
Selector:               app=flask-app
Replicas:               1 desired | 1 updated | 1 total | 1 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  app=flask-app
  Containers:
   flask-app:
    Image:         flask-app:latest
    Port:          15000/TCP
    Host Port:     0/TCP
    Environment:   <none>
    Mounts:        <none>
  Volumes:         <none>
  Node-Selectors:  <none>
  Tolerations:     <none>
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
OldReplicaSets:  <none>
NewReplicaSet:   flask-app-6d58f88547 (1/1 replicas created)
Events:
  Type    Reason             Age   From                   Message
  ----    ------             ----  ----                   -------
  Normal  ScalingReplicaSet  29s   deployment-controller  Scaled up replica set flask-app-6d58f88547 from 0 to 1
```

---

### 9. View the Application Logs

```bash
kubectl logs flask-app-6d58f88547-mw8k5
```

```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:15000
 * Running on http://10.244.0.4:15000
Press CTRL+C to quit
```

The logs confirm that Flask is running inside the Pod and listening on port `15000`.

---

### 10. Check Services

```bash
kubectl get services
```

```
NAME         TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP   9m2s
```

Only the default `kubernetes` service exists. The Flask app is not reachable from the host at `http://127.0.0.1:15000` yet, because Minikube runs in its own environment and port `15000` is only exposed inside the cluster.

---

### 11. Add a NodePort Service

Updated [`flask-deployment.yaml`](./flask-deployment.yaml) by adding a Service section:

```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: flask-app-service
spec:
  selector:
    app: flask-app
  ports:
  - port: 15000
    targetPort: 15000
  type: NodePort
```

* **port** – the port exposed by the Kubernetes Service.
* **targetPort** – the port the Flask container is listening on.

Request flow: **External request → Service (port 15000) → Container (targetPort 15000)**

Applied the updated manifest:

```bash
kubectl apply -f flask-deployment.yaml
```

```
deployment.apps/flask-app unchanged
service/flask-app-service created
```

The Deployment was unchanged, and the new `flask-app-service` was created.

---

### 12. Access the Application

Got the service URL from Minikube:

```bash
minikube service flask-app-service --url
```

```
http://127.0.0.1:42091
❗  Because you are using a Docker driver on linux, the terminal needs to be open to run it.
```

Kept the terminal open (it holds the tunnel) and opened `http://127.0.0.1:42091` in the browser.

![Flask App in Browser](./Screenshots/Flask%20App%20in%20Browser.png)

The page displayed **Hello from Flask on Kubernetes!**, confirming that the application was accessible through the Kubernetes Service.

---

## Screenshots

### 1. Flask Application in the Browser

![Flask App in Browser](./Screenshots/Flask%20App%20in%20Browser.png)

> Shows the Flask application responding with `Hello from Flask on Kubernetes!` at `http://127.0.0.1:42091`, the URL returned by `minikube service flask-app-service --url`.

---

## Q&A

**Q1: What is the purpose of `minikube service flask-app-service --url`?**
It returns the URL for accessing `flask-app-service` running in Minikube.

**Q2: What is the difference between `port` and `targetPort` in a Service?**
`port` is the port exposed by the Service; `targetPort` is the port the container is listening on.

**Q3: Why is `imagePullPolicy: Never` used?**
So Kubernetes uses the locally built `flask-app:latest` image instead of trying to pull it from a registry.

**Q4: Why does the terminal need to stay open when using the Docker driver?**
Minikube keeps a tunnel to the service open from that terminal; closing it closes the tunnel.

**Q5: What is the role of `kubectl` in this setup?**
`kubectl` is the Kubernetes CLI used to deploy the application, inspect Deployments, Pods and Services, and read logs.

---

## Result

Successfully built a **Flask Docker image** inside Minikube, deployed it as a **Kubernetes Deployment** using a YAML manifest, exposed it through a **NodePort Service**, and accessed it from the browser.

The `Hello from Flask on Kubernetes!` response confirms that the Deployment and Service were working successfully.
