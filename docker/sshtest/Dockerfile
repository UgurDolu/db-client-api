FROM ubuntu:22.04

# Install OpenSSH Server and required packages
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    openssh-server \
    iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /var/run/sshd

# SSH configuration
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#ListenAddress 0.0.0.0/ListenAddress 0.0.0.0/' /etc/ssh/sshd_config && \
    echo "AllowUsers testuser" >> /etc/ssh/sshd_config

# Create test user
ENV SSH_USER=testuser
ENV SSH_PASSWORD=testpass

RUN useradd -m -d /home/${SSH_USER} -s /bin/bash ${SSH_USER} && \
    echo "${SSH_USER}:${SSH_PASSWORD}" | chpasswd && \
    mkdir -p /home/${SSH_USER}/.ssh && \
    chmod 700 /home/${SSH_USER}/.ssh && \
    chown -R ${SSH_USER}:${SSH_USER} /home/${SSH_USER}/.ssh

# Create shared directory
RUN mkdir -p /home/${SSH_USER}/shared && \
    chown ${SSH_USER}:${SSH_USER} /home/${SSH_USER}/shared

# Generate host keys
RUN ssh-keygen -A

# Expose SSH port
EXPOSE 22

# Start SSH server with verbose logging
CMD ["/usr/sbin/sshd", "-D", "-e"] 