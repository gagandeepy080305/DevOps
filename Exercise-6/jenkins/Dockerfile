FROM jenkins/jenkins:lts-jdk21

# Docker CLI so pipeline steps can run docker commands against the Docker engine (via the mounted socket)
USER root
ARG DOCKER_VERSION=27.5.1
RUN curl -fsSL "https://download.docker.com/linux/static/stable/$(uname -m)/docker-${DOCKER_VERSION}.tgz" \
    | tar -xz -C /usr/local/bin --strip-components=1 docker/docker
USER jenkins

# Pipeline plugins
RUN jenkins-plugin-cli --plugins workflow-aggregator pipeline-stage-view

# Local lab only: skip the setup wizard and create the pipeline job from /project/Jenkinsfile at startup
ENV JAVA_OPTS=-Djenkins.install.runSetupWizard=false
COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/
