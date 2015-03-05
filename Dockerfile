FROM xdrum/nginx-extras:stable
MAINTAINER Lukas Hetzenecker <lukas.hetzenecker@gmail.com>

RUN apt-get update
RUN apt-get install -y --force-yes libpam-ldap nscd

# Install python packages
RUN apt-get install -y --force-yes python python-dev python-pip 
RUN apt-get install -y --force-yes libssl-dev libffi-dev
RUN apt-get install -y --force-yes libossp-uuid-perl
RUN pip install python-etcd
RUN pip install pystache
RUN pip install boto

# Remove default site
RUN rm -f /etc/nginx/sites-enabled/default

RUN mkdir /conf

# Add update script
ADD ./update.py /scripts/update.py
ADD ./templates /scripts/templates

# Run the boot script
CMD ["/usr/bin/python", "/scripts/update.py"]

