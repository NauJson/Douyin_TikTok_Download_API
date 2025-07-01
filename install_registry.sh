#!/bin/bash

set -e

echo "1. 创建数据目录 /opt/registry/data"
mkdir -p /opt/registry/data

echo "2. 拉取 registry 镜像"
docker pull registry:2

echo "3. 启动 registry 容器"
docker stop registry 2>/dev/null || true
docker rm registry 2>/dev/null || true
docker run -d \
  --name registry \
  -p 5000:5000 \
  --restart=always \
  -v /opt/registry/data:/var/lib/registry \
  registry:2

echo "4. 配置 Docker 信任私有仓库"
if [ -f /etc/docker/daemon.json ]; then
  grep '192.168.31.250:5000' /etc/docker/daemon.json || \
  sed -i 's/}/, "insecure-registries": ["192.168.31.250:5000"]}/' /etc/docker/daemon.json
else
  echo '{"insecure-registries": ["192.168.31.250:5000"]}' > /etc/docker/daemon.json
fi

echo "5. 重启 Docker 服务"
if command -v systemctl >/dev/null 2>&1; then
  systemctl restart docker
elif command -v service >/dev/null 2>&1; then
  service docker restart
elif [ -x /etc/init.d/docker ]; then
  /etc/init.d/docker restart
else
  echo "请手动重启 Docker 服务：如 'service docker restart' 或 'rc-service docker restart'"
fi

echo "6. 查看 registry 容器状态"
docker ps | grep registry

echo "私有镜像仓库已搭建完成！"
echo "推送镜像示例："
echo "  docker tag your-image:tag 192.168.31.250:5000/your-image:tag"
echo "  docker push 192.168.31.250:5000/your-image:tag"
echo "拉取镜像示例："
echo "  docker pull 192.168.31.250:5000/your-image:tag" 