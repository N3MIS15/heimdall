import heimdall
from heimdall import tasks
from heimdall import resources
from heimdall import supplies, demands
from heimdall.predicates import *

from game_item import game, comparePlatforms

import datetime
import difflib
import os, glob
import urllib
from urllib import quote_plus
import xml.etree.ElementTree as ET

thegamesdb = PredicateBuilder("thegamesdb", "http://thegamesdb.net/#", [ "identifier", "platform" ])

baseImageUrl = "http://thegamesdb.net/banners/"

class TranslatePlatform(tasks.SubjectTask):
    demand = [
        demands.required(game.platform)
    ]

    supply = [
        supplies.emit(thegamesdb.platform)
    ]

    def require(self):
        path = "http://thegamesdb.net/api/GetPlatformsList.php"
        return resources.CachedSimpleResource(path)

    def run(self, resource):
        root = ET.fromstring(resource)
        for platform in root.findall("Platforms/Platform"):
            nametag = platform.find("name")
            if nametag == None or nametag.text == None:
                continue
            if comparePlatforms(nametag.text, self.subject[game.platform]):
                self.subject.emit(thegamesdb.platform, nametag.text)
                break

def downloadArtwork(url, folder, title):
    searchPath = os.path.join(folder, title + ".*")
    #TODO glob has some limitations (i.e. issues with [])
    files = glob.glob(searchPath)
    if len(files) == 0:
        fileExtension = os.path.splitext(url)[1]
        newFile = os.path.join(folder, "%s%s" % (title, fileExtension))
        print "File does not exist. Start download: " + newFile
        try:
            urllib.urlretrieve(url, newFile)
        except Exception, (exc):
            print "Could not create file: '%s'. Error message: '%s'" % (newFile, str(exc))
    else:
        print "File already exist. Won't download artwork for " + title

class DownloadBoxfront(tasks.SubjectTask):
    demand = [
        demands.required(dc.title),
        demands.required(foaf.thumbnail),
        demands.required("pathboxfront"),
    ]

    supply = [ ]

    def run(self):
        print 'Download boxfront: ' + self.subject[foaf.thumbnail]
        url = baseImageUrl + self.subject[foaf.thumbnail]
        folder = self.subject["pathboxfront"]
        title = self.subject[dc.title]
        downloadArtwork(url, folder, title)

class DownloadFanart(tasks.SubjectTask):
    demand = [
        demands.required(dc.title),
        demands.required("fanart"),
        demands.required("pathfanart"),
    ]

    supply = [ ]

    def run(self):
        print 'Download fanart: ' + self.subject["fanart"]
        url = baseImageUrl + self.subject["fanart"]
        folder = self.subject["pathfanart"]
        title = self.subject[dc.title]
        downloadArtwork(url, folder, title)

class GamePredicateObject(tasks.SubjectTask):
    demand = [
#        demands.required(thegamesdb.identifier, "http://thegamesdb.net/api/GetGame.php?id=")
        demands.required(dc.title),
        demands.requiredClass("item.game"),
        demands.required(thegamesdb.platform)
    ]

    supply = [
        supplies.emit(thegamesdb.identifier),
        supplies.replace(dc.title),
        supplies.emit(dc.type),
        supplies.emit(dc.description),
        supplies.emit(dc.date),
        supplies.emit(media.rating),
        supplies.emit(game.developer),
        supplies.emit(game.publisher),
        supplies.emit(game.players),
        supplies.emit(foaf.thumbnail),
        supplies.emit("fanart"),
        supplies.emit("banner"),
        supplies.emit(video.trailer),
    ]

    def require(self):
        title = self.subject[dc.title]
        platform = self.subject[thegamesdb.platform]
        path = "http://thegamesdb.net/api/GetGame.php?name=%s&platform=%s" % (quote_plus(title), quote_plus(platform))
        return resources.SimpleResource(path)

    def run(self, resource):
        root = ET.fromstring(resource)
        gameRows = root.findall("Game")

        # TheGamesDB has search ordering problems. Sucks for XML scrapers... not for us!
        possibilities = [self.readTextElement(gameRow, "GameTitle") for gameRow in gameRows]
        gameTitle = difflib.get_close_matches(self.subject[dc.title], possibilities, 1)
        if gameTitle:
            gameTitle = gameTitle[0]
            for gameRow in gameRows:
                if gameTitle != self.readTextElement(gameRow, "GameTitle"):
                    continue
                gameid = self.readTextElement(gameRow, "id")
                self.subject.emit(thegamesdb.identifier, "http://thegamesdb.net/api/GetGame.php?id=%s" % gameid)
                self.subject.replace(dc.title, gameTitle)
                for genre in gameRow.findall("Genres/genre"):
                    self.subject.emit(dc.type, genre.text)
                self.subject.emit(dc.description, self.readTextElement(gameRow, "Overview"))
                try:
                    # Deserialize MM/DD/YYYY
                    dateobject = datetime.datetime.strptime(self.readTextElement(gameRow, "ReleaseDate"), "%m/%d/%Y")
                    self.subject.emit(dc.date, dateobject.strftime("%Y-%m-%d"))
                except ValueError:
                    # can't be parsed by strptime()
                    pass
                self.subject.emit(media.rating, self.readTextElement(gameRow, 'ESRB'))
                self.subject.emit(game.developer, self.readTextElement(gameRow, 'Developer'))
                self.subject.emit(game.publisher, self.readTextElement(gameRow, 'Publisher'))
                self.subject.emit(game.players, self.readTextElement(gameRow, 'Players'))

                for boxartRow in gameRow.findall('Images/boxart'):
                    side = boxartRow.attrib.get('side')
                    if side == 'front' and boxartRow.text:
                        self.subject.emit(foaf.thumbnail, baseImageUrl + boxartRow.text)
                for fanartRow in gameRow.findall('Images/fanart'):
                    original = self.readTextElement(fanartRow, 'original')
                    if original:
                        thumb = self.readTextElement(fanartRow, 'thumb')
                        if thumb:
                            self.subject.emit("fanart", {"fanart": baseImageUrl + original, "thumbnail": baseImageUrl + thumb})
                        else:
                            self.subject.emit("fanart", baseImageUrl + original)
                for bannerRow in gameRow.findall('Images/banner'):
                    self.subject.emit("banner", baseImageUrl + bannerRow.text)
                self.subject.emit(video.trailer, self.readTextElement(gameRow, 'Youtube'))

    def readTextElement(self, parent, elementName):
        element = parent.find(elementName)
        if element != None and element.text != None:
            return element.text
        else:
            return ''

module = [ TranslatePlatform, GamePredicateObject, DownloadBoxfront, DownloadFanart ]
