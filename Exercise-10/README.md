# Kubernetes Exercise 10

## Objective

The objective of this exercise is to deploy **multiple applications** on a **multi-node Kubernetes cluster** (Minikube), with replicas spread across nodes for high availability.

**Storyboard:** an e-commerce platform with two services:

| Service | App | Replicas |
|---------|-----|----------|
| **Product Catalog** (AppA) | Lists available products | 2 |
| **Shopping Cart** (AppB) | View and add items to a cart | 3 |

Each replica must run on a **different node**, so that if one node fails, customers can still browse products and use the cart.

---

## Prerequisites

* macOS (Apple Silicon)
* Colima (Docker engine), resized to **6 CPUs / 10 GB RAM** for three Minikube nodes
* Minikube v1.39.0 and kubectl

---

## Project Files

| File | Description |
|------|-------------|
| [`product_catalog.py`](./product_catalog.py) | Flask app: `GET /products` |
| [`shopping_cart.py`](./shopping_cart.py) | Flask app: `GET /cart` and `POST /cart` (in-memory cart) |
| [`Dockerfile.product`](./Dockerfile.product) | Image `product-catalog:latest` |
| [`Dockerfile.shopping`](./Dockerfile.shopping) | Image `shopping-cart:latest` |
| [`product_catalog_deployment.yaml`](./product_catalog_deployment.yaml) | Deployment, 2 replicas, pod anti-affinity |
| [`shopping_cart_deployment.yaml`](./shopping_cart_deployment.yaml) | Deployment, 3 replicas, pod anti-affinity |
| [`product_catalog_service.yaml`](./product_catalog_service.yaml) | NodePort Service for Product Catalog |
| [`shopping_cart_service.yaml`](./shopping_cart_service.yaml) | NodePort Service for Shopping Cart |

---

## Changes from the Lab Instructions

