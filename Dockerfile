FROM ubuntu:14.04
MAINTAINER Lukas Hetzenecker <lukas.hetzenecker@gmail.com>

RUN apt-get update

# Install Nginx
RUN apt-get install -y --force-yes nginx

# Install python-etcd and pystache
RUN apt-get install -y --force-yes python python-dev python-pip 
RUN apt-get install -y --force-yes libssl-dev libffi-dev
RUN pip install python-etcd
RUN pip install pystache

# Remove default site
RUN rm -f /etc/nginx/sites-enabled/default

# Add update script
ADD ./update.py /scripts/update.py
ADD ./templates /scripts/

# Run the boot script
CMD ["/usr/bin/python", "/scripts/update.py"]

