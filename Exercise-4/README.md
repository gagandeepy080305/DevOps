# Docker Exercise 4

## Objective

The objective of this exercise is to understand **Docker networking** by connecting multiple containers on a user-defined **bridge network**.

The application is made of three containers:

* A **Python Flask** web server (container 1)
* A **MySQL** database (container 2)
* A **Redis** cache (container 3)

All three are attached to the same network, so they can reach each other by **container name**.

---

## Prerequisites

* macOS (Apple Silicon)
* Colima (Docker engine) and Docker CLI

---

## Project Files

| File | Description |
|------|-------------|
| [`app.py`](./app.py) | Flask REST API with an `/about` endpoint on port `5001` |
| [`requirements.txt`](./requirements.txt) | Python dependencies (`Flask==2.0.1`, `Werkzeug==2.0.3`) |
| [`Dockerfile`](./Dockerfile) | Builds the `flask-api` image from `python:3.9-slim` |

---

## Changes from the Lab Instructions

Running the lab exactly as written fails in three places, so these fixes were made:

| Problem | Fix |
|---------|-----|
| `mysql:latest` exits immediately without a root password option (see [Step 5](#5-mysql-needs-a-password-option)) | Added `-e MYSQL_RANDOM_ROOT_PASSWORD=yes` to the MySQL `docker run` |
| `app.run(port=5001)` only listens on `127.0.0.1` inside the container, so `-p 5001:5001` cannot reach it | Changed to `app.run(debug=True, host='0.0.0.0', port=5001)` |
| `Flask==2.0.1` crashes with newer Werkzeug versions (`ImportError: cannot import name 'url_quote'`) | Pinned `Werkzeug==2.0.3` in `requirements.txt` |

The `python:3.9-slim` image also does not include `ping`, so the Dockerfile installs `iputils-ping` for the connectivity test.

---

## Steps Performed

### 1. Create a Bridge Network

```bash
docker network create --driver bridge my-bridge-net
```

```
2ef2c14bbee1e0667512bbddfb56527447002ff3b8dd911206cb43d6a5f50c45
```

---

### 2. Verify the Network

```bash
docker network ls
```

```
NETWORK ID     NAME            DRIVER    SCOPE
1ae26515c1ee   bridge          bridge    local
2408b65655a6   host            host      local
d4fef7af0be6   minikube        bridge    local
2ef2c14bbee1   my-bridge-net   bridge    local
9e96f71e999e   none            null      local
```

`my-bridge-net` is listed with the `bridge` driver. (The `minikube` network is left over from Exercise 3.)

---

### 3. Inspect the Network

```bash
docker network inspect my-bridge-net
```

```
[
    {
        "Name": "my-bridge-net",
        "Id": "2ef2c14bbee1e0667512bbddfb56527447002ff3b8dd911206cb43d6a5f50c45",
        "Created": "2026-10-13T17:08:42.519972566+05:30",
        "Scope": "local",
        "Driver": "bridge",
        "EnableIPv4": true,
        "EnableIPv6": false,
        "IPAM": {
            "Driver": "default",
            "Options": {},
            "Config": [
                {
                    "Subnet": "172.18.0.0/16",
                    "Gateway": "172.18.0.1"
                }
            ]
        },
        "Internal": false,
        "Attachable": false,
        "Ingress": false,
        ...
        "Containers": {},
        ...
    }
]
```

The network has the subnet `172.18.0.0/16` with gateway `172.18.0.1`, and no containers attached yet.

![Create and Inspect Network](./Screenshots/01%20Create%20and%20Inspect%20Network.png)

---

### 4. Build the Flask Image

Created [`app.py`](./app.py):

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/about', methods=['GET'])
def about():
    return jsonify({
        "name": "Simple REST API",
        "version": "1.0",
        "description": "This is a simple REST API built with Flask."
    })

if __name__ == '__main__':
    # host='0.0.0.0' so the app is reachable from outside the container (-p 5001:5001)
    app.run(debug=True, host='0.0.0.0', port=5001)
```

Created [`requirements.txt`](./requirements.txt):

```
Flask==2.0.1
Werkzeug==2.0.3
```

Created [`Dockerfile`](./Dockerfile):

```dockerfile
# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Install ping so we can test connectivity between containers
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and app code to the container
COPY requirements.txt .
COPY app.py .

# Install Flask (and any other dependencies you might have)
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 5001

# Define the command to run the application
CMD ["python", "app.py"]
```

Built the image:

```bash
docker build -t flask-api .
```

```
Step 1/8 : FROM python:3.9-slim
Step 2/8 : RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping && rm -rf /var/lib/apt/lists/*
Step 3/8 : WORKDIR /app
Step 4/8 : COPY requirements.txt .
Step 5/8 : COPY app.py .
Step 6/8 : RUN pip install --no-cache-dir -r requirements.txt
Successfully installed Flask-2.0.1 Jinja2-3.1.6 MarkupSafe-3.0.4 Werkzeug-2.0.3 click-8.1.8 itsdangerous-2.2.0
Step 7/8 : EXPOSE 5001
Step 8/8 : CMD ["python", "app.py"]
Successfully built d3d0ff467bb5
Successfully tagged flask-api:latest
```

![Build Flask Image](./Screenshots/02%20Build%20Flask%20Image.png)

---

### 5. MySQL Needs a Password Option

Running MySQL exactly as in the lab instructions:

```bash
docker run -d --name mysql-test --net=my-bridge-net mysql:latest
docker ps -a --filter name=mysql-test
docker logs mysql-test
```

```
NAMES        STATUS
mysql-test   Exited (1) 5 seconds ago

[ERROR] [Entrypoint]: Database is uninitialized and password option is not specified
    You need to specify one of the following as an environment variable:
    - MYSQL_ROOT_PASSWORD
    - MYSQL_ALLOW_EMPTY_PASSWORD
    - MYSQL_RANDOM_ROOT_PASSWORD
```

The container exits straight away, so it would not be reachable from the other containers. The test container was removed, and the real MySQL container is started with `MYSQL_RANDOM_ROOT_PASSWORD=yes`, which generates a random root password. That way no password is stored in this repo.

![MySQL Without Password](./Screenshots/03%20MySQL%20Without%20Password.png)

---

### 6. Launch the Containers

Started all three containers on `my-bridge-net` in detached mode (`-d`):

```bash
docker run -d --name mysql --net=my-bridge-net -e MYSQL_RANDOM_ROOT_PASSWORD=yes mysql:latest
docker run -d --name redis --net=my-bridge-net redis:latest
docker run -d --name flask --net=my-bridge-net -p 5001:5001 flask-api
```

```
458ea0eb93feb682f2b68644eac83b84aa8bd91cebd930c9bfaa81b850e0b1d9
94c1f6801eb63a9db76314388381934d7bb1cefd37a8b263b65cebf03efb5aa4
db4870a74d1348f5d5f28992858f5990b17d439b46775584dc73ab137d9fafe2
```

```bash
docker ps
```

```
CONTAINER ID   IMAGE          STATUS         PORTS                                         NAMES
db4870a74d13   flask-api      Up 8 seconds   0.0.0.0:5001->5001/tcp, [::]:5001->5001/tcp   flask
94c1f6801eb6   redis:latest   Up 8 seconds   6379/tcp                                      redis
458ea0eb93fe   mysql:latest   Up 8 seconds   3306/tcp, 33060/tcp                           mysql
```

All three containers are running. Only `flask` publishes a port to the host (`5001`). MySQL (`3306`) and Redis (`6379`) are only reachable inside the network.

Each container got an IP address on `my-bridge-net`:

```bash
docker inspect -f '{{.Name}}  {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' mysql redis flask
```

```
/mysql  172.18.0.2
/redis  172.18.0.3
/flask  172.18.0.4
```

![Launch Containers](./Screenshots/04%20Launch%20Containers.png)

---

### 7. Test Connectivity

Pinged MySQL and Redis **by container name** from inside the Flask container:

```bash
docker exec flask ping -c 3 mysql
```

```
PING mysql (172.18.0.2) 56(84) bytes of data.
64 bytes from mysql.my-bridge-net (172.18.0.2): icmp_seq=1 ttl=64 time=0.194 ms
64 bytes from mysql.my-bridge-net (172.18.0.2): icmp_seq=2 ttl=64 time=0.157 ms
64 bytes from mysql.my-bridge-net (172.18.0.2): icmp_seq=3 ttl=64 time=0.207 ms

--- mysql ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2042ms
```

```bash
docker exec flask ping -c 3 redis
```

```
PING redis (172.18.0.3) 56(84) bytes of data.
64 bytes from redis.my-bridge-net (172.18.0.3): icmp_seq=1 ttl=64 time=0.160 ms
64 bytes from redis.my-bridge-net (172.18.0.3): icmp_seq=2 ttl=64 time=0.167 ms
64 bytes from redis.my-bridge-net (172.18.0.3): icmp_seq=3 ttl=64 time=0.143 ms

--- redis ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2058ms
```

Docker's built-in DNS resolved `mysql` → `172.18.0.2` and `redis` → `172.18.0.3` with 0% packet loss.

Also accessed the Flask API from the host through the published port:

```bash
curl http://localhost:5001/about
```

```
{
  "description": "This is a simple REST API built with Flask.",
  "name": "Simple REST API",
  "version": "1.0"
}
```

![Ping Between Containers](./Screenshots/05%20Ping%20Between%20Containers.png)

---

### 8. Name Resolution and Network Isolation

Connected to the Redis **service** by name from another container on the network:

```bash
docker run --rm --net=my-bridge-net redis:latest redis-cli -h redis ping
```

```
PONG
```

Then compared a container **on** `my-bridge-net` with one on Docker's **default** bridge:

```bash
docker run --rm --net=my-bridge-net flask-api ping -c 2 mysql
```

```
PING mysql (172.18.0.2) 56(84) bytes of data.
64 bytes from mysql.my-bridge-net (172.18.0.2): icmp_seq=1 ttl=64 time=0.109 ms
64 bytes from mysql.my-bridge-net (172.18.0.2): icmp_seq=2 ttl=64 time=0.175 ms
```

```bash
docker run --rm flask-api ping -c 2 mysql      # default bridge, NOT on my-bridge-net
```

```
ping: mysql: Name or service not known
```

A container outside `my-bridge-net` cannot even resolve the name `mysql`. User-defined bridge networks give containers both **name-based discovery** and **isolation** from other containers.

![Name Resolution and Isolation](./Screenshots/06%20Name%20Resolution%20and%20Isolation.png)

---

### 9. Access the Flask API in the Browser

Opened `http://localhost:5001/about`:

![Flask About Endpoint](./Screenshots/07%20Flask%20About%20Endpoint.png)

---

### 10. Clean Up

Stopped and removed the containers, then removed the network:

```bash
docker stop mysql redis flask && docker rm mysql redis flask
docker network rm my-bridge-net
```

```
mysql
redis
flask
mysql
redis
flask
my-bridge-net
```

```bash
docker network ls
```

```
NETWORK ID     NAME       DRIVER    SCOPE
1ae26515c1ee   bridge     bridge    local
2408b65655a6   host       host      local
d4fef7af0be6   minikube   bridge    local
9e96f71e999e   none       null      local
```

`my-bridge-net` is gone.

![Cleanup](./Screenshots/08%20Cleanup.png)

---

## Screenshots

### 1. Create and Inspect Network

![Create and Inspect Network](./Screenshots/01%20Create%20and%20Inspect%20Network.png)

> Shows `docker network create` creating `my-bridge-net`, `docker network ls` listing it, and `docker network inspect` showing its `172.18.0.0/16` subnet.

---

### 2. Build Flask Image

![Build Flask Image](./Screenshots/02%20Build%20Flask%20Image.png)

> Shows `docker build -t flask-api .` running all 8 Dockerfile steps and tagging `flask-api:latest`.

---

### 3. MySQL Without Password

![MySQL Without Password](./Screenshots/03%20MySQL%20Without%20Password.png)

> Shows `mysql:latest` exiting with code 1 when no password option is given, and the error listing the required environment variables.

---

### 4. Launch Containers

![Launch Containers](./Screenshots/04%20Launch%20Containers.png)

> Shows the MySQL, Redis and Flask containers starting on `my-bridge-net`, `docker ps` with all three running, and each container's IP address.

---

### 5. Ping Between Containers

![Ping Between Containers](./Screenshots/05%20Ping%20Between%20Containers.png)

> Shows the Flask container pinging `mysql` and `redis` by name with 0% packet loss, and `curl` reaching `/about` from the host.

---

### 6. Name Resolution and Isolation

![Name Resolution and Isolation](./Screenshots/06%20Name%20Resolution%20and%20Isolation.png)

> Shows `redis-cli -h redis ping` returning `PONG`, a container on `my-bridge-net` reaching `mysql`, and a container on the default bridge failing to resolve `mysql`.

---

### 7. Flask About Endpoint

![Flask About Endpoint](./Screenshots/07%20Flask%20About%20Endpoint.png)

> `http://localhost:5001/about` returning the API's name, version and description through the published port.

---

### 8. Cleanup

![Cleanup](./Screenshots/08%20Cleanup.png)

> Shows the containers being stopped and removed, and `my-bridge-net` being deleted.

---

## Q&A

**Q1: What is the purpose of the `--net` flag in `docker run`?**
It specifies the network to connect the container to. Here, `--net=my-bridge-net` put all three containers on the same network.

**Q2: How do containers communicate with each other on the same network?**
By container name or IP address. Docker's built-in DNS resolved `mysql` to `172.18.0.2` and `redis` to `172.18.0.3`.

**Q3: What is the difference between a bridge network and a host network?**
A bridge network gives containers their own private, isolated network; a host network shares the host's network stack directly.
* **Bridge network:** containers are in a private room, talking to each other through a door.
* **Host network:** containers are in the same room as the host, talking directly to everyone.

**Q4: How can you expose a container's port to the host machine?**
With the `-p` flag, e.g. `-p 5001:5001` (`host port:container port`). This is how `http://localhost:5001/about` was reached from the browser.

---

## Result

Successfully created a **user-defined bridge network**, ran **Flask, MySQL and Redis** containers on it, and confirmed that they communicate **by container name**.

Containers outside the network could not reach them, and the Flask API was reachable from the host only through its published port `5001`. All containers and the network were cleaned up at the end.
