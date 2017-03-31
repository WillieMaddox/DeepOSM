FROM python:3.4
ENV PYTHONUNBUFFERED 1
RUN mkdir /deeposmorg
WORKDIR /deeposmorg
ADD requirements.txt /deeposmorg/
RUN pip install -r requirements.txt
ADD . /deeposmorg/
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY