import websocket
import json
from collections import deque
from datetime import datetime, timedelta

from req import Reqs
from env import BASE_URL


# instantiate the HTTP requests
req = Reqs()

# shared between SellMonitor and OrderChecker
elligibleOrders = deque()

# current orders that need to be sold, shared SellMonitor and OrderChecker
unreversedOrders = []


class PriceSocket:
    # responsible from receiving incoming price data and checking if buy or sell orders can be placed
    def __init__(self) -> None:
        self.last_buy_time = datetime.now() - timedelta(minutes=1) # set initial time to ensure a buy can happen immediately
        self.subscribeMessage = json.dumps({
            "type": "subscribe",
            # "topic": f"/market/ticker:{self.instrument}",
            "topic": f"/market/ticker:BTC-USDT",
            "privateChannel": False,
            "response": True
        })

        self.wsapp = websocket.WebSocketApp(
            f"wss://ws-api-spot.kucoin.com/?token={req.requestTokenPublic()}", on_message=self.onMessage)

    def onMessage(self, wsapp, msg):
        msg = json.loads(msg)

        if datetime.now() > self.last_buy_time + timedelta(seconds=60):
            self.buyMonitor(msg)
            self.last_buy_time = datetime.now()

        self.sellMonitor(msg)

    def buyMonitor(self, msg):
        if msg:
            print('Buy Order Reached')

    def sellMonitor(self, msg):
        if msg:
            price = msg['data']['bestAsk']  
            if len(self.dq) == 2:
                currentPrice = float(self.dq[-1])
                previousPrice = float(self.dq[0])
                # placeholder condition
                if (previousPrice - currentPrice) > 10000:
                    try:
                        print('TEST -- Buy Order Reached')
                    except:
                        print('Attempted buy but failed')

                    self.dq.pop()
            else:
                self.dq.appendleft(price)
            pass

    def startSocket(self):
        self.wsapp.run_forever()


class OrdersSocket:
    # responsible for confirming orders that are placed by the buy and sell checkers
    def __init__(self) -> None:
        self.elligibleOrderIndexesTemp = []
        self.subscribeMessage = json.dumps({
            "type": "subscribe",
            "topic": "/spotMarket/tradeOrders",
            "privateChannel": True,
            "response": True
        })

        self.wsapp = websocket.WebSocketApp(
            f"wss://ws-api-spot.kucoin.com/?token={req.requestTokenPrivate()}", on_message=self.onMessage)

    def onMessage(self, wsapp, msg):
        newOrderQty = 0.0
        orderPrices = []       
        for i, order in enumerate(unreversedOrders):
            if float(price) > float(order['filledPrice']):
                orderPrices.append(float(order['filledPrice']))
                newOrderQty += float(order['filledSize'])
                self.elligibleOrderIndexesTemp.append(i)
        # must      meet minimum required order qty
        if newOrderQty >= 0.1:
            maxPrice = max(orderPrices)
            # ensure the specified price is a multiple of priceIncrement
            r = maxPrice % 0.00001000
            if r != 0:
                print('The price is not a multiple of the min price')
                if r < 0.00001000:
                    dif = 0.00001000 - r
                    finalPrice = maxPrice + dif
                else:
                    finalPrice = maxPrice + r
            else:
                finalPrice = maxPrice + 0.00001000

            # place an order
            try:
                print('TEST -- Sell Order Reached')
                # req.createSellOrderLimit(
                #     price=finalPrice, qty=newOrderQty, instrument='BTC-USDT')
            except:
                print('Attempted sell order but failed')
            else:
                # export the indexes that need to be removed from unreversedOrders, so they order checker can remove them
                elligibleOrders.appendleft(self.elligibleOrderIndexesTemp)

                # reset temp stores
                newOrderQty = 0.0
                self.elligibleOrderIndexesTemp = []
                orderPrices = []

    def startSocket(self):
        self.wsapp.run_forever()


if __name__ == '__main__':
    price_socket = PriceSocket()
    order_socket = OrdersSocket()

    t1 = threading.Thread(target=price_socket.startSocket)
    t2 = threading.Thread(target=order_socket.startSocket)

    t1.start()
    t2.start()