FROM pytorch/pytorch:1.9.1-cuda11.1-cudnn8-devel

ENV TZ Asia/Seoul
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y vim tzdata

RUN ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
RUN ln -s /usr/bin/python3 /usr/bin/python 

WORKDIR /workspace
ADD . .

RUN pip install -r requirements.txt

RUN chmod +x /workspace/run_worker.sh
ENTRYPOINT ["sh","/workspace/run_worker.sh"]