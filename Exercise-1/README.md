# Kubernetes Exercise 1

## Objective

The objective of this exercise is to deploy and access a containerized application using Kubernetes and Minikube.

In this exercise, an **Nginx container** is used to simulate a web application that needs to be deployed on Kubernetes.

---

## Prerequisites

* Windows 11
* Docker Desktop
* Minikube
* kubectl

Minikube is configured to use the **Docker driver**.

---

## Steps Performed

### 1. Start Minikube

Started the local Kubernetes cluster using the Docker driver:

```bash
minikube start
```

The first attempt showed a Docker API connection error because Docker Desktop's Linux engine was not available at that moment. After Docker was available, `minikube start` completed successfully and configured `kubectl` to use the `minikube` cluster.

![Minikube Start](./Screenshots/Screenshot%2012-09-2026%2006_07_26%20PM.png)

---

### 2. Create the Kubernetes Pod

Created an Nginx Pod using:

```bash
kubectl run hello-k8s --image=nginx --port=80
```

The command created the Pod named `hello-k8s`.

![Kubernetes Pod Creation](./Screenshots/Administrator_%20Command%20Prompt%2012-09-2026%2006_09_30%20PM.png)

---

### 3. Verify the Pod

Checked the status of the Pod:

```bash
kubectl get pods
```

The screenshot captures the Pod while it was in the `ContainerCreating` state during startup.

![Pod Status](./Screenshots/Administrator_%20Command%20Prompt%2012-09-2026%2006_09_30%20PM.png)

---

### 4. Expose the Pod

Exposed the Pod using a NodePort service:

```bash
kubectl expose pod hello-k8s --type=NodePort --port=80
```

The service was created successfully and assigned a NodePort.

![Kubernetes Service](./Screenshots/Administrator_%20Command%20Prompt%20-%20minikube%20%20service%20hello-k8s%2012-09-2026%2006_10_16%20PM.png)

---

### 5. Access the Application

Opened the deployed Nginx application using:

```bash
minikube service hello-k8s
```

Minikube created a tunnel to the service and opened the application in the browser.

![Nginx Welcome Page](./Screenshots/Welcome%20to%20nginx!%20-%20Profile%201%20-%20Microsoft%E2%80%8B%20Edge%2012-09-2026%2006_10_10%20PM.png)

The default **Welcome to nginx!** page was successfully displayed, confirming that the application was accessible through the Kubernetes Service.

---

## Screenshots

### 1. Minikube Setup (Install + First Start Attempt)

![Minikube Setup](./Screenshots/Screenshot%2012-09-2026%2006_07_26%20PM.png)

> Shows Chocolatey installing Minikube, the first failed `minikube start` due to Docker not running, and the successful second `minikube start` with the cluster fully initialized.

---

### 2. Pod Creation and Status

![Minikube Cluster and Pod](./Screenshots/Administrator_%20Command%20Prompt%2012-09-2026%2006_09_30%20PM.png)

> Shows `minikube start` completing, `kubectl run hello-k8s --image=nginx --port=80` creating the pod, and `kubectl get pods` showing the pod in `ContainerCreating` state.

---

### 3. Service Exposure and Tunnel

![Kubernetes Service](./Screenshots/Administrator_%20Command%20Prompt%20-%20minikube%20%20service%20hello-k8s%2012-09-2026%2006_10_16%20PM.png)

> Shows `kubectl expose pod hello-k8s --type=NodePort --port=80` creating the service, followed by `minikube service hello-k8s` opening a tunnel to `http://127.0.0.1:56212`.

---

### 4. Nginx Welcome Page

![Nginx Welcome Page](./Screenshots/Welcome%20to%20nginx!%20-%20Profile%201%20-%20Microsoft%E2%80%8B%20Edge%2012-09-2026%2006_10_10%20PM.png)

> Confirms the Nginx application is accessible through the browser via the Minikube tunnel at `http://127.0.0.1:56212`.

---

## Result

Successfully created an **Nginx container as a Kubernetes Pod** using Minikube, exposed the Pod through a **NodePort Kubernetes Service**, and accessed the application through a web browser.

The final Nginx welcome page confirms that the Kubernetes deployment and service access were working successfully.
