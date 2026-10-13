# Docker Exercise 5

## Objective

The objective of this exercise is to secure a Docker container with an **AppArmor profile**, apply the profile with both the Docker CLI and the **Docker SDK for Python**, and test that restricted actions are blocked inside the container.

**Scenario:** a Python Flask web application runs in a Docker container. The container must be prevented from reading sensitive directories (`/etc`, `/var`) and from executing binaries in `/bin` and `/usr/bin`.

---

## Prerequisites

* macOS (Apple Silicon)
* Colima (Docker engine) and Docker CLI
* Python 3 with the Docker SDK (`pip install docker`)

AppArmor is a **Linux kernel** security module, and macOS does not have it. Colima runs Docker inside an **Ubuntu 24.04 VM** (kernel 6.8) where AppArmor is enabled, so AppArmor profiles are loaded **inside that VM** with `colima ssh`. `apparmor_parser` is already installed there, so the `apt-get install apparmor-utils` step from the lab is not needed.

```
$ docker info --format '{{.SecurityOptions}}'
[name=apparmor name=seccomp,profile=builtin name=cgroupns]
```

---

## Project Files

| File | Description |
|------|-------------|
| [`app.py`](./app.py) | Flask app that returns a greeting on port `5000` |
| [`Dockerfile`](./Dockerfile) | Builds the `flask-apparmor` image from `python:3.8-slim` |
| [`my-apparmor-profile`](./my-apparmor-profile) | Working AppArmor profile applied to the container |
| [`apply_apparmor.py`](./apply_apparmor.py) | Docker SDK script: builds the image, runs it with the profile, verifies the profile |
| [`test_restricted_actions.py`](./test_restricted_actions.py) | Docker SDK script: tries restricted actions inside the confined container |

---

## Changes from the Lab Instructions

| Problem | Fix |
|---------|-----|
| The lab profile uses `deny ... rmix`, which `apparmor_parser` rejects: *in deny rules 'x' must not be preceded by exec qualifier 'i'* | Changed to `deny ... rmx` |
| The lab profile is named `/usr/bin/python3`, but Docker looks profiles up **by name**, so `apparmor=my-apparmor-profile` fails with `label not found` | Declared it as `profile my-apparmor-profile` |
| The lab profile only allows `/app/**`, so the container cannot load Python or its libraries | Added `file,` (like Docker's default profile). The `deny` rules still take precedence |
| Port `5000` on macOS is used by the **AirPlay Receiver** (`Server: AirTunes`) | Published the container on host port **5050** (`-p 5050:5000`) |

---

## Steps Performed

### 1. Create the Flask Application

Created [`app.py`](./app.py):

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, this is a secure Flask application running inside a Docker container!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

### 2. Containerize the Application

Created [`Dockerfile`](./Dockerfile):

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Flask
RUN pip install flask

# Expose port 5000
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "app.py"]
```

Built the image:

```bash
docker build -t flask-apparmor .
```

```
Step 1/6 : FROM python:3.8-slim
Step 2/6 : WORKDIR /app
Step 3/6 : COPY . /app
Step 4/6 : RUN pip install flask
Successfully installed Jinja2-3.1.6 MarkupSafe-2.1.5 Werkzeug-3.0.6 blinker-1.8.2 click-8.1.8 flask-3.0.3 importlib-metadata-8.5.0 itsdangerous-2.2.0 zipp-3.20.2
Step 5/6 : EXPOSE 5000
Step 6/6 : CMD ["python", "app.py"]
Successfully built 31bf0722ceef
Successfully tagged flask-apparmor:latest
```

![Build Image](./Screenshots/01%20Build%20Image.png)

---

### 3. Try the Lab's AppArmor Profile

Saved the lab's profile as `/etc/apparmor.d/my-apparmor-profile` in the Colima VM and loaded it:

```bash
colima ssh -- sudo apparmor_parser -r /etc/apparmor.d/my-apparmor-profile
```

```
AppArmor parser error for /etc/apparmor.d/my-apparmor-profile in profile /etc/apparmor.d/my-apparmor-profile at line 15:
Invalid perms, in deny rules 'x' must not be preceded by exec qualifier 'i', 'p', or 'u'
```

After changing `rmix` → `rmx`, the profile loaded, but `aa-status` showed it under the name **`/usr/bin/python3`**:

```bash
colima ssh -- sudo aa-status | grep -E "python3|my-apparmor"
```

```
   /usr/bin/python3
