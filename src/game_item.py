import heimdall
from heimdall import tasks
from heimdall import resources
from heimdall import supplies, demands
from heimdall.predicates import *

class ResolvePlatform(tasks.SubjectTask):
    demand = [
        demands.required(dc.identifier, "^(/|file://)"),
        demands.requiredClass("item"),
    ]

    supply = [
        supplies.replace(rdf.Class, "item.game"),
        supplies.emit(game.platform),
    ]

    def run(self):
        path = self.subject[dc.identifier]
        ext = path[path.rindex("."):].lower()
        platform = None

        if ext in [".gb"]:
            platform = "Game Boy"
        elif ext in [".gbc", ".cgb", ".sgb"]:
            platform = "Game Boy Color"
        elif ext in [".gba", ".agb"]:
            platform = "Game Boy Advance"
        if platform is not None:
            self.subject.emit(game.platform, platform)


module = [ ResolvePlatform ]
