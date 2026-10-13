# Jenkins Exercise 8

## Objective

The objective of this exercise is to create a **"Hello World" Jenkins job**:

1. Write a `hello-world.sh` script and push it to a new GitHub repository.
2. Create a Jenkins **Freestyle project** that pulls the script from GitHub and runs it.
3. Run the job and check the console output.

---

## Prerequisites

* Jenkins running at `http://localhost:8080` (set up in [Exercise 7](../Exercise-7))
* A GitHub account, with Git and the GitHub CLI (`gh`) signed in on this Mac

---

## Project Files

| File | Description |
|------|-------------|
| [`hello-world.sh`](./hello-world.sh) | Copy of the script pushed to [gagandeepy080305/devops-sample-code](https://github.com/gagandeepy080305/devops-sample-code) |

---

## Changes from the Lab Instructions

| Lab instruction | What was done instead | Why |
|-----------------|-----------------------|-----|
| Create the repo in the GitHub web UI and push with a Personal Access Token | Created it with `gh repo create`, and pushed using the existing `gh` login | Same result. `gh` was already signed in, so no token needed to be created or pasted. |
| `git config --global user.name/email` | Set the name/email for this repository only (`git config` without `--global`) | Leaves the global Git configuration unchanged. |
| `git init` (creates branch `master`), then `git push -u origin main` | `git init -b main` | The lab's commands don't match: they create `master` but push `main`. |
| Jenkins *Branch Specifier* left at its default `*/master` (not mentioned in the lab) | Set to **`*/main`** | The repository's branch is `main`. With `*/master` the build fails because that branch doesn't exist. |

---

## Steps Performed

### 1. Create a New GitHub Repository

Created a **public** repository named `devops-sample-code` with the description from the lab:

```bash
gh repo create devops-sample-code --public --description "A demo repository for Jenkins scripting."
```

```
https://github.com/gagandeepy080305/devops-sample-code
```

![Create GitHub Repository](./Screenshots/01%20Create%20GitHub%20Repository.png)

---

### 2. Create the Script Locally

```bash
touch hello-world.sh
```

Edited the file and added:

```bash
#!/bin/bash
echo "Hello, Jenkins!"
```

Made it executable:

```bash
chmod +x hello-world.sh
ls -l hello-world.sh
```

```
-rwxr-xr-x@ 1 gagandeepy  staff  35 Oct 13 18:17 hello-world.sh
```

---

### 3. Initialize a Local Git Repository and Commit

```bash
git init -b main
git config user.name "Gagandeep Y"
git config user.email "gagan080305@gmail.com"
git add hello-world.sh
git status
```

```
On branch main

No commits yet

Changes to be committed:
  (use "git rm --cached <file>..." to unstage)
	new file:   hello-world.sh
```

```bash
git commit -m "Add hello-world.sh"
```

```
[main (root-commit) 7c6e528] Add hello-world.sh
 1 file changed, 2 insertions(+)
 create mode 100755 hello-world.sh
```

---

### 4. Link to GitHub and Push

```bash
git remote add origin https://github.com/gagandeepy080305/devops-sample-code.git
git push -u origin main
```

```
To https://github.com/gagandeepy080305/devops-sample-code.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

![Create Script and Push to GitHub](./Screenshots/02%20Create%20Script%20and%20Push%20to%20GitHub.png)

---

### 5. Verify the Script on GitHub

The repository shows `hello-world.sh` with the commit **Add hello-world.sh** (`7c6e528`):

![GitHub Repository](./Screenshots/03%20GitHub%20Repository.png)

![hello-world.sh on GitHub](./Screenshots/04%20hello-world.sh%20on%20GitHub.png)

---

### 6. Access Jenkins

Opened `http://localhost:8080` and signed in as `admin`:

![Jenkins Sign In](./Screenshots/05%20Jenkins%20Sign%20In.png)

![Jenkins Dashboard](./Screenshots/06%20Jenkins%20Dashboard.png)

---

### 7. Create a New Job

**New Item** → name **`HelloWorld`** → **Freestyle project** → **OK**:

![New Item Freestyle Project](./Screenshots/07%20New%20Item%20Freestyle%20Project.png)

---

### 8. Configure the Job

**General:** description `Hello World! Jenkins job.`

![Configure General](./Screenshots/08%20Configure%20General.png)

**Source Code Management:** selected **Git** and entered the repository URL `https://github.com/gagandeepy080305/devops-sample-code.git`. No credentials are needed because the repository is public:

![Configure Source Code Management](./Screenshots/09%20Configure%20Source%20Code%20Management.png)

**Branches to build:** changed the Branch Specifier from the default `*/master` to **`*/main`**:

![Configure Branch to Build](./Screenshots/10%20Configure%20Branch%20to%20Build.png)

**Build Steps:** **Add build step → Execute shell** with:

```bash
sh hello-world.sh
```

![Configure Build Step](./Screenshots/11%20Configure%20Build%20Step.png)

Clicked **Save**.

---

### 9. Run the Job

On the job page, clicked **Build Now**. Build **#1** finished successfully (green check):

![Build Success](./Screenshots/12%20Build%20Success.png)

---

### 10. View the Build Output

**Build History → #1 → Console Output:**

```
Started by user admin
Running as SYSTEM
Building in workspace /var/jenkins_home/workspace/HelloWorld
The recommended git tool is: NONE
No credentials specified
Cloning the remote Git repository
Cloning repository https://github.com/gagandeepy080305/devops-sample-code.git
 > git init /var/jenkins_home/workspace/HelloWorld # timeout=10
Fetching upstream changes from https://github.com/gagandeepy080305/devops-sample-code.git
 > git --version # timeout=10
 > git --version # 'git version 2.47.3'
 > git fetch --tags --force --progress -- https://github.com/gagandeepy080305/devops-sample-code.git +refs/heads/*:refs/remotes/origin/* # timeout=10
 > git config remote.origin.url https://github.com/gagandeepy080305/devops-sample-code.git # timeout=10
 > git config --add remote.origin.fetch +refs/heads/*:refs/remotes/origin/* # timeout=10
Avoid second fetch
 > git rev-parse refs/remotes/origin/main^{commit} # timeout=10
Checking out Revision 7c6e528e011f8d550c645c0b753c6fc8ae44b09d (refs/remotes/origin/main)
 > git config core.sparsecheckout # timeout=10
 > git checkout -f 7c6e528e011f8d550c645c0b753c6fc8ae44b09d # timeout=10
Commit message: "Add hello-world.sh"
First time build. Skipping changelog.
[HelloWorld] $ /bin/sh -xe /tmp/jenkins9270178043081332376.sh
+ sh hello-world.sh
Hello, Jenkins!
Finished: SUCCESS
```

Jenkins cloned the repository, checked out commit `7c6e528` on `main`, ran `sh hello-world.sh`, and printed **Hello, Jenkins!**

![Console Output](./Screenshots/13%20Console%20Output.png)

---

## Screenshots

| # | Screenshot | Shows |
|---|-----------|-------|
| 1 | [Create GitHub Repository](./Screenshots/01%20Create%20GitHub%20Repository.png) | `gh repo create` creating the public repository |
| 2 | [Create Script and Push to GitHub](./Screenshots/02%20Create%20Script%20and%20Push%20to%20GitHub.png) | Script creation, `git init/add/status/commit`, `git push` |
| 3 | [GitHub Repository](./Screenshots/03%20GitHub%20Repository.png) | `devops-sample-code` on GitHub with `hello-world.sh` |
| 4 | [hello-world.sh on GitHub](./Screenshots/04%20hello-world.sh%20on%20GitHub.png) | Script contents on GitHub (executable file) |
| 5 | [Jenkins Sign In](./Screenshots/05%20Jenkins%20Sign%20In.png) | Jenkins sign-in page |
| 6 | [Jenkins Dashboard](./Screenshots/06%20Jenkins%20Dashboard.png) | Dashboard with *New Item* |
| 7 | [New Item Freestyle Project](./Screenshots/07%20New%20Item%20Freestyle%20Project.png) | `HelloWorld` with *Freestyle project* selected |
| 8 | [Configure General](./Screenshots/08%20Configure%20General.png) | Job description |
| 9 | [Configure Source Code Management](./Screenshots/09%20Configure%20Source%20Code%20Management.png) | Git with the repository URL |
| 10 | [Configure Branch to Build](./Screenshots/10%20Configure%20Branch%20to%20Build.png) | Branch Specifier `*/main` |
| 11 | [Configure Build Step](./Screenshots/11%20Configure%20Build%20Step.png) | *Execute shell*: `sh hello-world.sh` |
| 12 | [Build Success](./Screenshots/12%20Build%20Success.png) | HelloWorld job with successful build #1 |
| 13 | [Console Output](./Screenshots/13%20Console%20Output.png) | Clone, checkout, `Hello, Jenkins!`, `Finished: SUCCESS` |

---

## Q&A

**Q1: What is a Freestyle project in Jenkins?**
The classic, general-purpose Jenkins job type. It checks out code from one source repository, runs build steps one after another, and then runs post-build actions. Everything is configured in the web UI.

**Q2: Why does the job need Source Code Management?**
So Jenkins fetches the latest code from GitHub into the job's workspace before every build. The build step then runs the script from that fresh checkout.

**Q3: Why did the Branch Specifier have to be changed?**
Jenkins defaults to `*/master`, but this repository uses `main`. Building a branch that doesn't exist fails, so the specifier must match the repository's branch.

**Q4: Where does Jenkins run the build?**
In the job's workspace on the Jenkins controller: `/var/jenkins_home/workspace/HelloWorld`.

**Q5: How do you see the result of a build?**
Open the build from *Build History* (e.g. `#1`) and click *Console Output*. It shows every command Jenkins ran and the final status (`Finished: SUCCESS`).

---

## Result

Successfully created the **`hello-world.sh`** script, pushed it to the public GitHub repository **[devops-sample-code](https://github.com/gagandeepy080305/devops-sample-code)**, and created the **`HelloWorld` Freestyle job** in Jenkins.

The job cloned the repository, ran the script, and printed **`Hello, Jenkins!`** with **`Finished: SUCCESS`**.
