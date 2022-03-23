FROM nvidia/cuda:11.1-cudnn8-devel-ubuntu20.04

ENV TZ Asia/Seoul
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y vim python3-pip python3-dev tzdata openssh-server libmysqlclient-dev

RUN ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
RUN ln -s /usr/bin/python3 /usr/bin/python 
RUN echo "root:root" | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config


WORKDIR /workspace
ADD . .

RUN pip install setuptools==59.6.0
RUN pip install -r requirements.txt

RUN chmod +x /workspace/script/entrypoint.sh
ENTRYPOINT ["sh","/workspace/script/entrypoint.sh"]
