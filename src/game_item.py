import heimdall
from heimdall import tasks
from heimdall import resources
from heimdall import supplies, demands
from heimdall.predicates import *

import re
import urlparse

game = PredicateBuilder("game", "http://purl.org/game#", [ "platform", "developer", "publisher", "players", "code", "region" ])

def comparePlatforms(platform1, platform2):
    platform1 = re.sub("[^a-z0-9 ]", "", platform1.lower())
    platform2 = re.sub("[^a-z0-9 ]", "", platform2.lower())
    if platform1 == platform2:
        return True

    # Don't want "nintendo entertainment system" to match "super nintendo entertainment system"
    SNES = re.compile("((^|[^a-z])snes([^a-z]|$)|super nintendo)")
    if SNES.match(platform1) or SNES.match(platform2):
        return SNES.match(platform1) and SNES.match(platform2)

    NES = re.compile("((^|[^a-z])nes([^a-z]|$)|nintendo entertainment system)")
    if NES.match(platform1):
        return NES.match(platform2)
    elif NES.match(platform2):
        return NES.match(platform1)

    for company in ["microsoft", "nintendo", "sega", "sony"]:
        if platform1.startswith(company):
            platform1 = platform1[len(company):].strip()
        if platform2.startswith(company):
            platform2 = platform2[len(company):].strip()

    aliases = {
        "atari xe": "atari 8bit",
        "c64":       "commodore 64",
        "osx":       "max os",
        "n64":       "64", # nintendo was stripped
        "nds":       "ds",
        "ndsi":      "dsi",
        "gb":        "game boy",
        "gba":       "game boy advance",
        "gbc":       "game boy color",
        "gcn":       "gamecube",
        "ngc":       "gamecube",
        "sms":       "master system",
        "ps":        "playstation",
        "ps2":       "playstation 2",
        "ps3":       "playstation 3",
        "ps4":       "playstation 4",
        "vita":      "playstation vita",
        "psp":       "playstation portable",
        "sgb":       "super game boy",
    }

    if platform1 in aliases:
        platform1 = aliases[platform1]
    if platform2 in aliases:
        platform2 = aliases[platform2]
    # Finally, compare without spaces so that "game boy" matches "gameboy"
    return platform1.replace(" ", "") == platform2.replace(" ", "")


class ResolvePlatform(tasks.SubjectTask):
    demand = [
        demands.required(dc.identifier),
        demands.requiredClass("item"),
    ]

    supply = [
        supplies.ugpradeClass("item.game"), # NOT IMPLEMENTED YET
        supplies.replace(rdf.Class, "item.game"),
        supplies.emit(game.platform),
    ]

    def run(self):
        path = urlparse.urlparse(self.subject[dc.identifier]).path
        ext = path[path.rindex("."):].lower()
        platform = None

        self.subject.extendClass("item.game")
        self.subject.replace(rdf.Class, "item.game") # If a workaround is needed for supplies.ugpradeClass

        if ext in [".gb"]:
            platform = "Game Boy"
        elif ext in [".gbc", ".cgb", ".sgb"]:
            platform = "Game Boy Color"
        elif ext in [".gba", ".agb"]:
            platform = "Game Boy Advance"
        if platform is not None:
            self.subject.emit(game.platform, platform)

module = [ ResolvePlatform ]
