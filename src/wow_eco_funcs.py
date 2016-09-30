
import lockfile
import sys
import models
import battlenet
import time
import os
import multiprocessing.pool
import json
import datetime
from numpy import array as nparray
from sqlalchemy import exc



def log(message):
    # Quick and dirty.
    #sys.stdout.write("%s: %s\n"%(time.asctime(), message))
    print (u"%s: %s"%(time.asctime(), message)).encode("utf-8")

def handle_auc(auctions, db_realm, session, api):
    db_realm.action_count = 0                                   # Int - realm specific counter that increments as auctions appear
    auc = auctions["auctions"]                                  # List of jsons, each json is an auction listing(auc, item, owner, bit, bouyout etc.)
    db_realm.auction_count+=len(auc)
    _json_path = "auction_cache/%s.json"%(db_realm.slug)        # string refering to the json that contains the auctions ids(auc["auc"])

    log("   - Found %s auctions"%len(auc))
    auc_ids = nparray([adata['auc'] for adata in auc])          # <type 'numpy.ndarray'>

    if os.path.exists(_json_path):
        with open(_json_path, "r") as pd:                       # json object containing auction ids from the previous snapshot
            try:
                previous_ids = nparray(json.load(pd))           # turning json into nparray
            except ValueError:
                log("   - Error decoding JSON document %s! Removing"%_json_path)
                os.remove(_json_path)
            else:
                temp_ids = list(set(auc_ids) - set(previous_ids))       # list of auctions ids from this snapshot that are not in the previous
                if len(temp_ids):
                    new_ids = nparray(temp_ids)                         # turning the list into nparray
                else:
                    new_ids = []                                        # otherwise an empty list
                del previous_ids, temp_ids
                log("   - Found %s new auctionsl"%len(new_ids))
                new_item_ids = nparray([t["item"] for t in auc if t["auc"] in new_ids])         # a list of the item ids that are auctioned in the new auctions
                log("    - Created item array")
                if not len(new_item_ids):
                    log("     - Passing...")
                    return      # changed from continue

                query = session.query(models.Price).filter(models.Price.day==datetime.datetime.now().date()) \
                                                               .filter(models.Price.realm==db_realm) \
                                                               .filter(models.Price.item_id.in_(new_item_ids))      # query object with all models.Price instances with new item ids
                                                               
                price_objects = {p.item_id:p for p in query.all()}  # dictionary of item_id:Price instabce from the last query
                to_add = []                                         # prepare a list for the future session.add_all()
                
                del new_item_ids

                uauction = {}                                       # a dictionary where keys are owners
                uauction_objects = []                               # a list 

                for auction in auc:                                 # another go through the whole auction list of jsons
                        if auction["auc"] in new_ids:
                            # We got a new item yo
                            if not auction["owner"] == "???":
                                if auction["owner"] not in uauction:
                                    uauction[auction["owner"]] = set()      # initializing a key entry in the dictionary of owners

                                uauction[auction["owner"]].add(auction["item"])     # add an item id the owner
                            
                            # Lets see if we have a Price already
                            if auction["item"] in price_objects:
                                price_db = price_objects[auction["item"]]           # a Price instance taken from the query from before
                            else:
                                #price = models.Price()
                                price_db = models.Price(datetime.datetime.now().date(), db_realm, auction["item"],
                                                        0, 0, 0)    # instantiation of Price in case the was not in the querry. bid, buyout and quantity set to 0
                                price_objects[auction["item"]] = price_db       # reverse of the main if statement
                                
                            price_db.quantity+=auction["quantity"]              # price_db.quantity is incremented whether it was in query or was freshly instantiated
                            if price_db.average_counter > 0:                    # when Price is instantiated self.average_counter = 0
                                price_db.bid = ((price_db.bid * price_db.average_counter) + auction["bid"]) / price_db.average_counter + 1
                                price_db.buyout = ((price_db.buyout * price_db.average_counter) + auction["buyout"]) / price_db.average_counter + 1
                                price_db.average_counter+=1                     # rolling of the average, combining the values of previous snapshots with this one
                            else:
                                price_db.bid = auction["bid"]
                                price_db.buyout = auction["buyout"]
                                price_db.average_counter = 1                    # when no previous snapshots present, initialize rolling averages
                            to_add.append(price_db)

                log("    - Found %s owners, searching"%len(uauction.keys()))
                user_auctions_that_exist = session.query(models.UserAuction).filter(models.UserAuction.owner.in_(uauction.keys())) \
                                                                            .filter(models.UserAuction.realm_id == db_realm.id).all()   # list of UserAuction instances 

                for uauc in user_auctions_that_exist:                           # loop over every UserAuction instance from the query
                    uauc.items = uauc.items + list(uauction[uauc.owner])        # add all the items that belong to the owner of this instance
                    if len(uauc.items) > 30:
                        uauc.items = uauc.items[len(uauc.items)-30:]    # Pop the last auctions off the list
                    uauc.last_updated = datetime.datetime.now()         # add a time stamp
                    to_add.append(uauc)                                 # populating the list that will be commited to database
                    uauction_objects.append(uauc)                       # 

                    del uauction[uauc.owner]

                for name in uauction:                                   # loop over all owners recorded as keys in uauction
                    p = models.UserAuction(name, db_realm, uauction[name])      # instanciate UserAuction
                    to_add.append(p)                                            # prepare to be added to database
                    uauction_objects.append(p)

                session.add_all(to_add)
                session.commit()                                        # the big commit

                log("   - Commited new auctions to the database")
                
                for item in price_objects:                              # loop over the new items from the Price query
                    session.expunge(price_objects[item])                
                for uauction in uauction_objects:           
                    session.expunge(uauction)
                del price_objects
                del to_add
                del uauction_objects
                del uauction                                            # Cleaning the session
                
                item_ids = set([auction_data["item"] for auction_data in auc])      # Another go through the whole list of jsons to gather all item ids
                
                sesquery = session.query(models.Item.id).filter(models.Item.id.in_(item_ids)).all()     # Item ids(Integers) with item ids that are present both in this snapshot and in databse
                items_that_dont_exist = item_ids - set([ o[0] for o in sesquery ])                      # loop over the integers, cannot understand [0]
                
                log("   - Found %s items that dont exist"%len(items_that_dont_exist))
                _o = 0
                _tp = 0
                for item_id in items_that_dont_exist:                   # loop over all new item ids
                    _o+=1
                    _tp+=1
                    _item = api.get_item(item_id)                          # request the new item from blizzard
                    if not _item:
                        log("   - Cant get item id %s"%item_id)
                    else:
                        #log("   - Fetched item %s [%s/%s]"%(item_id, _o, _c))
                        item_db = models.Item(item_id, _item.name, _item.icon, _item.description,
                                              _item.buyPrice, _item.sellPrice, _item.quality, _item.itemLevel)  # instantiate Item using the information from the item json 
                        #to_add.append(item_db)
                        try:
                            session.add(item_db)
                            session.flush()
                            if _tp == 30:
                                session.commit()       # building list of items and commiting after every 30 items
                                _tp = 0
                            session.expunge(item_db)
                        except Exception:
                            log("   - Error adding id %s"%item_id)
                            session.rollback()
                try:
                    session.commit()                    # some commit, don't know why
                except Exception:
                    session.rollback()                             

    else:
        log("    - No previous dump found, dumping current record.")
    
    with open(_json_path, "w") as fd:
        json.dump(list(auc_ids), fd)
