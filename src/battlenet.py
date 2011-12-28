#import requests
import urllib2
import json
import traceback

class Realm(object):
    def __init__(self, data):
        for i in ("type","queue","status","population","name","battlegroup","slug"):
            setattr(self, i, data[i])
            
    def __repr__(self):
        return "<Realm(%s,%s)>"%(self.name, self.slug)
    
class Item(object):
    def __init__(self, data):
        self._auctionID = None
        
        for x in ("name", "description", "icon", "buyPrice", "sellPrice", "quality", "itemLevel"):
            setattr(self, x, data[x])
    
    def __repr__(self):
        return "<Item(%s,%s,%s)>"%(self.name, self.icon, self.quality)
    
class UnavailableError(Exception):
    pass

class BattleNetApi(object):
    def __init__(self, logfunc):
        self.logger = logfunc
        
    def get_content(self, url):
        try:
            #r = requests.get(url)
            r = urllib2.urlopen(url)
        except Exception,e:
            self.logger("Request to %s failed. Traceback:"%url)
            self.logger(traceback.format_exc())
            if e.code == 503:
                raise UnavailableError()
            return None
        
        try:
            d = json.loads(r.read(), encoding="utf-8")#.encode("utf-8"))
        except Exception:
            self.logger("Invalid json detected @ %s"%url)
            self.logger("Status: %s, Final URL: %s"%(r.code, r.geturl()))
            self.logger(traceback.format_exc())
            return None
        
        if "status" in d:
            if d["status"] == "nok":
                self.logger("WOW API failed @ %s"%url)
                self.logger("Reason: %s"%(d["reason"]))
                return None
        return d
    
    def get_item(self, id):
        r = self.get_content("http://eu.battle.net/api/wow/item/%s"%id)
        if not r:
            return None
        
        return Item(r)
    
    def get_realms(self):
        r = self.get_content("http://eu.battle.net/api/wow/realm/status")
        if not r: 
            return None
        return [Realm(d) for d in r["realms"]]
    
    def get_auction(self, realm, last_timestamp):
        r = self.get_content("http://eu.battle.net/api/wow/auction/data/"+realm)
        if r == None: 
            raise Exception()
        d = r["files"][0]
        
        if (d["lastModified"] / 1000) > last_timestamp:
            # We have a hit, fetch and return
            return d["lastModified"], self.get_content(d["url"])
        else:
            return None, None # Same data