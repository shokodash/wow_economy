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
        
        if "icon" in data:
            setattr(self, "icon", data["icon"])
        else:
            setattr(self, "icon", "inv_engineering_sonicenvironmentenhancer")
        for x in ("name", "description", "buyPrice", "sellPrice", "quality", "itemLevel"):
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
            if hasattr(e,"code"):
                if e.code == 503:
                    raise UnavailableError()
            return None
        
        try:
            d = json.loads(r.read(), encoding="utf-8")          #   <type 'dict'>
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
        r = self.get_content("https://eu.api.battle.net/wow/item/%s?locale=en_GB&apikey=ncfqkhsgnytx86tscw8n8z2e5bmduauj"%id)
        if not r:
            return None
        
        return Item(r)
    
    def get_realms(self):
        r = self.get_content("https://eu.api.battle.net/wow/realm/status?locale=en_GB&apikey=ncfqkhsgnytx86tscw8n8z2e5bmduauj")
        if not r: 
            return None
        return [Realm(d) for d in r["realms"]]
    
    def get_auction(self, realm, last_timestamp):
        r = self.get_content("https://eu.api.battle.net/wow/auction/data/"+realm+"?locale=en_GB&apikey=ncfqkhsgnytx86tscw8n8z2e5bmduauj") # <type 'dict'>
        if r == None: 
            raise Exception()
        d = r["files"][0]                               #  <type 'dict'>
        if (d["lastModified"] / 1000) > last_timestamp:
            # We have a hit, fetch and return
            return d["lastModified"], self.get_content(d["url"])
        else:
            return None, None # Same data