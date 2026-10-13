# Jenkins Exercise 7

## Objective

The objective of this exercise is to understand **Continuous Integration (CI)** and to install and set up **Jenkins** with Docker.

---

## Continuous Integration in Brief

**Continuous Integration** means developers merge their changes into a shared repository often, and every change is automatically built and tested. Problems are caught early, while they are still small and cheap to fix.

| Key feature | What it means |
|-------------|---------------|
| Frequent integration | Code is committed to the shared repository many times a day |
| Automated builds | Every commit triggers a build |
| Automated testing | Tests run as part of every build |
| Immediate feedback | Developers quickly learn whether their change broke something |

**CI workflow:** developer pushes code → CI server detects the change → build → tests → feedback (pass/fail).

**Common CI tools:** Jenkins, GitLab CI/CD, GitHub Actions, CircleCI, Travis CI, Bamboo, TeamCity, Azure Pipelines, Spinnaker, Buildkite and Drone.

### Jenkins

**Jenkins** is an open-source automation server for building, testing and deploying software. It is highly extensible through plugins.

| Concept | Meaning |
|---------|---------|
| Job / Project | A task Jenkins runs |
| Build | One run of a job |
| Pipeline | A series of stages to build, test and deploy |
| Plugins | Add features (e.g. Git, Pipeline, Docker) |
| Nodes | Machines that run jobs (controller and agents) |

---

## Prerequisites

* macOS (Apple Silicon)
* Colima (Docker engine) and Docker CLI

---

## Steps Performed

### 1. Install Jenkins Using Docker

```bash
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 jenkins/jenkins:lts
```

```
Unable to find image 'jenkins/jenkins:lts' locally
lts: Pulling from jenkins/jenkins
Digest: sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1
Status: Downloaded newer image for jenkins/jenkins:lts
c3cafa3bec5adb4abd914aa1cca495f45fd39e021b24814c4b1637d7faade054
```

* `-p 8080:8080` – Jenkins web UI
* `-p 50000:50000` – port for build agents to connect to the controller

![Install Jenkins with Docker](./Screenshots/01%20Install%20Jenkins%20with%20Docker.png)

---

### 2. Get the Initial Admin Password

```bash
docker ps -a --filter name=jenkins
```

```
CONTAINER ID   IMAGE                 COMMAND                  CREATED         STATUS         PORTS                                                                                          NAMES
c3cafa3bec5a   jenkins/jenkins:lts   "/usr/bin/tini -- /u…"   7 seconds ago   Up 7 seconds   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp, 0.0.0.0:50000->50000/tcp, [::]:50000->50000/tcp   jenkins
```

On first start, Jenkins generates a one-time password. It is stored in a file inside the container and also printed in the container log:

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
docker logs jenkins
```

```
b300************************9b56

*************************************************************

Jenkins initial setup is required. An admin user has been created and a password generated.
Please use the following password to proceed to installation:

b300************************9b56

This may also be found at: /var/jenkins_home/secrets/initialAdminPassword
```

The password (32 hex characters) is **masked** here so it is not published.

The lab uses `docker exec -it jenkins bash` and then `cat` inside the container. Running `docker exec jenkins cat ...` directly gives the same result in one command.

![Get Initial Admin Password](./Screenshots/02%20Get%20Initial%20Admin%20Password.png)

---

### 3. Unlock Jenkins

Opened `http://localhost:8080/` and pasted the initial admin password:

![Unlock Jenkins](./Screenshots/03%20Unlock%20Jenkins.png)

---

### 4. Customize Jenkins: Install Suggested Plugins

Chose **Install suggested plugins**:

![Customize Jenkins](./Screenshots/04%20Customize%20Jenkins.png)

---

### 5. Getting Started: Plugins Installing

Jenkins downloaded and installed the suggested plugins (Folders, Pipeline, Git, Credentials Binding, Timestamper, Workspace Cleanup, Gradle, Ant, GitHub Branch Source, Matrix Authorization Strategy, LDAP, Email Extension, Mailer, Dark Theme, …) and their dependencies:

