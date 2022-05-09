FROM jrottenberg/ffmpeg:4.3.3-nvidia2004

ENV TZ Asia/Seoul
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A4B469963BF863CC
RUN apt update \
    && apt install -y vim tzdata python3-pip

RUN ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
RUN ln -s /usr/bin/python3 /usr/bin/python 

WORKDIR /workspace
ADD . .


RUN pip install -r requirements.txt



RUN chmod +x /workspace/run_worker.sh
ENTRYPOINT ["sh","/workspace/run_worker.sh"]
