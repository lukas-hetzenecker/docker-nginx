import os
import etcd
import pystache
import boto.route53.connection
import urllib3.exceptions

HOST = os.environ.get('HOST', '127.0.0.1')
PUBLIC_IP = os.environ.get('PUBLIC_IP')
DOMAIN = os.environ.get('DOMAIN')
ACCESS_KEY = os.environ.get('ACCESS_KEY')
SECRET_KEY = os.environ.get('SECRET_KEY')

assert DOMAIN

os.system('service nginx start')

etcd_client = etcd.Client(host=HOST)
if ACCESS_KEY and SECRET_KEY:
   assert PUBLIC_IP
   route53_client = boto.route53.connection.Route53Connection(ACCESS_KEY, SECRET_KEY)
   route53_zone = route53_client.get_zone(DOMAIN)

def reload():
   os.system('service nginx reload')

def publish(entry):
   if entry.dir:
      return

   service = entry.key.split('/')[-1]
   name = entry.value
   servername = name + '.' + DOMAIN
   if servername == '':
      servername = DOMAIN

   print "Publishing service '%s'..." % service

   try:
      service_host = etcd_client.get('/services/%s/host' % service).value
      service_port = etcd_client.get('/services/%s/port' % service).value
   except KeyError as e:
      print "Could not publish '%s': %s" % (service, e)
      return

   try:
      nginx_template = etcd_client.get('/services/%s/nginx_template' % service).value
   except KeyError as e:
      nginx_template = 'default'

   try:
      nginx_protocol = etcd_client.get('/services/%s/nginx_protocol' % service).value
   except KeyError as e:
      nginx_protocol = 'http'

   try:
      enable_socketio = bool(etcd_client.get('/services/%s/nginx_enable_socketio' % service).value)
   except KeyError as e:
      enable_socketio = False

   data = {
      'name': service,
      'protocol': nginx_protocol,
      'upstream': service_host + ':' + service_port,
      'server_name': name + '.' + DOMAIN,
      'socketio': enable_socketio
   }

   nginx_template = nginx_template.replace('.', '').replace('/', '')
   template = file('/scripts/templates/%s.tmpl' % nginx_template, 'r').read()
   rendered = pystache.render(template, data)

   nginx_file = file('/etc/nginx/sites-enabled/%s.conf' % service, 'w')
   nginx_file.write(rendered)
   nginx_file.close()

   reload()

   if ACCESS_KEY and SECRET_KEY:
      domainname = servername + '.'
      print "Adding A record for %s" % domainname
      try:
         route53_zone.delete_a(domainname)
         print "Deleted old record"
      except Exception as e:
         pass
      try:
         route53_zone.add_a(domainname, PUBLIC_IP, comment = 'generated by docker-nginx')
      except Exception as e:
         print "Failed: %s" % e

def unpublish(entry):
   service = entry.key.split('/')[-1]
   name = entry._prev_node.value
   servername = name + '.' + DOMAIN

   nginx_file = '/etc/nginx/sites-enabled/%s.conf' % service

   print "Unpublishing service '%s'..." % service

   if os.path.exists(nginx_file):
      os.remove(nginx_file)
      reload()

   if ACCESS_KEY and SECRET_KEY:
      domainname = servername + '.'
      print "Deleting A record for %s" % domainname
      try:
         route53_zone.delete_a(domainname)
      except Exception as e:
         print "Failed: %s" % e

# Unfortunately locking is not possible yet

try:
   to_publish = etcd_client.read('/publish')
   map(publish, to_publish.children)
except KeyError:
   pass

while True:
   try:
      entry = etcd_client.read("/publish", recursive=True, wait=True, timeout=0)
   except (urllib3.exceptions.ReadTimeoutError, etcd.EtcdException):
      continue

   if entry.action == 'set':
      publish(entry)
   elif entry.action == 'delete':
      unpublish(entry)

