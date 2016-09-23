

def handle_auc(auctions, db_realm, session):
    db_realm.action_count = 0
    auc = auctions["auctions"]      # key removed
    db_realm.auction_count+=len(auc)
    _json_path = "auction_cache/%s.json"%(db_realm.slug)        # key removed

    log("   - Found %s auctions"%len(auc))
    auc_ids = nparray([adata['auc'] for adata in auc])

    if os.path.exists(_json_path):
        with open(_json_path, "r") as pd:
            try:
                previous_ids = nparray(json.load(pd))
            except ValueError:
                log("   - Error decoding JSON document %s! Removing"%_json_path)
                os.remove(_json_path)
            else:
                tempids = list(set(auc_ids) - set(previous_ids))
                if len(temp_ids):
                    new_ids = nparray(temp_ids)
                else:
                    new_ids = []
                del previous_ids, temp_ids
                log("   - Found %s new auctionsl"%len(new_ids))
                new_item_ids = nparray([t["item"] for t in auc if t["auc"] in new_ids])
                log("    - Created item array")
                if not len(new_item_ids):
                    log("     - Passing...")
                    return      # changed from continue

                query = session.query(models.Price).filter(models.Price.day==datetime.datetime.now().date()) \
                                                               .filter(models.Price.realm==db_realm) \
                                                               .filter(models.Price.item_id.in_(new_item_ids))
                                                               # .filter(models.Price.faction==key)
                                                               
                price_objects = {p.item_id:p for p in query.all()}  # dict comprehension
                to_add = []
                
                del new_item_ids

                uauction = {}
                uauction_objects = []

                for auction in auc:
                        if auction["auc"] in new_ids:
                            # We got a new item yo
                            if not auction["owner"] == "???":
                                if auction["owner"] not in uauction:
                                    uauction[auction["owner"]] = set()

                                uauction[auction["owner"]].add(auction["item"])
                            
                            # Lets see if we have a Price already
                            if auction["item"] in price_objects:
                                price_db = price_objects[auction["item"]]
                            else:
                                #price = models.Price()
                                price_db = models.Price(datetime.datetime.now().date(), db_realm, auction["item"],
                                                        0, 0, 0)    # key component removed from instantiation
                                price_objects[auction["item"]] = price_db
                                
                            price_db.quantity+=auction["quantity"]
                            if price_db.average_counter > 0:
                                price_db.bid = ((price_db.bid * price_db.average_counter) + auction["bid"]) / price_db.average_counter + 1
                                price_db.buyout = ((price_db.buyout * price_db.average_counter) + auction["buyout"]) / price_db.average_counter + 1
                                price_db.average_counter+=1
                            else:
                                price_db.bid = auction["bid"]
                                price_db.buyout = auction["buyout"]
                                price_db.average_counter = 1
                            to_add.append(price_db)

                log("    - Found %s owners, searching"%len(uauction.keys()))
                user_auctions_that_exist = session.query(models.UserAuction).filter(models.UserAuction.owner.in_(uauction.keys())) \
                                                                            .filter(models.UserAuction.realm_id == db_realm.id).all()

                for uauc in user_auctions_that_exist:
                    uauc.items = uauc.items + list(uauction[uauc.owner])
                    if len(uauc.items) > 30:
                        uauc.items = uauc.items[len(uauc.items)-30:] # Pop the last auctions off the list
                    uauc.last_updated = datetime.datetime.now()
                    to_add.append(uauc)
                    uauction_objects.append(uauc)

                    del uauction[uauc.owner]

                for name in uauction:
                    p = models.UserAuction(name, db_realm, uauction[name])
                    to_add.append(p)
                    uauction_objects.append(p)

                session.add_all(to_add)
                session.commit()

                log("   - Commited new auctions to the database")
                
                for item in price_objects:
                    session.expunge(price_objects[item])
                for uauction in uauction_objects:
                    session.expunge(uauction)
                del price_objects
                del to_add
                del uauction_objects
                del uauction
                
                item_ids = set([auction_data["item"] for auction_data in auc])
                
                items_that_dont_exist = item_ids - set([ o[0] for o in session.query(models.Item.id).filter(models.Item.id.in_(item_ids)).all() ])
                
                log("   - Found %s items that dont exist"%len(items_that_dont_exist))
                _o = 0
                _tp = 0
                for item_id in items_that_dont_exist:
                    _o+=1
                    _tp+=1
                    _item = api.get_item(item_id)
                    if not _item:
                        log("   - Cant get item id %s"%item_id)
                    else:
                        #log("   - Fetched item %s [%s/%s]"%(item_id, _o, _c))
                        item_db = models.Item(item_id, _item.name, _item.icon, _item.description,
                                              _item.buyPrice, _item.sellPrice, _item.quality, _item.itemLevel)
                        #to_add.append(item_db)
                        try:
                            session.add(item_db)
                            session.flush()
                            if _tp == 30:
                                session.commit()
                                _tp = 0
                            session.expunge(item_db)
                        except Exception:
                            log("   - Error adding id %s"%item_id)
                            session.rollback()
                try:
                    session.commit()
                except Exception:
                    session.rollback()                             

    else:
        log("    - No previous dump found, dumping current record.")
    
    with open(_json_path, "w") as fd:
        json.dump(list(auc_ids), fd)
