
import battlenet
import auction_cron


api = battlenet.BattleNetApi(auction_cron.log)

print type(api)

bb = api.get_auction('outland', 0)

print type(bb)