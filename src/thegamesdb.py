import heimdall
from heimdall import tasks
from heimdall import resources
from heimdall import supplies, demands
from heimdall.predicates import *

import json
import os, glob
import xml.etree.ElementTree as ET
import urllib
from urllib import unquote_plus, quote_plus

thegamesdb = PredicateBuilder("thegamesdb", "http://thegamesdb.net/#", [ "identifier", "platform" ])

tgdb_image_base = "http://thegamesdb.net/banners/"


class TranslatePlatform(tasks.SubjectTask):
    demand = [
        demands.required(game.platform)
    ]

    supply = [
        supplies.emit(thegamesdb.platform)
    ]

    def require(self):
        path = "http://thegamesdb.net/api/GetPlatformsList.php"
        return resources.SimpleResource(path)

    def run(self, resource):
        root = ET.fromstring(resource)
        gameRows = root.findall("Game")
        for gameRow in gameRows:
            element = gameRow.find('GameTitle')
            gameTitle = element.text if (element != None and element.text != None) else ''
            self.subject.emit(thegamesdb.platform, '')


class GamePredicateObject(tasks.SubjectTask):
    demand = [
        demands.required(thegamesdb.identifier, tmdb_base + "movie/")
    ]

    supply = [
        supplies.emit(dc.title),
        supplies.emit(dc.description),
        supplies.emit(owl.sameAs),
        supplies.emit(foaf.homepage),
        supplies.emit(foaf.thumbnail),
        supplies.emit("fanart")
    ]

    def require(self):
        uri = self.subject[dc.identifier]
        ID = uri[len(tmdb_base + "movie/"):]

        return [
            resources.SimpleResource(tmdb_api_base + "/configuration?api_key=57983e31fb435df4df77afb854740ea9"),
            resources.SimpleResource(tmdb_api_base + "movie/" + ID + "?api_key=57983e31fb435df4df77afb854740ea9")
        ]

    def run(self, configuration, resource):
        c = json.loads(configuration)
        movie = json.loads(resource)

        self.subject.emit(dc.title, movie["original_title"])
        self.subject.emit(dc.description, movie["overview"])
        self.subject.emit(owl.sameAs, "http://www.imdb.com/title/" + movie["imdb_id"])
        self.subject.emit(foaf.homepage, movie["homepage"])

        images = c["images"]
        image_base = images["base_url"]

        for size in images["poster_sizes"]:
            self.subject.emit(foaf.thumbnail, image_base + size + movie["poster_path"])

        for size in images["backdrop_sizes"]:
            self.subject.emit("fanart", image_base + size + movie["poster_path"])



def downloadArtwork(url, folder, title):
    searchPath = os.path.join(folder, title +".*")
    #TODO glob has some limitations (i.e. issues with [])
    files = glob.glob(searchPath)
    if(len(files) == 0):
        fileExtension = os.path.splitext(url)[1]
        newFile = os.path.join(folder, "%s%s" %(title, fileExtension))
        print "File does not exist. Start download: " +newFile
        
        try:
            urllib.urlretrieve( url, newFile)
        except Exception, (exc):
            print "Could not create file: '%s'. Error message: '%s'" %(newFile, str(exc))
    else:
        print "File already exist. Won't download artwork for " +title


class DownloadBoxfront(tasks.SubjectTask):
    demand = [
        demands.required("Filetypeboxfront")
    ]
    
    supply = []

    def run(self):
        print 'Download boxfront: ' +self.subject["Filetypeboxfront"]
        url = tgdb_image_base + self.subject["Filetypeboxfront"]
        folder = self.subject["pathboxfront"]
        title = self.subject[dc.title]
        
        downloadArtwork(url, folder, title)
        

class DownloadFanart(tasks.SubjectTask):
    demand = [
        demands.required("Filetypefanart")
    ]
    
    supply = []

    def run(self):
        print 'Download fanart: ' +self.subject["Filetypefanart"]
        
        url = tgdb_image_base + self.subject["Filetypefanart"]
        folder = self.subject["pathfanart"]
        title = self.subject[dc.title]
        
        downloadArtwork(url, folder, title)
        

class SearchGameCollector(tasks.SubjectTask):
    demand = [
        demands.required(dc.title),
        demands.requiredClass("item.game"),
        demands.required(game.platform)
    ]

    supply = [
        supplies.emit(dc.description)
        #supplies.emit("Filetypeboxfront"),
        #supplies.emit("Filetypefanart")
    ]

    def require(self):
        title = self.subject[dc.title]
        platform = self.subject[game.platform]
        path = "http://thegamesdb.net/api/GetGame.php?name=%s&platform=%s" % (quote_plus(title), quote_plus(platform))
        return resources.SimpleResource(path)

    def run(self, resource):
        root = ET.fromstring(resource)
        gameRows = root.findall("Game")
        for gameRow in gameRows:
            element = gameRow.find('GameTitle')
            gameTitle = element.text if (element != None and element.text != None) else ''
            
            #TODO name guessing
            if (gameTitle == self.subject[dc.title]):
                gameid = self.readTextElement(gameRow, 'id')
                print "found match: id = %s" % gameid
                self.subject.emit('gameid', gameid)
                self.subject.emit(dc.description, self.readTextElement(gameRow, 'Overview'))
                self.subject.emit('Genre', self.readTextElement(gameRow, 'Genres/genre'))
                self.subject.emit('Players', self.readTextElement(gameRow, 'Players'))
                self.subject.emit('Developer', self.readTextElement(gameRow, 'Developer'))
                self.subject.emit('Publisher', self.readTextElement(gameRow, 'Publisher'))
                self.subject.emit('ReleaseYear', self.readTextElement(gameRow, 'ReleaseDate'))
                
                boxartRows = gameRow.findall('Images/boxart')
                for boxartRow in boxartRows:
                    side = boxartRow.attrib.get('side')
                    if(side == 'front'):
                        self.subject.emit('Filetypeboxfront', self.readTextElement(boxartRow, ""))
                                
                self.subject.emit('Filetypefanart', self.readTextElement(gameRow, 'Images/fanart/original'))
                break
            
    
module = [ SearchGameCollector, DownloadBoxfront, DownloadFanart ]
