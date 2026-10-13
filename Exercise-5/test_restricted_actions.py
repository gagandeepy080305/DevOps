import docker

# Create a Docker client
client = docker.from_env()

# Run the container with the AppArmor profile
# Host port 5050 is used because macOS AirPlay Receiver already listens on port 5000
container = client.containers.run(
    "flask-apparmor",
    ports={'5000/tcp': 5050},
    security_opt=["apparmor=my-apparmor-profile"],
    detach=True
)
print(f"Container started: {container.short_id}\n")


def attempt(description, cmd):
    exit_code, output = container.exec_run(cmd)
    lines = output.decode().strip().splitlines()
    print(f"Attempt to {description}: Exit Code {exit_code}, Output: {lines[-1] if lines else ''}")


# Test restricted actions (from the lab)
attempt("read /etc/passwd", "cat /etc/passwd")
attempt("execute /bin/bash", "/bin/bash")

# Additional checks: actions performed by a process already confined by the profile
attempt("read /etc/passwd from Python", ["python", "-c", "open('/etc/passwd').read()"])
attempt("write to /var from Python", ["python", "-c", "open('/var/test.txt', 'w')"])
attempt("run /bin/ls from bash", ["/bin/bash", "-c", "ls /app"])
attempt("run /bin/ls from Python", ["python", "-c", "import subprocess; subprocess.run(['/bin/ls', '/app'])"])
attempt("write to /app (allowed)", ["python", "-c", "open('/app/test.txt', 'w').write('ok'); print('ok')"])

# Stop the container
container.stop()
container.remove()
print("\nContainer stopped")