| Lab instruction | What was done instead | Why |
|-----------------|-----------------------|-----|
| `shopping_cart_deployment.yaml` uses `namespace: devops-exercise` | Changed to **`namespace: default`** | The namespace is never created, so `kubectl apply` fails (see [Step 6](#6-deploy-the-applications)). Creating it would not help either: the `shopping-cart-service` is in `default`, and a Service only selects pods in its own namespace. The lab's expected output also shows the cart pods in `default`. |
| `minikube service <name>` (opens the browser) | `minikube service <name> --url` | Prints the URL without opening a browser. On macOS with the Docker driver, the tunnel stays open in the background either way. |
| — | Added a **node failure test** and a **per-replica cart check** | Tests the lab's high-availability claim, and shows a side-effect of keeping the cart in memory. |

---

## Steps Performed

### 1. Clean Up and Start a 3-Node Cluster

Removed the old single-node cluster (from Exercise 3) and created a 3-node cluster in the profile `devops-multinode`:

```bash
minikube stop
minikube delete
minikube start --nodes 3 -p devops-multinode --force
```

```
* [devops-multinode] minikube v1.39.0 on Darwin 27.0.1 (arm64)
! minikube skips various validations when --force is supplied; this may lead to unexpected behavior
* Starting "devops-multinode" primary control-plane node in "devops-multinode" cluster
* Starting "devops-multinode-m02" worker node in "devops-multinode" cluster
* Starting "devops-multinode-m03" worker node in "devops-multinode" cluster
* Done! kubectl is now configured to use "devops-multinode" cluster and "default" namespace by default
```

```bash
kubectl get nodes -o wide
```

```
NAME                   STATUS  ROLES           AGE    VERSION   INTERNAL-IP    CONTAINER-RUNTIME
devops-multinode       Ready   control-plane   43s    v1.37.0   192.168.49.2   docker://29.7.2
devops-multinode-m02   Ready   <none>          30s    v1.37.0   192.168.49.3   docker://29.7.2
devops-multinode-m03   Ready   <none>          21s    v1.37.0   192.168.49.4   docker://29.7.2
```

Three nodes: one control-plane and two workers.

![Start Multi-Node Cluster](./Screenshots/01%20Start%20Multi-Node%20Cluster.png)

---

### 2. Enable the Registry Add-on

```bash
minikube -p devops-multinode addons enable registry
```

```
│    Registry addon with docker driver uses port 32770 please use that instead of default port 5000    │
  - Using image registry.k8s.io/minikube/kube-registry-proxy:v0.0.11
  - Using image docker.io/registry:3
* Verifying registry addon...
* The 'registry' addon is enabled
```

![Enable Registry Addon](./Screenshots/02%20Enable%20Registry%20Addon.png)

---

### 3. Create the Applications

[`product_catalog.py`](./product_catalog.py):

```python
from flask import Flask, jsonify

app = Flask(__name__)

products = [
    {"id": 1, "name": "Laptop", "price": 1200},
    {"id": 2, "name": "Phone", "price": 800},
    {"id": 3, "name": "Headphones", "price": 150},
]

@app.route("/products", methods=["GET"])
def get_products():
    return jsonify(products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
```

[`shopping_cart.py`](./shopping_cart.py):

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

cart = []

@app.route("/cart", methods=["GET"])
def get_cart():
    return jsonify(cart)

@app.route("/cart", methods=["POST"])
def add_to_cart():
    item = request.json
    cart.append(item)
    return jsonify(cart), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
```

---

### 4. Build the Docker Images

```bash
docker build -t product-catalog:latest -f Dockerfile.product .
docker build -t shopping-cart:latest -f Dockerfile.shopping .
```

```
Successfully tagged product-catalog:latest
Successfully tagged shopping-cart:latest

IMAGE                    ID             DISK USAGE   CONTENT SIZE
product-catalog:latest   5c2618d72584        228MB           50MB
shopping-cart:latest     9b61ccb4bc55        228MB           50MB
```

![Build Docker Images](./Screenshots/03%20Build%20Docker%20Images.png)

---

### 5. Load the Images into the Cluster

In a multi-node cluster, `eval $(minikube docker-env)` only points at one node. `minikube image load` copies the image to **every** node:

```bash
minikube -p devops-multinode image load product-catalog:latest
minikube -p devops-multinode image load shopping-cart:latest
```

Verified on each node:

```bash
minikube -p devops-multinode ssh -n devops-multinode     -- docker images
minikube -p devops-multinode ssh -n devops-multinode-m02 -- docker images
minikube -p devops-multinode ssh -n devops-multinode-m03 -- docker images
```

All three nodes list `product-catalog:latest` and `shopping-cart:latest`. This is required because the Deployments use `imagePullPolicy: Never`.

![Load Images on All Nodes](./Screenshots/04%20Load%20Images%20on%20All%20Nodes.png)

---

### 6. Deploy the Applications

Both Deployments use a **required pod anti-affinity** rule on `kubernetes.io/hostname`. This means *never put two pods of this app on the same node*:

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          app: shopping-cart
      topologyKey: "kubernetes.io/hostname"
```

Applied the manifests as written in the lab:

```bash
kubectl apply -f product_catalog_deployment.yaml
kubectl apply -f shopping_cart_deployment.yaml
```

```
deployment.apps/product-catalog created
Error from server (NotFound): error when creating "shopping_cart_deployment.yaml": namespaces "devops-exercise" not found
```

Changed the shopping cart's namespace to `default` (where its Service is) and applied again, together with both Services:

```bash
kubectl apply -f shopping_cart_deployment.yaml
kubectl apply -f product_catalog_service.yaml
kubectl apply -f shopping_cart_service.yaml
```

```
deployment.apps/shopping-cart created
service/product-catalog-service created
service/shopping-cart-service created
```

![Namespace Error and Fix](./Screenshots/05%20Namespace%20Error%20and%20Fix.png)

---

### 7. Verify Deployment and Distribution

```bash
kubectl get pods -o wide
```

```
NAME                             READY   STATUS    RESTARTS   AGE   IP           NODE
product-catalog-7cb85d4f-tfzx8   1/1     Running   0          14s   10.244.1.3   devops-multinode-m02
product-catalog-7cb85d4f-zxlvq   1/1     Running   0          14s   10.244.2.4   devops-multinode-m03
shopping-cart-6858b5f797-6kb4s   1/1     Running   0          6s    10.244.2.5   devops-multinode-m03
shopping-cart-6858b5f797-8tmq6   1/1     Running   0          6s    10.244.1.4   devops-multinode-m02
shopping-cart-6858b5f797-xp4wm   1/1     Running   0          6s    10.244.0.4   devops-multinode
```

| App | Replicas | Nodes |
|-----|----------|-------|
| product-catalog | 2/2 | `m02`, `m03` |
| shopping-cart | 3/3 | `devops-multinode`, `m02`, `m03` |

Every replica of each app is on a **different node**, exactly as the anti-affinity rule requires.

```
NAME                      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)
product-catalog-service   NodePort    10.106.47.253   <none>        80:30406/TCP
shopping-cart-service     NodePort    10.107.74.235   <none>        80:30448/TCP
```

![Pods Distributed Across Nodes](./Screenshots/06%20Pods%20Distributed%20Across%20Nodes.png)

---

### 8. Access the Services

```bash
minikube -p devops-multinode service product-catalog-service --url
minikube -p devops-multinode service shopping-cart-service --url
```

```
http://127.0.0.1:59032
! Because you are using a Docker driver on darwin, the terminal needs to be open to run it.
http://127.0.0.1:59033
! Because you are using a Docker driver on darwin, the terminal needs to be open to run it.
```

* Product Catalog → `http://127.0.0.1:59032`
* Shopping Cart → `http://127.0.0.1:59033`

---

### 9. Test with curl

```bash
curl http://127.0.0.1:59032/products
```

```json
[{"id":1,"name":"Laptop","price":1200},{"id":2,"name":"Phone","price":800},{"id":3,"name":"Headphones","price":150}]
```

```bash
curl http://127.0.0.1:59033/cart
```

```json
[]
```

```bash
curl -X POST http://127.0.0.1:59033/cart -H "Content-Type: application/json" -d '{"id": 1, "name": "Laptop", "quantity": 1}'
```

```json
[{"id":1,"name":"Laptop","quantity":1}]
```

All three responses match the lab's expected output.

![Service URLs and curl Tests](./Screenshots/07%20Service%20URLs%20and%20curl%20Tests.png)

![Product Catalog in Browser](./Screenshots/08%20Product%20Catalog%20in%20Browser.png)

![Shopping Cart in Browser](./Screenshots/09%20Shopping%20Cart%20in%20Browser.png)

---

### 10. Observation: Each Cart Replica Has Its Own Cart

After the POST, six `GET /cart` requests all returned `[]`. Reading the cart **inside each pod** showed why:

```
pod/shopping-cart-6858b5f797-6kb4s (devops-multinode-m03): []
pod/shopping-cart-6858b5f797-8tmq6 (devops-multinode-m02): [{"id":1,"name":"Laptop","quantity":1}]
pod/shopping-cart-6858b5f797-xp4wm (devops-multinode): []
```

`shopping_cart.py` keeps the cart in a Python list **in memory**, so each replica has its own separate cart. The POST was handled by the pod on `m02`, and the Service sends each request to any of the 3 pods. Over 20 more requests:

```
  11 []
   9 [{"id":1,"name":"Laptop","quantity":1}]
```

In a real system the cart would be stored in a shared database or cache (e.g. Redis, as in [Exercise 4](../Exercise-4)), so every replica sees the same cart.

![Cart State per Replica](./Screenshots/10%20Cart%20State%20per%20Replica.png)

---

### 11. Node Failure Test

Tested the use case directly: *"even if one node fails, the services remain available."* Stopped worker node `m03`:

```bash
minikube -p devops-multinode node stop devops-multinode-m03
kubectl get nodes
```

```
NAME                   STATUS     ROLES           AGE     VERSION
devops-multinode       Ready      control-plane   4m30s   v1.37.0
devops-multinode-m02   Ready      <none>          4m17s   v1.37.0
devops-multinode-m03   NotReady   <none>          4m8s    v1.37.0
```

With `m03` down, both services kept answering. HTTP status codes of 10 requests each:

```bash
for i in $(seq 1 10); do curl -s -o /dev/null -w '%{http_code} ' http://127.0.0.1:59032/products; done
for i in $(seq 1 10); do curl -s -o /dev/null -w '%{http_code} ' http://127.0.0.1:59033/cart; done
```

```
200 200 200 200 200 200 200 200 200 200
200 200 200 200 200 200 200 200 200 200
```

**20/20 requests succeeded.** The remaining replicas on the other nodes served all traffic.

![Node Failure Services Still Available](./Screenshots/11%20Node%20Failure%20Services%20Still%20Available.png)

About 5 minutes later, Kubernetes evicted the pods from the unreachable node and created replacements:

```
NAME                             READY  STATUS       NODE
product-catalog-7cb85d4f-rt6p4   1/1    Running      devops-multinode       <- replacement
product-catalog-7cb85d4f-tfzx8   1/1    Running      devops-multinode-m02
product-catalog-7cb85d4f-zxlvq   1/1    Terminating  devops-multinode-m03
shopping-cart-6858b5f797-6kb4s   1/1    Terminating  devops-multinode-m03
shopping-cart-6858b5f797-8tmq6   1/1    Running      devops-multinode-m02
shopping-cart-6858b5f797-g9f9d   0/1    Pending      <none>                 <- replacement
shopping-cart-6858b5f797-xp4wm   1/1    Running      devops-multinode
```

```
Warning  FailedScheduling  default-scheduler  0/3 nodes are available: 1 node(s) had untolerated taint(s),
         2 node(s) didn't match pod anti-affinity rules.
```

* **product-catalog** was back to 2 running pods. The replacement went to the control-plane node, which had no product-catalog pod.
* **shopping-cart** could not place its 3rd pod. Both healthy nodes already run a cart pod, and the **required** anti-affinity rule forbids a second one on the same node. Using `preferredDuringSchedulingIgnoredDuringExecution` instead would allow doubling up when nodes are lost.

![Pods Rescheduled After Node Failure](./Screenshots/12%20Pods%20Rescheduled%20After%20Node%20Failure.png)

Restarted the node:

```bash
minikube -p devops-multinode node start devops-multinode-m03
```

The Pending cart pod was scheduled on `m03` as soon as it was Ready, and the cluster was back to 2 + 3 running pods:

```
NAME                             READY  STATUS   NODE
product-catalog-7cb85d4f-rt6p4   1/1    Running  devops-multinode
product-catalog-7cb85d4f-tfzx8   1/1    Running  devops-multinode-m02
shopping-cart-6858b5f797-8tmq6   1/1    Running  devops-multinode-m02
shopping-cart-6858b5f797-g9f9d   1/1    Running  devops-multinode-m03
shopping-cart-6858b5f797-xp4wm   1/1    Running  devops-multinode
```

![Node Restarted All Pods Running](./Screenshots/13%20Node%20Restarted%20All%20Pods%20Running.png)

---

## Screenshots

| # | Screenshot | Shows |
|---|-----------|-------|
| 1 | [Start Multi-Node Cluster](./Screenshots/01%20Start%20Multi-Node%20Cluster.png) | Clean-up, `minikube start --nodes 3`, 3 Ready nodes |
| 2 | [Enable Registry Addon](./Screenshots/02%20Enable%20Registry%20Addon.png) | Registry add-on enabled |
| 3 | [Build Docker Images](./Screenshots/03%20Build%20Docker%20Images.png) | Both images built |
| 4 | [Load Images on All Nodes](./Screenshots/04%20Load%20Images%20on%20All%20Nodes.png) | `minikube image load` and images present on all 3 nodes |
| 5 | [Namespace Error and Fix](./Screenshots/05%20Namespace%20Error%20and%20Fix.png) | `devops-exercise` not found, then applied in `default` |
| 6 | [Pods Distributed Across Nodes](./Screenshots/06%20Pods%20Distributed%20Across%20Nodes.png) | 2 + 3 pods, each on a different node; Services |
| 7 | [Service URLs and curl Tests](./Screenshots/07%20Service%20URLs%20and%20curl%20Tests.png) | Service URLs, `GET /products`, `GET /cart`, `POST /cart` |
| 8 | [Product Catalog in Browser](./Screenshots/08%20Product%20Catalog%20in%20Browser.png) | `/products` in the browser |
| 9 | [Shopping Cart in Browser](./Screenshots/09%20Shopping%20Cart%20in%20Browser.png) | `/cart` in the browser |
| 10 | [Cart State per Replica](./Screenshots/10%20Cart%20State%20per%20Replica.png) | Each replica's own in-memory cart |
| 11 | [Node Failure Services Still Available](./Screenshots/11%20Node%20Failure%20Services%20Still%20Available.png) | `m03` stopped, 20/20 requests OK |
| 12 | [Pods Rescheduled After Node Failure](./Screenshots/12%20Pods%20Rescheduled%20After%20Node%20Failure.png) | Product pod rescheduled; cart pod Pending (anti-affinity) |
| 13 | [Node Restarted All Pods Running](./Screenshots/13%20Node%20Restarted%20All%20Pods%20Running.png) | `m03` back, all 5 pods running |

---

## Q&A

**Q1: Why use multiple nodes and replicas?**
For high availability. If a node fails, replicas on other nodes keep serving. With `m03` stopped, both services still answered 20/20 requests.

**Q2: What does pod anti-affinity do here?**
`requiredDuringSchedulingIgnoredDuringExecution` with `topologyKey: kubernetes.io/hostname` forbids two pods of the same app on one node. That forces the replicas onto different nodes.

**Q3: What is the downside of a *required* anti-affinity rule?**
If there are fewer healthy nodes than replicas, the extra pods stay **Pending**. This happened to the 3rd shopping-cart pod while `m03` was down. A *preferred* rule spreads pods when possible, but still schedules them when it isn't.

**Q4: Why `minikube image load` instead of `minikube docker-env`?**
`docker-env` points at a single node's Docker daemon, so the image would exist on that node only. `image load` copies it to all nodes. Every node needs it because of `imagePullPolicy: Never`.

**Q5: Why did `GET /cart` sometimes return an empty cart after adding an item?**
Each replica keeps its own cart in memory, and the Service load-balances requests across replicas. Shared state must live outside the pods, for example in a database or Redis.

---

## Result

Successfully created a **3-node Minikube cluster** and deployed the **Product Catalog** (2 replicas) and **Shopping Cart** (3 replicas) services, with pod anti-affinity placing every replica on a different node.

Both services were exposed with NodePort Services and tested with `curl`. When a worker node was stopped, both services **stayed available**. The product catalog was rescheduled automatically, and the shopping cart recovered fully once the node returned.
