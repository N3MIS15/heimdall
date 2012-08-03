import tasks
from utils import SimpleCache
try:
	import requests
	def vfs_read(uri):
		return requests.get(uri).content
except:
	import urllib
	def vfs_read(uri):
		return urllib.urlopen(uri).read()

class Resource(tasks.Task):
	def __init__(self, uri):
		self.uri = uri

	def run(self):
		return self

	def read(self):
		return vfs_read(self.uri)

class SimpleResource(tasks.Task):
	cache = SimpleCache()

	def __init__(self, uri):
		self.uri = uri
		self.data = None

	def require(self):
		return Resource(self.uri)

	def run(self, resource):
		factory = lambda : resource.read()
		return SimpleResource.cache.get(self.uri, factory)