```

So Docker still could not find a profile called `my-apparmor-profile`:

```bash
docker run --rm --security-opt="apparmor=my-apparmor-profile" -p 5000:5000 flask-apparmor
```

```
docker: Error response from daemon: ... unable to apply apparmor profile: apparmor failed to apply profile:
write fsmount:fscontext:proc/thread-self/attr/apparmor/exec: no such file or directory
```

The kernel log shows the reason:

```
apparmor="DENIED" operation="change_onexec" info="label not found" profile="unconfined" name="my-apparmor-profile"
```

The `/usr/bin/python3` profile was then unloaded (`apparmor_parser -R`) so it would not confine the VM's own Python.

![Lab Profile Errors](./Screenshots/02%20Lab%20Profile%20Errors.png)

---

### 4. Create and Load a Working AppArmor Profile

Created [`my-apparmor-profile`](./my-apparmor-profile). It keeps all of the lab's restrictions:

```
#include <tunables/global>

# Named profile so Docker can apply it with --security-opt apparmor=my-apparmor-profile
profile my-apparmor-profile flags=(attach_disconnected,mediate_deleted) {
    #include <abstractions/base>

    # Allow general file access (like Docker's default profile); the deny rules below take precedence
    file,

    # Allow Flask app to bind to port 5000
    network inet stream,
    network inet6 stream,

    # Let Docker stop the container
    signal (receive) peer=unconfined,
    signal (send,receive) peer=my-apparmor-profile,

    # Permissions to the application directory
    /app/** rwk,

    # Deny access to sensitive system files
    deny /etc/** r,
    deny /var/** rw,

    # Deny execution of any binaries in /bin or /usr/bin
    deny /bin/** rmx,
    deny /usr/bin/** rmx,

    # Capability restrictions
    capability net_bind_service,
    deny capability sys_admin,
}
```

* `profile my-apparmor-profile` gives the profile the name Docker uses.
* `flags=(attach_disconnected,mediate_deleted)` is needed for container filesystems (Docker's own default profile uses it too).
* `deny` rules always win over allow rules, so `file,` does not weaken the restrictions.

Copied it into the VM and loaded it:

```bash
colima ssh -- sudo tee /etc/apparmor.d/my-apparmor-profile < my-apparmor-profile
colima ssh -- sudo apparmor_parser -r /etc/apparmor.d/my-apparmor-profile
colima ssh -- sudo aa-status | grep my-apparmor
```

```
   my-apparmor-profile
```

---

### 5. Run the Container with the Profile

```bash
docker run -d --name flask-secure --security-opt="apparmor=my-apparmor-profile" -p 5050:5000 flask-apparmor
docker inspect -f '{{.AppArmorProfile}}' flask-secure
curl http://localhost:5050/
```

```
NAMES          STATUS         PORTS
flask-secure   Up 4 seconds   0.0.0.0:5050->5000/tcp, [::]:5050->5000/tcp

my-apparmor-profile

Hello, this is a secure Flask application running inside a Docker container!
```

The container runs under `my-apparmor-profile`, and the Flask app still works normally.

![Working Profile Loaded](./Screenshots/03%20Working%20Profile%20Loaded.png)

![Secure Flask App](./Screenshots/04%20Secure%20Flask%20App.png)

---

### 6. Test Restricted Actions with the Docker CLI

```bash
docker exec flask-secure cat /etc/passwd
docker exec flask-secure python -c "open('/etc/passwd').read()"
docker exec flask-secure python -c "open('/var/test.txt', 'w')"
docker exec flask-secure python -c "open('/app/test.txt', 'w').write('ok'); print(open('/app/test.txt').read())"
docker exec flask-secure /bin/bash -c 'ls /app'
docker exec flask-secure python -c "import subprocess; subprocess.run(['/bin/ls', '/app'])"
```

| Action | Result | Exit code |
|--------|--------|-----------|
| `cat /etc/passwd` | `cat: /etc/passwd: Permission denied` | 1 |
| Read `/etc/passwd` from Python | `PermissionError: [Errno 13] Permission denied: '/etc/passwd'` | 1 |
| Write to `/var` from Python | `PermissionError: [Errno 13] Permission denied: '/var/test.txt'` | 1 |
| Write to `/app` | `ok` (allowed) | 0 |
| Run `/bin/ls` from bash | `/bin/bash: line 1: /usr/bin/ls: Permission denied` | **126** |
| Run `/bin/ls` from Python | `PermissionError: [Errno 13] Permission denied: '/bin/ls'` | 1 |

![Restricted Actions](./Screenshots/05%20Restricted%20Actions.png)

**Note on executing binaries:** `cat` and `/bin/bash` themselves were allowed to *start*. The first program that `docker exec` runs is launched by Docker's runtime (`runc`), which is not confined. AppArmor applies the profile as that program starts. From then on, the profile controls everything it does, including starting other programs. That is why `cat` could not read `/etc/passwd`, and why bash and Python could not run `/bin/ls`. A compromised app inside the container can't launch shell tools.

---

### 7. Compare with Docker's Default Profile

Ran the same image without the custom profile. Docker applies its built-in `docker-default` profile:

```bash
docker run -d --name flask-default -p 5051:5000 flask-apparmor
docker inspect -f '{{.AppArmorProfile}}' flask-default
docker exec flask-default cat /etc/passwd
docker exec flask-default python -c "open('/var/test.txt', 'w'); print('written')"
docker exec flask-default /bin/bash -c 'ls /app'
```

Output (last 3 lines of each command):

```
docker-default

irc:x:39:39:ircd:/run/ircd:/usr/sbin/nologin
_apt:x:42:65534::/nonexistent:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin

written

README.md
Screenshots
app.py
```

With `docker-default`, every one of these actions succeeds. The restrictions come from `my-apparmor-profile`.

![Default Profile Comparison](./Screenshots/06%20Default%20Profile%20Comparison.png)

---

### 8. Apply the Profile with the Docker SDK for Python

Created [`apply_apparmor.py`](./apply_apparmor.py), which builds the image, runs the container with `security_opt=["apparmor=my-apparmor-profile"]`, and reads the profile back with `inspect_container`:

```python
container = client.containers.run(
    "flask-apparmor",
    ports={'5000/tcp': 5050},
    security_opt=["apparmor=my-apparmor-profile"],
    detach=True
)
...
container_info = client.api.inspect_container(container.id)
apparmor_profile = container_info['HostConfig']['SecurityOpt']
```

```bash
pip install docker
python apply_apparmor.py
```

```
Building image from Dockerfile...
[INFO] Step 1/6 : FROM python:3.8-slim
[INFO] Step 2/6 : WORKDIR /app
[INFO] Step 3/6 : COPY . /app
[INFO] Step 4/6 : RUN pip install flask
[INFO] Successfully installed Jinja2-3.1.6 MarkupSafe-2.1.5 Werkzeug-3.0.6 blinker-1.8.2 click-8.1.8 flask-3.0.3 importlib-metadata-8.5.0 itsdangerous-2.2.0 zipp-3.20.2
[INFO] Step 5/6 : EXPOSE 5000
[INFO] Step 6/6 : CMD ["python", "app.py"]
[INFO] Successfully built ee74ea092e1d
[INFO] Successfully tagged flask-apparmor:latest

Running container with AppArmor profile...
Container started: 5d73478f308f

Inspecting container to verify AppArmor profile...
AppArmor profile applied: ['apparmor=my-apparmor-profile']
Active AppArmor profile: my-apparmor-profile

Stopping the container...
Container stopped and removed
```

![Docker SDK Apply Profile](./Screenshots/07%20Docker%20SDK%20Apply%20Profile.png)

---

### 9. Test Restricted Actions with the Docker SDK

Created [`test_restricted_actions.py`](./test_restricted_actions.py). It runs the lab's two tests (`cat /etc/passwd` and `/bin/bash`) plus the checks from Step 6, using `container.exec_run()`:

```bash
python test_restricted_actions.py
```

```
Container started: 3ef3710c8472

Attempt to read /etc/passwd: Exit Code 1, Output: cat: /etc/passwd: Permission denied
Attempt to execute /bin/bash: Exit Code 0, Output:
Attempt to read /etc/passwd from Python: Exit Code 1, Output: PermissionError: [Errno 13] Permission denied: '/etc/passwd'
Attempt to write to /var from Python: Exit Code 1, Output: PermissionError: [Errno 13] Permission denied: '/var/test.txt'
Attempt to run /bin/ls from bash: Exit Code 126, Output: /bin/bash: line 1: /usr/bin/ls: Permission denied
Attempt to run /bin/ls from Python: Exit Code 1, Output: PermissionError: [Errno 13] Permission denied: '/bin/ls'
Attempt to write to /app (allowed): Exit Code 0, Output: ok

Container stopped
```

The lab expected `/bin/bash` to return exit code 126. In practice bash starts (see the note in Step 6) and exits with 0 because it has no input. Once bash tries to run another program (`ls`), it gets exit code **126 – Permission denied**.

![Docker SDK Test Restricted Actions](./Screenshots/08%20Docker%20SDK%20Test%20Restricted%20Actions.png)

---

## Screenshots

### 1. Build Image

![Build Image](./Screenshots/01%20Build%20Image.png)

> Shows `docker build -t flask-apparmor .` building the image from `python:3.8-slim`.

---

### 2. Lab Profile Errors

![Lab Profile Errors](./Screenshots/02%20Lab%20Profile%20Errors.png)

> Shows the lab profile failing to parse (`rmix`), then loading as `/usr/bin/python3` after the syntax fix, `docker run` failing because no profile is named `my-apparmor-profile`, and the kernel's `label not found` log entries.

---

### 3. Working Profile Loaded

![Working Profile Loaded](./Screenshots/03%20Working%20Profile%20Loaded.png)

> Shows the working profile loaded as `my-apparmor-profile`, the `flask-secure` container running with it, and `curl` reaching the app on port 5050.

---

### 4. Secure Flask App

![Secure Flask App](./Screenshots/04%20Secure%20Flask%20App.png)

> `http://localhost:5050/` served by the Flask app running under the AppArmor profile.

---

### 5. Restricted Actions

![Restricted Actions](./Screenshots/05%20Restricted%20Actions.png)

> Shows reads of `/etc/passwd`, writes to `/var`, and execution of `/bin/ls` being denied, while writes to `/app` are allowed.

---

### 6. Default Profile Comparison

![Default Profile Comparison](./Screenshots/06%20Default%20Profile%20Comparison.png)

> Shows the same actions succeeding in a container using Docker's `docker-default` profile.

---

### 7. Docker SDK Apply Profile

![Docker SDK Apply Profile](./Screenshots/07%20Docker%20SDK%20Apply%20Profile.png)

> Shows `apply_apparmor.py` building the image, starting the container with the profile, and confirming `['apparmor=my-apparmor-profile']`.

---

### 8. Docker SDK Test Restricted Actions

![Docker SDK Test Restricted Actions](./Screenshots/08%20Docker%20SDK%20Test%20Restricted%20Actions.png)

> Shows `test_restricted_actions.py` results: sensitive file access and binary execution denied, `/app` writes allowed.

---

## Q&A

**Q1: What is the purpose of using AppArmor with Docker containers?**
AppArmor enforces security policies that confine a container to a limited set of files, network access and capabilities. It adds a layer of security on top of the container's isolation.

**Q2: How do AppArmor profiles help secure a Docker container?**
A profile defines what the containerized app can and cannot do. In this exercise, `my-apparmor-profile` blocked reads of `/etc`, writes to `/var`, and execution of `/bin` and `/usr/bin` binaries, while the Flask app kept working.

**Q3: Why is it important to restrict access to sensitive directories such as `/etc/` and `/var/`?**
`/etc` holds configuration and account data such as `/etc/passwd`, and `/var` holds logs and application state. Blocking them stops a compromised app from reading sensitive data or tampering with system files.

**Q4: What other capabilities can you restrict using AppArmor profiles?**
Network access (e.g. only `inet stream`), binding to ports (`net_bind_service`), executing binaries, writing to specific directories, sending signals, mounting, and Linux capabilities such as `sys_admin`.

**Q5: How can you verify if an AppArmor profile is successfully applied to a Docker container?**
Inspect the container. With the CLI, use `docker inspect -f '{{.AppArmorProfile}}' <container>`. With the Docker SDK, read `HostConfig.SecurityOpt` from `inspect_container()`. Both showed `my-apparmor-profile`. On the host, `aa-status` lists the loaded profiles.

---

## Result

Successfully containerized a **Flask application** and secured it with a custom **AppArmor profile**. The profile was loaded in Colima's Linux VM and applied with both the **Docker CLI** and the **Docker SDK for Python**.

Inside the confined container, reading `/etc/passwd`, writing to `/var`, and executing `/bin` binaries were all **denied**, while the Flask app and writes to `/app` kept working. A container using Docker's default profile could do all of these actions, which confirms the custom profile is what blocks them.
