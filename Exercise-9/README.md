# Jenkins Exercise 9

## Objective

The objective of this exercise is to create and run a **multi-stage Jenkins Pipeline** for a Python Flask application. The pipeline has **Build**, **Test**, **Deploy**, **Run Application** and **Test Application** stages.

**Scenario:** automate CI/CD for a Flask app.

1. **Build:** install dependencies
2. **Test:** run unit tests
3. **Deploy:** copy the app to a mock deployment directory

---

## Prerequisites

* Jenkins running at `http://localhost:8080` (from [Exercise 7](../Exercise-7)), with the **Pipeline** plugin. It was installed as part of the suggested plugins.
* The GitHub repository [gagandeepy080305/devops-sample-code](https://github.com/gagandeepy080305/devops-sample-code) (from [Exercise 8](../Exercise-8))

---

## Project Files

These files were pushed to the root of `devops-sample-code`. Copies are kept here:

| File | Description |
|------|-------------|
| [`app.py`](./app.py) | Flask app returning `Hello, Jenkins Multi-Stage Pipeline!` |
| [`requirements.txt`](./requirements.txt) | `flask==2.1.2` |
| [`test_app.py`](./test_app.py) | `unittest` test that calls `/` with Flask's test client |
| [`Jenkinsfile`](./Jenkinsfile) | Declarative pipeline with 5 stages and post actions |

---

## Changes from the Lab Instructions

| Lab instruction | What was done instead | Why |
|-----------------|-----------------------|-----|
| `git init` + `git remote add origin ...` | Added the files to the existing local `devops-sample-code` repository | The repository already existed from Exercise 8. |
| Jenkins Branch Specifier left at its default `*/master` | Set to **`*/main`** | The repository's branch is `main` (same fix as Exercise 8). |
| `apt install python3.11-venv` | Ran it (it failed: *Unable to locate package*), then installed **`python3-venv`** | The current `jenkins/jenkins:lts` image is based on **Debian 13**, which ships Python **3.13**, so there is no `python3.11-venv` package. |
| Interactive `docker exec -it -u root ... bash`, then `apt install ...` | Ran each command with `docker exec -u root jenkins apt install -y ...` | Same commands, as root in the same container. `-y` answers apt's confirmation prompt. |

---

## Steps Performed

### 1. Create the Sample Python Application

[`app.py`](./app.py):

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, Jenkins Multi-Stage Pipeline!"

if __name__ == "__main__":
    app.run(debug=True)
```

[`requirements.txt`](./requirements.txt):

```
flask==2.1.2
```

[`test_app.py`](./test_app.py):

```python
import unittest
from app import app

class TestApp(unittest.TestCase):
    def test_home(self):
        tester = app.test_client()
        response = tester.get("/")
        print(response.data.decode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("utf-8"), "Hello, Jenkins Multi-Stage Pipeline!")

if __name__ == "__main__":
    unittest.main()
```

---

### 2. Define the Jenkinsfile

[`Jenkinsfile`](./Jenkinsfile):

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'Creating virtual environment and installing dependencies...'
            }
        }
        stage('Test') {
            steps {
                echo 'Running tests...'
                sh 'python3 -m unittest discover -s .'
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying application...'
                sh '''
                mkdir -p ${WORKSPACE}/python-app-deploy
                cp ${WORKSPACE}/app.py ${WORKSPACE}/python-app-deploy/
                '''
            }
        }
        stage('Run Application') {
            steps {
                echo 'Running application...'
                sh '''
                nohup python3 ${WORKSPACE}/python-app-deploy/app.py > ${WORKSPACE}/python-app-deploy/app.log 2>&1 &
                echo $! > ${WORKSPACE}/python-app-deploy/app.pid
                '''
            }
        }
        stage('Test Application') {
            steps {
                echo 'Testing application...'
                sh '''
                python3 ${WORKSPACE}/test_app.py
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check the logs for more details.'
        }
    }
}
```

| Stage | What it does |
|-------|--------------|
| Build | Prints a message (the lab's Jenkinsfile does not actually run `pip install`) |
| Test | Runs all unit tests with `python3 -m unittest discover -s .` |
| Deploy | Copies `app.py` into `python-app-deploy/` in the workspace |
| Run Application | Starts the app in the background with `nohup` and saves its PID |
| Test Application | Runs `test_app.py` directly |
| post | Prints a success or failure message |

---

### 3. Push the Application and Jenkinsfile to GitHub

```bash
git add app.py requirements.txt test_app.py
git commit -m "Add Python Flask app and unit test"
git push

git add Jenkinsfile
git commit -m "Added Jenkinsfile"
git push
```

```
[main 39075cf] Add Python Flask app and unit test
 3 files changed, 24 insertions(+)
To https://github.com/gagandeepy080305/devops-sample-code.git
   7c6e528..39075cf  main -> main

[main 3fb3b2d] Added Jenkinsfile
 1 file changed, 52 insertions(+)
To https://github.com/gagandeepy080305/devops-sample-code.git
   39075cf..3fb3b2d  main -> main
```

![Push App and Jenkinsfile to GitHub](./Screenshots/01%20Push%20App%20and%20Jenkinsfile%20to%20GitHub.png)

![GitHub Repository](./Screenshots/02%20GitHub%20Repository.png)

---

### 4. Create a Pipeline Job in Jenkins

**New Item** → name **`Python-MultiStage-Pipeline`** → **Pipeline** → **OK**:

![New Item Pipeline](./Screenshots/03%20New%20Item%20Pipeline.png)

---

### 5. Configure the Job: Pipeline Script from SCM

Under **Pipeline**:

* **Definition:** Pipeline script from SCM
* **SCM:** Git
* **Repository URL:** `https://github.com/gagandeepy080305/devops-sample-code.git` (public, so no credentials)
* **Branch Specifier:** `*/main`
* **Script Path:** `Jenkinsfile`

![Configure Pipeline Script from SCM](./Screenshots/04%20Configure%20Pipeline%20Script%20from%20SCM.png)

![Configure Branch and Script Path](./Screenshots/05%20Configure%20Branch%20and%20Script%20Path.png)

Clicked **Save**.

---

### 6. Run the Pipeline: Build #1 Fails

Clicked **Build Now**. Jenkins got the Jenkinsfile from GitHub (commit `3fb3b2d`), and **Checkout SCM** and **Build** passed, but **Test** failed:

```
+ python3 -m unittest discover -s .
/var/jenkins_home/workspace/Python-MultiStage-Pipeline@tmp/durable-a14e336b/script.sh.copy: 1: python3: not found
...
Stage "Deploy" skipped due to earlier failure(s)
Stage "Run Application" skipped due to earlier failure(s)
Stage "Test Application" skipped due to earlier failure(s)
...
Pipeline failed. Check the logs for more details.
ERROR: script returned exit code 127
Finished: FAILURE
```

This is the failure the lab predicts in *Step 8: Handling build errors*. The `jenkins/jenkins:lts` image has no Python. Exit code **127** means "command not found". The later stages were skipped, and the `post { failure }` block ran.

![Build 1 Failed Stages](./Screenshots/06%20Build%201%20Failed%20Stages.png)

![Build 1 Console Output](./Screenshots/07%20Build%201%20Console%20Output.png)

---

### 7. Handle the Build Errors: Install Python in the Jenkins Container

Confirmed Python was missing:

```bash
docker exec jenkins python3 --version
```

```
OCI runtime exec failed: exec failed: unable to start container process: exec: "python3": executable file not found in $PATH
```

Ran the lab's commands as **root** inside the Jenkins container:

```bash
apt-get update
apt install python3
apt install pip
apt install python3.11-venv
apt install python3-flask
```

| Command | Result |
|---------|--------|
| `apt-get update` | OK |
| `apt install python3` | OK, installed Python **3.13.5** |
| `apt install pip` | OK, installed pip **25.1.1** |
| `apt install python3.11-venv` | **Error:** `Unable to locate package python3.11-venv` (exit code 100) |
| `apt install python3-venv` | OK (replacement for the line above) |
| `apt install python3-flask` | OK, installed Flask **3.1.1** |

The container is **Debian 13 (trixie)**, whose Python version is 3.13. That is why `python3.11-venv` doesn't exist and `python3-venv` is the right package.

![Install Python in Jenkins Container](./Screenshots/08%20Install%20Python%20in%20Jenkins%20Container.png)

---

### 8. Run the Pipeline Again: Build #2 Succeeds

Clicked **Build Now** again. All stages passed:

```
[Pipeline] { (Test)
Running tests...
+ python3 -m unittest discover -s .
.
----------------------------------------------------------------------
Ran 1 test in 0.002s

OK
Hello, Jenkins Multi-Stage Pipeline!
[Pipeline] { (Deploy)
Deploying application...
+ mkdir -p /var/jenkins_home/workspace/Python-MultiStage-Pipeline/python-app-deploy
+ cp /var/jenkins_home/workspace/Python-MultiStage-Pipeline/app.py /var/jenkins_home/workspace/Python-MultiStage-Pipeline/python-app-deploy/
[Pipeline] { (Run Application)
Running application...
+ echo 2231
+ nohup python3 /var/jenkins_home/workspace/Python-MultiStage-Pipeline/python-app-deploy/app.py
[Pipeline] { (Test Application)
Testing application...
+ python3 /var/jenkins_home/workspace/Python-MultiStage-Pipeline/test_app.py
.
----------------------------------------------------------------------
Ran 1 test in 0.002s

OK
Hello, Jenkins Multi-Stage Pipeline!
[Pipeline] { (Declarative: Post Actions)
Pipeline completed successfully!
[Pipeline] End of Pipeline
Finished: SUCCESS
```

![Build 2 Successful Stages](./Screenshots/09%20Build%202%20Successful%20Stages.png)

![Build 2 Console Output](./Screenshots/10%20Build%202%20Console%20Output.png)

The job page shows the history: **#1 failed**, **#2 succeeded**.

![Pipeline Job Build History](./Screenshots/11%20Pipeline%20Job%20Build%20History.png)

---

## Expected Outcome vs Actual

| Stage | Expected (lab) | Actual (build #2) |
|-------|----------------|-------------------|
| Build | Dependencies installed | Message printed. The lab's Jenkinsfile has no `pip install` step; Flask came from `apt install python3-flask` |
| Test | Unit tests pass | `Ran 1 test ... OK` |
| Deploy | `app.py` copied to the deployment directory | Copied to `$WORKSPACE/python-app-deploy/` (the path the Jenkinsfile uses) |
| Run Application | App started in the background | Started with `nohup` (PID 2231) |
| Test Application | Test passes | `Ran 1 test ... OK` |
| Result | `Finished: SUCCESS` | **`Finished: SUCCESS`** |

---

## Screenshots

| # | Screenshot | Shows |
|---|-----------|-------|
| 1 | [Push App and Jenkinsfile to GitHub](./Screenshots/01%20Push%20App%20and%20Jenkinsfile%20to%20GitHub.png) | Two commits pushed to `devops-sample-code` |
| 2 | [GitHub Repository](./Screenshots/02%20GitHub%20Repository.png) | Repository with app, tests and Jenkinsfile |
| 3 | [New Item Pipeline](./Screenshots/03%20New%20Item%20Pipeline.png) | `Python-MultiStage-Pipeline` with *Pipeline* selected |
| 4 | [Configure Pipeline Script from SCM](./Screenshots/04%20Configure%20Pipeline%20Script%20from%20SCM.png) | Definition *Pipeline script from SCM*, Git, repository URL |
| 5 | [Configure Branch and Script Path](./Screenshots/05%20Configure%20Branch%20and%20Script%20Path.png) | Branch `*/main`, Script Path `Jenkinsfile` |
| 6 | [Build 1 Failed Stages](./Screenshots/06%20Build%201%20Failed%20Stages.png) | Stage graph: Test failed, later stages skipped |
| 7 | [Build 1 Console Output](./Screenshots/07%20Build%201%20Console%20Output.png) | `python3: not found`, `Finished: FAILURE` |
| 8 | [Install Python in Jenkins Container](./Screenshots/08%20Install%20Python%20in%20Jenkins%20Container.png) | Lab's `apt install` commands run as root, versions installed |
| 9 | [Build 2 Successful Stages](./Screenshots/09%20Build%202%20Successful%20Stages.png) | Stage graph: all stages green |
| 10 | [Build 2 Console Output](./Screenshots/10%20Build%202%20Console%20Output.png) | Tests OK, deploy, run, `Finished: SUCCESS` |
| 11 | [Pipeline Job Build History](./Screenshots/11%20Pipeline%20Job%20Build%20History.png) | Build #1 failed, build #2 succeeded |

---

## Q&A

**Q1: What is the difference between a Freestyle job and a Pipeline job?**
A Freestyle job is configured in the UI with a fixed set of steps. A Pipeline job is defined as code in a `Jenkinsfile`, with named stages, conditions and post actions. It is versioned in Git alongside the application.

**Q2: What does "Pipeline script from SCM" mean?**
Jenkins reads the `Jenkinsfile` from the Git repository at build time (*Obtained Jenkinsfile from git ...*), instead of from a script pasted into the job. Changing the pipeline is then just a commit.

**Q3: What happens when a stage fails?**
The pipeline stops. The remaining stages are marked *skipped due to earlier failure(s)*, the `post { failure }` block runs, and the build ends with `Finished: FAILURE`. This is what happened in build #1.

**Q4: Why did the first build fail with exit code 127?**
The Jenkins image has no Python, so the shell couldn't find `python3`. Exit code 127 means "command not found". Installing Python in the container fixed it.

**Q5: What is the `post` section used for?**
Actions that run after the stages, depending on the result: `success`, `failure`, `always`, etc. They are typically used for notifications or clean-up.

---

## Result

Successfully created a **multi-stage Jenkins Pipeline** (`Python-MultiStage-Pipeline`) that reads its `Jenkinsfile` from GitHub.

* **Build #1** failed at the *Test* stage because Python was missing from the Jenkins container, as the lab predicts.
* After installing Python 3.13, pip, venv and Flask in the container, **build #2** passed every stage (Build → Test → Deploy → Run Application → Test Application) and printed **`Pipeline completed successfully!`** with **`Finished: SUCCESS`**.
