#!/bin/bash
set -euxo pipefail

# Install Docker
dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user

# Install Docker Compose plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Create 1GB swap (t3.micro has only 1GB RAM)
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab

# Clone the repo
su - ec2-user -c "git clone https://github.com/mrazzini/fineas.git ~/fineas"
