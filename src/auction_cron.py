# Auctioncron.py
# Gets new auctions, processes them and updates the database. To be ran as a cron job.

import lockfile
import sys
if __name__ == '__main__':
    lock = lockfile.LockFile("auctioncron.lock")
    while not lock.i_am_locking():
        try:
            print "Getting the lock..."
            lock.acquire(timeout=60)
            print "Lock acquired"
        except lockfile.LockTimeout:
            print "Could not get the lock in 60 seconds, exiting."
            sys.exit(1)

import models
import battlenet
import time
import os
import multiprocessing.pool
import json
import datetime
from numpy import array as nparray
from sqlalchemy import exc
from pprint import pprint as pp
import wow_eco_funcs
#from sqlalchemy.orm.exc import NoResultFound

#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

def log(message):
    # Quick and dirty.
    #sys.stdout.write("%s: %s\n"%(time.asctime(), message))
    print (u"%s: %s"%(time.asctime(), message)).encode("utf-8")
        

def HandleRealm(realm):
    api = battlenet.BattleNetApi(log)                               # <class 'battlenet.BattleNetApi'> 
        # api.logger = log              
    
    log("Connecting to the database...")
    session = models.Session()
    log("Connection successful. ")
    
    log(" - Getting realm: %s"%realm)
    try:
        db_realm = session.query(models.Realm).filter(models.Realm.slug == realm.slug).with_lockmode("read").one()
    except exc.DBAPIError:
        log("  - Could not get the realm, task already running!")
        session.close()
        return None
    except Exception:
        db_realm = models.Realm(realm.name, realm.slug)         # db_realm.lastupdate = 0
        session.add(db_realm)
        session.commit()
    
    log("  - DB LastModified: %s"%time.ctime(db_realm.lastupdate))
    
    for i in xrange(5):
        try:
            lastModified, auctions = api.get_auction(realm.slug, db_realm.lastupdate)
            break
        except Exception:
            if i == 4:
                log("   - Not attempting again, returning.")
                return
            log("   - Attempting again...")
    
    if (lastModified, auctions) == (None, None):
        log("   - Skipping auctions for realm %s"%realm)
        session.close()
        return
    
    
    log("  - LastModified: %s"%(time.ctime(lastModified / 1000)))
    db_realm.auction_count = 0
            
    wow_eco_funcs.handle_auc(auctions, db_realm, session, api)   # the big function instead of for key in alliance, horde, neutral  

    db_realm.lastupdate = lastModified / 1000
    session.add(db_realm)
    session.commit()
    session.close()
    log("   - Finished realm %s"%realm.slug)

if __name__ == "__main__":
    try:
        if not os.path.exists("auction_cache"):
            os.mkdir("auction_cache")


        api = battlenet.BattleNetApi(log)

        log("Getting realm list...")
        realms = api.get_realms()
        log("Retrieved %s realms, sending to the realm pool"%len(realms))
        nrealms = 6
        print [realms[i].name for i in range(nrealms)]
        # print len(realms)
        # for i in range(3):
        #     HandleRealm(realms[i])
            
        log("Spinning up thread pools...")
        realm_pool = multiprocessing.pool.ThreadPool(4)
        if "--debug" in sys.argv:
            HandleRealm([x for x in realms if x.slug == "deathwing"][0])
        else:
            realm_pool.map(HandleRealm, realms[:nrealms])
    finally:
        lock.release()