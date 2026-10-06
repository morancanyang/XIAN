# syntax=docker/dockerfile:1
# 沙箱基础镜像：含 CJK 字体 + Python + Node，供场景模板实例化。
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8 \
    TZ=Asia/Shanghai

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        locales \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        curl \
        git \
    && sed -i '/zh_CN.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# 非 root 运行；真实隔离增强（gVisor runsc）在 M3 起由 K8s runtimeClass 指定
RUN useradd --system --create-home --uid 10003 sandbox

WORKDIR /sandbox
USER sandbox

CMD ["/bin/bash"]