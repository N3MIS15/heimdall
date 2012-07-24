import heimdall
from heimdall import tasks
from heimdall import resources
from heimdall import supplies, demands
from heimdall.predicates import *

import json
from urllib import unquote_plus, quote_plus
from urlparse import urlsplit
import os

mime_types = {
	".mkv": "video/x-matroska",
	".avi": "video/avi"
}

mime_type_to_class = {
	"video/x-matroska": "item.media.video"
}

class ItemPredicateObject(tasks.SubjectTask):
	demand = [
		demands.subject("^file://")
	]

	supply = [
		supplies.emit(rdf.Class, "item"),
		supplies.emit(rdf.Class, "item.media"),
		supplies.emit(dc.title),
		supplies.emit(dc.format)
	]

	def run(self):
		path = urlsplit(self.subject.uri).path
		ext = path[path.rindex("."):].lower()
		mime_type = mime_types.get(ext, None)

		title = os.path.basename(path)[ : path.rindex(".") - len(path)]
		title = title.replace(".", " ")

		self.subject.emit(dc.title, title)
		self.subject.emit(dc.format, mime_type)

		self.subject.Class = mime_type_to_class.get(mime_type, "item.media")

class ChangeVideoToMovie(tasks.SubjectTask):
	demand = [
		demands.requiredClass("item.media.video")
	]

	supply = [
		supplies.replace(rdf.Class, "item.media.video.Movie"),
	]

	def run(self):
		self.subject.Class = "item.media.video.Movie"

module = [ ItemPredicateObject, ChangeVideoToMovie ]
