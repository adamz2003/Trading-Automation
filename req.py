import base64
import hashlib
import hmac
import json
import time
import uuid
import requests
from env import API_KEY, API_PASS, API_SECRET


class Reqs:
    def __init__(self) -> None:
        pass

    def requestTokenPublic(self):
        response = requests.post('https://api.kucoin.com/api/v1/bullet-public')
        response = response.json()
        token = response['data']['token']
        return token

    def requestTokenPrivate(self):
        api_key = API_KEY
        api_secret = API_SECRET
        api_passphrase = API_PASS
        now = int(time.time() * 1000)
        str_to_sign = str(now) + 'POST' + '/api/v1/bullet-private'
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        passphrase = base64.b64encode(hmac.new(api_secret.encode(
            'utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2"
        }
        response = requests.post(
            'https://api.kucoin.com/api/v1/bullet-private', headers=headers)
        response = response.json()
        token = response['data']['token']
        return token

    def createBuyOrderMarket(self, funds, instrument):

        api_key = API_KEY
        api_secret = API_SECRET
        api_passphrase = API_PASS
        now = int(time.time() * 1000)
        clientGeneratedId = uuid.uuid1()
        data = {
            "clientOid": str(clientGeneratedId),
            "side": "buy",
            "symbol": instrument,
            "type": "market",
            "funds": str(funds)
        }
        dataJson = json.dumps(data)
        str_to_sign = str(now) + 'POST' + '/api/v1/orders' + dataJson
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        passphrase = base64.b64encode(hmac.new(api_secret.encode(
            'utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.post(
            'https://api.kucoin.com/api/v1/orders', data=dataJson, headers=headers)
        print(response.status_code)
        print(response.json())
        return response.json()

    def createSellOrderMarket(self, funds, instrument):

        api_key = API_KEY
        api_secret = API_SECRET
        api_passphrase = API_PASS
        now = int(time.time() * 1000)
        clientGeneratedId = uuid.uuid1()
        data = {
            "clientOid": str(clientGeneratedId),
            "side": "sell",
            "symbol": instrument,
            "type": "market",
            "funds": str(funds)
        }
        dataJson = json.dumps(data)
        str_to_sign = str(now) + 'POST' + '/api/v1/orders' + dataJson
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        passphrase = base64.b64encode(hmac.new(api_secret.encode(
            'utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.post(
            'https://api.kucoin.com/api/v1/orders', data=dataJson, headers=headers)
        print(response.status_code)
        print(response.json())
        return response.json()

    def createSellOrderLimit(self, price, qty, instrument):

        api_key = API_KEY
        api_secret = API_SECRET
        api_passphrase = API_PASS
        now = int(time.time() * 1000)
        clientGeneratedId = uuid.uuid1()
        # NOTE Price must be in base currency for limit orders
        # NOTE Price must be a multiple of priceIncrement for limit orders
        data = {
            "clientOid": str(clientGeneratedId),
            "side": "sell",
            "symbol": instrument,
            "type": "limit",
            "price": str(price),
            "size": qty,
            "timeInForce": "FOK"
        }
        dataJson = json.dumps(data)
        str_to_sign = str(now) + 'POST' + '/api/v1/orders' + dataJson
        signature = base64.b64encode(
            hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
        passphrase = base64.b64encode(hmac.new(api_secret.encode(
            'utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.post(
            'https://api.kucoin.com/api/v1/orders', data=dataJson, headers=headers)
        print(response.status_code)
        print(response.json())
        return response.json()
