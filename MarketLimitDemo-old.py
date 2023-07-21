import random
import time
import websocket
import json
from env import BASE_URL
import threading
from collections import deque
import pandas as pd
import uuid
import requests
from req import Reqs
import csv
import concurrent.futures
import asyncio
from asyncio import Queue

# instantiate the HTTP requests
req = Reqs()

# using lock for thread safe reading/writing of shared store
lock = threading.Lock()

async def getLockData():
    # acquire the lock
    lock.acquire()
    print(lock)

    # release the lock
    lock.release()

# used to share elligible order info from sell monitor and order checker
elligibleOrders = deque()

# current orders that need to be sold
unreversedOrders = []


class PriceSocket:
    # responsible from receiving incoming price data and checking if buy or sell orders can be placed
    def __init__(self) -> None:

        self.subscribeMessage = json.dumps({
            "type": "subscribe",
            # "topic": f"/market/ticker:{self.instrument}",
            "topic": f"/market/ticker:BTC-USDT",
            "privateChannel": False,
            "response": True
        })

        self.wsapp = websocket.WebSocketApp(
            f"wss://ws-api-spot.kucoin.com/?token={req.requestTokenPublic()}", on_open=self.onOpen, on_message=self.onMessage)

        # instantiate buy and sell monitors
        self.buyMonitor = BuyMonitor()
        self.sellMonitor = SellMonitor()

    async def onMessage(self, wsapp, msg):
        # convert the message to json so it can be manipulated
        msg = json.loads(msg)
        # start the processor methods in separate tasks
        task1 = asyncio.create_task(self.buyMonitor.checkForBuys(msg))
        task2 = asyncio.create_task(self.sellMonitor.monitorUnreversedOrders(msg))

        # wait for task 2 to complete after a delay of 60 seconds
        await asyncio.sleep(60)
        await task2, getLockData()

    def onOpen(self, wsapp):
        sent = wsapp.send(self.subscribeMessage)
        # print(f'Sent: {sent}')
        print('starting PriceSocket')

    def onPing(self, wsapp, message):
        pass

    def onPong(self, wsapp, message):
        pass

    async def startSocket(self):
        async with websockets.connect(f"wss://ws-api-spot.kucoin.com/?token={req.requestTokenPublic()}") as ws:
            self.wsapp = ws
            sent = await self.wsapp.send(self.subscribeMessage)
            print('starting PriceSocket')
            async for msg in self.wsapp:
                await self.onMessage(ws, msg)


class BuyMonitor:
    # responsible for checking incoming ws messages to see if a buy order should be placed
    # the buy monitor needs the last price and the current price
    # the current price is only updated every x seconds

    def __init__(self) -> None:
        self.dq = deque()

    async def checkForBuys(self, msg):
        startTime = time.time()
        currentTime = time.time()
        print(msg)
        while True:
            if currentTime - startTime < 60:
                currentTime = time.time()
            else:
                print('reached 60s')
                currentTime = time.time()
                startTime = time.time()
                price = msg['data']['bestAsk']  
                if len(self.dq) == 2:
                    currentPrice = float(self.dq[-1])
                    previousPrice = float(self.dq[0])
                    # placeholder condition
                    if (previousPrice - currentPrice) > 10000:
                        try:
                            print('TEST -- Buy Order Reached')
                            # req.createBuyOrderMarket('0.1', 'BTC-USDT')
                        except:
                            print('Attempted buy but failed')

                        self.dq.pop()

                else:
                    self.dq.appendleft(price)


class SellMonitor:
    # responsible for continuously iterating over the current orders that need to be sold and checking if any profitable trades can be made
    # a profitable trade is any trade where the difference in price is > 0, or a custom defined profit target
    # sell monitor exports data to the order checker via the global elligibleOrders deque

    def __init__(self) -> None:

        self.elligibleOrderIndexesTemp = []

    async def monitorUnreversedOrders(self, msg):
        price = msg['data']['bestAsk']
        newOrderQty = 0.0
        orderPrices = []
        print(msg)
        while True:
            print(f'-----{price}-----')
            # check the global store that contains all orders that need to be sold to see if any orders can be sold for a profit
            lock.acquire()
            # unreversedOrders is shared between order checker and sell monitor
            for i, order in enumerate(unreversedOrders):
                if float(price) > float(order['filledPrice']):
                    orderPrices.append(float(order['filledPrice']))
                    newOrderQty += float(order['filledSize'])
                    self.elligibleOrderIndexesTemp.append(i)
            lock.release()

            # must meet minimum required order qty
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


class OrdersSocket:
    # responsible for confirming orders that are placed by the buy and sell checkers
    def __init__(self) -> None:

        self.subscribeMessage = json.dumps({
            "type": "subscribe",
            "topic": "/spotMarket/tradeOrders",
            "privateChannel": True,
            "response": True
        })

        self.wsapp = websocket.WebSocketApp(
            f"wss://ws-api-spot.kucoin.com/?token={req.requestTokenPrivate()}", on_open=self.onOpen, on_message=self.onMessage)

    async def onMessage(self, wsapp, msg):
        # convert the message to json so it can be manipulated
        msg = json.loads(msg)
        print(msg)
        # process incoming messages
        if msg['subject'] == 'orderChange':
            if msg['data']['status'] == 'done':
                print(msg['data'])
                data = {
                    'serverId': msg['data']['orderId'],
                    'symbol': msg['data']['symbol'],
                    'orderType': msg['data']['limit'],
                    'side': msg['data']['sell'],
                    'specifiedSize': msg['data']['size'],
                    'filledSize': msg['data']['filledSize'],
                    'filledPrice': msg['data']['price']
                }

                if data['side'] == 'buy':
                    async with lock:
                        unreversedOrders.append(data)
                elif data['side'] == 'sell':
                    await self.handleSellOrder()

                    specifiedSize = float(data['specifiedSize'])
                    filledSize = float(data['filledSize'])
                    if specifiedSize - filledSize != 0:
                        # TODO save the mismatch to be accumulated with other mismatches and sold later
                        print(f'Sell order fill mismatch: {specifiedSize - filledSize}')

    async def handleSellOrder(self):
        indexesToBeRemoved = list(elligibleOrders.pop())
        indexesToBeRemoved.sort(reverse=True)
        async with lock:
            # once a sell order is confirmed, it needs to be removed from elligibleOrders because they have already been sold
            for i in indexesToBeRemoved:
                del elligibleOrders[i]

    def onOpen(self, wsapp):
        sent = wsapp.send(self.subscribeMessage)
        # print(sent)
        print('starting order socket')

    def onPing(self, wsapp, message):
        pass

    def onPong(self, wsapp, message):
        pass

    async def startSocket(self):
        async with websockets.connect(f"wss://ws-api-spot.kucoin.com/?token={req.requestTokenPrivate()}") as ws:
            self.wsapp = ws
            sent = await self.wsapp.send(self.subscribeMessage)
            print('starting order socket')
            async for msg in self.wsapp:
                await self.onMessage(ws, msg)

# async def main():
#     orders_socket = OrdersSocket()
#     price_socket = PriceSocket()
#     tasks = [orders_socket.startSocket(), price_socket.startSocket()]
#     await asyncio.gather(*tasks)

# if __name__ == '__main__':
#     pass
#     asyncio.run(main())

if __name__ == '__main__':
    pass
    priceSocket = PriceSocket()
    orderSocket = OrdersSocket()

    t1 = threading.Thread(target=priceSocket.startSocket)
    t2 = threading.Thread(target=orderSocket.startSocket)

    t1.start()
    t2.start()