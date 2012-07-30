import heimdall
from heimdall import tasks
from heimdall import resources
from heimdall import supplies, demands
from heimdall.predicates import *

import json
from urllib import unquote_plus, quote_plus
import types

api_key = "78626d636d76696473706c"

tadb_api_base = "http://www.theaudiodb.com/api/v1/json/{0}/".format(api_key)
tadb_base = "http://www.theaudiodb.com/"

class ArtistPredicateObject(tasks.SubjectTask):
	demand = [
		demands.subject(tadb_base + "artist/")
	]

	supply = [
		supplies.emit(dc.title),
		supplies.emit(dc.description),
		supplies.emit(foaf.homepage),
		supplies.emit(foaf.thumbnail),
		supplies.emit("fanart")
	]

	def require(self):
		artistID = self.subject.uri[len(tadb_base + "artist/"):]
		return resources.SimpleResource("http://www.theaudiodb.com/api/v1/json/{0}/artist.php?i={1}".format(api_key, artistID))

	def run(self, resource):
		artist = json.loads(resource)["artists"][0]["artist"]

		self.subject.emit(dc.title, artist["strArtist"])
		self.subject.emit(dc.description, artist["strBiography"])
		self.subject.emit(foaf.homepage, artist["strWebsite"])
		self.subject.emit(foaf.homepage, artist["strFacebook"])
		self.subject.emit(foaf.homepage, artist["strTwitter"])

		self.subject.emit(foaf.thumbnail, artist["strArtistThumb"])

		self.subject.emit("fanart", artist["strArtistFanart"])
		self.subject.emit("fanart", artist["strArtistFanart2"])
		self.subject.emit("fanart", artist["strArtistFanart3"])

class AlbumPredicateObject(tasks.SubjectTask):
	demand = [
		demands.subject(tadb_base + "album/")
	]

	supply = [
		supplies.emit(dc.title),
		supplies.emit(dc.description),
		supplies.emit(dc.date),
		supplies.emit(foaf.thumbnail),
	]

	def require(self):
		albumID = self.subject.uri[len(tadb_base + "album/"):]
		return resources.SimpleResource("http://www.theaudiodb.com/api/v1/json/{0}/album.php?m={1}".format(api_key, albumID))

	def run(self, resource):
		print json.dumps(json.loads(resource), indent=4, sort_keys=True)
		album = json.loads(resource)["album"][0]["album"]

		self.subject.emit(dc.title, album["strAlbum"])
		self.subject.emit(dc.description, album["strDescription"])
		self.subject.emit(foaf.thumbnail, album["strAlbumThumb"])
		self.subject.emit(dc.date, album["intYearReleased"])

class SearchArtist(tasks.SubjectTask):
	demand = [
		demands.required(upnp.artist)
	]

	supply = [
		supplies.emit(upnp.artist, tadb_base + "artist/")
	]

	def require(self):
		artist = self.subject[upnp.artist]
		return resources.SimpleResource("http://www.theaudiodb.com/api/v1/json/{0}/search.php?s={1}".format(api_key, quote_plus(artist)))

	def run(self, resource):
		result = json.loads(resource)

		artists = result.get("artists", [])
		artists = artists if type(artists) == types.ListType else []

		for r in artists:
			artist = r["artist"]
			if "idArtist" in artist:
				self.subject.emit(upnp.artist, "{0}artist/{1}".format(tadb_base, artist["idArtist"]))

class SearchAlbum(tasks.SubjectTask):
	demand = [
		demands.required(upnp.artist),
		demands.required(upnp.album)
	]

	supply = [
		supplies.emit(upnp.album, tadb_base + "album/")
	]

	def require(self):
		artist = self.subject[upnp.artist]
		album = self.subject[upnp.album]

		path = "http://www.theaudiodb.com/api/v1/json/{0}/searchalbum.php?s={1}&a={2}".format(api_key, quote_plus(artist), quote_plus(album))

		return resources.SimpleResource(path)

	def run(self, resource):
		result = json.loads(resource)

		albums = result.get("album", [])
		albums = albums if type(albums) == types.ListType else []

		for r in albums:
			album = r["album"]
			if "idAlbum" in album:
				self.subject.emit(upnp.album, "{0}album/{1}".format(tadb_base, album["idAlbum"]))

module = [ SearchArtist, SearchAlbum, ArtistPredicateObject, AlbumPredicateObject ]