![Getting Started Installing Plugins](./Screenshots/05%20Getting%20Started%20Installing%20Plugins.png)

The Jenkins log confirmed:

```
Completed installation of 92 plugins in 2 min 51 sec
```

---

### 6. Create First Admin User

Chose **Skip and continue as admin**. Jenkins keeps the built-in `admin` account, which uses the initial admin password, so no extra account was created for this local lab instance.

![Create First Admin User](./Screenshots/06%20Create%20First%20Admin%20User.png)

---

### 7. Instance Configuration

Kept the default Jenkins URL `http://localhost:8080/` and clicked **Save and Finish**:

![Instance Configuration](./Screenshots/07%20Instance%20Configuration.png)

---

### 8. Jenkins Is Ready

![Jenkins Is Ready](./Screenshots/08%20Jenkins%20Is%20Ready.png)

---

### 9. Jenkins Landing Page

Clicked **Start using Jenkins** and reached the dashboard. From here you can create jobs (**New Item**), view **Build History**, and set up agents or clouds for distributed builds:

![Jenkins Landing Page](./Screenshots/09%20Jenkins%20Landing%20Page.png)

---

## Screenshots

| # | Screenshot | Shows |
|---|-----------|-------|
| 1 | [Install Jenkins with Docker](./Screenshots/01%20Install%20Jenkins%20with%20Docker.png) | Pulling `jenkins/jenkins:lts` and starting the container |
| 2 | [Get Initial Admin Password](./Screenshots/02%20Get%20Initial%20Admin%20Password.png) | Container running, initial admin password (masked) from the file and the log |
| 3 | [Unlock Jenkins](./Screenshots/03%20Unlock%20Jenkins.png) | Unlock Jenkins page asking for the administrator password |
| 4 | [Customize Jenkins](./Screenshots/04%20Customize%20Jenkins.png) | Install suggested plugins / Select plugins to install |
| 5 | [Getting Started Installing Plugins](./Screenshots/05%20Getting%20Started%20Installing%20Plugins.png) | Plugin installation in progress |
| 6 | [Create First Admin User](./Screenshots/06%20Create%20First%20Admin%20User.png) | Admin user form with *Skip and continue as admin* |
| 7 | [Instance Configuration](./Screenshots/07%20Instance%20Configuration.png) | Jenkins URL `http://localhost:8080/` |
| 8 | [Jenkins Is Ready](./Screenshots/08%20Jenkins%20Is%20Ready.png) | Setup complete |
| 9 | [Jenkins Landing Page](./Screenshots/09%20Jenkins%20Landing%20Page.png) | *Welcome to Jenkins!* dashboard |

---

## Q&A

**Q1: What is Continuous Integration?**
A practice where developers integrate code into a shared repository frequently, and each change is automatically built and tested to catch problems early.

**Q2: Why run Jenkins in Docker?**
It needs no Java installation or system setup on the machine. One `docker run` command gives a clean, reproducible Jenkins that is easy to remove or upgrade.

**Q3: What are ports 8080 and 50000 used for?**
`8080` serves the Jenkins web UI. `50000` is used by build agents to connect to the Jenkins controller for distributed builds.

**Q4: Why does Jenkins ask for an initial admin password?**
So that only someone with access to the server (its log or `/var/jenkins_home/secrets/initialAdminPassword`) can complete the setup. Nobody else who reaches the web UI can take it over.

**Q5: What do the suggested plugins provide?**
The most common features: Pipelines, Git and GitHub integration, credentials handling, build timeouts and timestamps, workspace cleanup, Gradle and Ant builds, email notifications and access control.

---

## Result

Successfully installed **Jenkins LTS (2.580.1)** using Docker, unlocked it with the initial admin password, installed the **suggested plugins** (92 plugins including dependencies), completed the setup wizard, and reached the **Welcome to Jenkins!** dashboard at `http://localhost:8080/`.
