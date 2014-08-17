import os
import etcd
import pystache

# Unfortunately locking is not possible yet

HOST = os.environ.get('HOST', '127.0.0.1')
DOMAIN = os.environ.get('DOMAIN')

assert DOMAIN

os.system('service nginx start')

client = etcd.Client(host=HOST)

def reload():
   os.system('service nginx reload')

def publish(entry):
   service = entry.key.split('/')[-1]
   name = entry.value

   print "Publishing service '%s'..." % service

   try:
      service_host = client.get('/services/%s/host' % service).value
      service_port = client.get('/services/%s/port' % service).value
   except KeyError as e:
      print "Could not publish '%s': %s" % (service, e)
      return

   try:
      nginx_template = client.get('/services/%s/nginx_template' % service)
   except KeyError as e:
      nginx_template = 'default'

   data = {
      'name': service,
      'upstream': service_host + ':' + service_port,
      'server_name': name + '.' + DOMAIN
   }

   nginx_template = nginx_template.replace('.', '').replace('/', '')
   template = file('templates/%s.tmpl' % nginx_template, 'r').read()
   rendered = pystache.render(template, data)

   nginx_file = file('/etc/nginx/sites-enabled/%s.conf' % service, 'w')
   nginx_file.write(rendered)
   nginx_file.close()

   reload()

def unpublish(entry):
   service = entry.key.split('/')[-1]
   nginx_file = '/etc/nginx/sites-enabled/%s.conf' % service

   print "Unpublishing service '%s'..." % service

   if os.path.exists(nginx_file):
      os.remove(nginx_file)
      reload()

try:
   to_publish = client.read('/publish')
   map(publish, to_publish.children)
except KeyError:
   pass

while True:
   entry = client.read("/publish", recursive=True, wait=True, timeout=0)
   if entry.action == 'set':
      publish(entry)
   elif entry.action == 'delete':
      unpublish(entry)

