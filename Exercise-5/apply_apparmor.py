import docker

# Create a Docker client
client = docker.from_env()

# Build the Docker image
print("Building image from Dockerfile...")
image, logs = client.images.build(path=".", tag="flask-apparmor")
for chunk in logs:
    line = chunk.get("stream", "").strip()
    if line.startswith(("Step", "Successfully")):
        print(f"[INFO] {line}")

# Run the container with the AppArmor profile
# Host port 5050 is used because macOS AirPlay Receiver already listens on port 5000
print("\nRunning container with AppArmor profile...")
container = client.containers.run(
    "flask-apparmor",
    ports={'5000/tcp': 5050},
    security_opt=["apparmor=my-apparmor-profile"],
    detach=True
)

print(f"Container started: {container.short_id}")

# Verify AppArmor profile applied
print("\nInspecting container to verify AppArmor profile...")
container_info = client.api.inspect_container(container.id)
apparmor_profile = container_info['HostConfig']['SecurityOpt']

print(f"AppArmor profile applied: {apparmor_profile}")
print(f"Active AppArmor profile: {container_info['AppArmorProfile']}")

# Stop the container
print("\nStopping the container...")
container.stop()
container.remove()
print("Container stopped and removed")
