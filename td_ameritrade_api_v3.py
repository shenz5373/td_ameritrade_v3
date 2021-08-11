import time
from datetime import datetime, timedelta
import pytz
import urllib
import requests
from splinter import Browser
from config import client_id, chromedriver_path

refresh_token = ''
COMMUNICATION_RETRY_TIMES = 5
RETRY_SLEEP_SECONDS = 0.5
DEBUG_IN_NO_TRADING_TIME = False

def get_access_token():
    global refresh_token
    exec_path = {'executable_path': chromedriver_path}
    browser = Browser('chrome', **exec_path, headless=False)

    method = 'GET'
    url = 'https://auth.tdameritrade.com/auth?'
    client_code = client_id + '@AMER.OAUTHAP'
    payload = {'response_type': 'code', 'redirect_uri': 'http://localhost/test', 'client_id': client_code}

    built_url = requests.Request(method, url, params=payload).prepare()
    built_url = built_url.url
    browser.visit(built_url)
    bquit = False
    while not bquit:
        time.sleep(1)
        new_url = browser.url
        if new_url.find(r'localhost/test') == -1:
            time.sleep(1)
        else:
            parse_url = urllib.parse.unquote(new_url.split('code=')[1])
            bquit = True
            browser.quit()
    # print(parse_url)

    url = r'https://api.tdameritrade.com/v1/oauth2/token'
    headers = {'Content_Type': "application/x-www-form-urlencoded"}
    payload = {'grant_type': 'authorization_code',
               'access_type': 'offline',
               'code': parse_url,
               'client_id': client_id,
               'redirect_uri': 'http://localhost/test'}
    auth_reply = requests.post(url, headers=headers, data=payload)
    decoded_content = auth_reply.json()
    # print("authorization response:", decoded_content)
    refresh_token = decoded_content['refresh_token']
    return decoded_content['access_token']


def refresh_token():
    global refresh_token
    url = r'https://api.tdameritrade.com/v1/oauth2/token'
    headers = {'Content_Type': "application/x-www-form-urlencoded"}
    payload = {'grant_type': 'refresh_token',
               'refresh_token': refresh_token,
               'client_id': client_id}
    auth_reply = requests.post(url, headers=headers, data=payload, timeout=5)
    decoded_content = auth_reply.json()
    print("refresh token response")   # print("refresh token response", decoded_content)
    return decoded_content['access_token']


def account_available(account_num, access_token):
    headers = {'Authorization': "Bearer {}".format(access_token)}
    endpoint = r"https://api.tdameritrade.com/v1/accounts"

    content = requests.get(url=endpoint, headers=headers)
    data = content.json()
    # print(data)
    account_found = False
    for account in data:
        print(account['securitiesAccount']['accountId'])
        if account['securitiesAccount']['accountId'] == account_num:
            account_found = True
            if not account['securitiesAccount']['isDayTrader']:
                print(
                    "Your account is not a Day Trade Account. Check TD Ameritrade->Client Services->My Profile->General")
                if input('Do you still want to continue?') != 'y':
                    exit(1)
            break
    if not account_found:
        print("Your account number is wrong!")
        exit(1)

    return True


def place_saved_order(account_num, access_token, symbol, asset_type, instruction, price, quantity):
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/savedorders".format(account_num)
    # https://tda-api.readthedocs.io/en/stable/order-builder.html#:~:text=Premarket%20session%2C%20from%208%3A00am%20to%209%3A30am%20Eastern.&text=After%2Dmarket%20session%2C%20from%204,00pm%20to%208%3A00pm%20Eastern.&text=Orders%20are%20active%20during%20all%20trading%20sessions%20except%20the%20overnight%20session.
    # 5:00-13:00,13:00-17:00, at 13:00 program need to reopen the buy and sell order
    headers = {'Authorization': "Bearer {}".format(access_token)}
    payload = {'orderType': 'LIMIT',
               'session': 'SEAMLESS',
               'duration': 'DAY',
               'price': "{:.2f}".format(price),
               'orderStrategyType': 'SINGLE',
               "orderLegCollection": [
                   {"instruction": instruction,
                    "quantity": quantity,
                    "instrument": {"symbol": symbol, "assetType": asset_type}
                    }],
               }
    content = requests.post(url=endpoint, json=payload, headers=headers)
    print('place order content.status_code:', content.status_code)

    content = requests.get(url=endpoint, headers=headers)
    print(content.status_code)
    print("get saved orders status:", content.status_code)

    data = content.json()
    data.reverse()
    for order in data:
        if order['session'] == 'SEAMLESS' and order['orderType'] == 'LIMIT' and order['duration'] == 'DAY' and \
                order['orderLegCollection'][0]['instrument']['assetType'] == asset_type and \
                order['orderLegCollection'][0]['instrument']['symbol'] == symbol and "{:.2f}".format(
            float(order['price'])) == "{:.2f}".format(price) and order['orderLegCollection'][0][
            'instruction'].upper() == instruction.upper() and \
                int(order['orderLegCollection'][0]['quantity']) == int(quantity):
            print(order['savedOrderId'])
            return order['savedOrderId']

    return -1


def cancel_saved_order(account_num, access_token, order_id):
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/savedorders/{}".format(account_num, str(order_id))
    headers = {'Authorization': "Bearer {}".format(access_token)}
    content = requests.delete(url=endpoint, headers=headers)
    print("cancel order status:", content.status_code)

    return content.status_code


def get_saved_orders(account_num, access_token):
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/savedorders".format(account_num)
    headers = {'Authorization': "Bearer {}".format(access_token)}
    content = requests.get(url=endpoint, headers=headers)
    print("get saved orders status:", content.status_code)

    data = content.json()
    data.reverse()
    print(data)
    return data


def place_order(account_num, access_token, symbol, asset_type, instruction, price, quantity):
    UTC = pytz.utc        #timezone('US/Eastern')
    before_time = datetime.now(UTC)
    btstr = before_time.strftime("%Y-%m-%dT%H:%M:%S")
    b_time = datetime.strptime(btstr, "%Y-%m-%dT%H:%M:%S")
    print('before time:', b_time, 'order detail,', instruction, " ", symbol, '@price:', "{:.2f}".format(price))
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/orders".format(account_num)
    # https://tda-api.readthedocs.io/en/stable/order-builder.html#:~:text=Premarket%20session%2C%20from%208%3A00am%20to%209%3A30am%20Eastern.&text=After%2Dmarket%20session%2C%20from%204,00pm%20to%208%3A00pm%20Eastern.&text=Orders%20are%20active%20during%20all%20trading%20sessions%20except%20the%20overnight%20session.
    # 5:00-13:00,13:00-17:00, at 13:00 program need to reopen the buy and sell order
    headers = {'Authorization': "Bearer {}".format(access_token)}
    payload = {'orderType': 'LIMIT',
               'session': 'SEAMLESS',
               'duration': 'DAY',
               'price': "{:.2f}".format(price),
               'orderStrategyType': 'SINGLE',
               'taxLotMethod': 'SPECIFIC_LOT',
               "orderLegCollection": [
                   {"instruction": instruction,
                    "quantity": quantity,
                    "instrument": {"symbol": symbol, "assetType": asset_type}
                    }],
               }
    content = requests.post(url=endpoint, json=payload, headers=headers, timeout=5)
    if int(content.status_code) == 201:
        for a in range(0, COMMUNICATION_RETRY_TIMES + 1):
            after_time = datetime.now(UTC)
            at_str = after_time.strftime("%Y-%m-%dT%H:%M:%S")
            a_time = datetime.strptime(at_str, "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=3)
            print('after time:', a_time)

            payload = {'status': 'FILLED'}
            content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
            if int(content.status_code) == 200:
                data = content.json()
                for order in data:
                    entered_time = datetime.strptime(order['enteredTime'], "%Y-%m-%dT%H:%M:%S+%f")
                    #print('entered time:', entered_time)
                    if order['session'] == 'SEAMLESS' and order['orderType'] == 'LIMIT' and order['duration'] == 'DAY' and \
                            order['orderLegCollection'][0]['instrument']['assetType'] == asset_type and \
                            order['orderLegCollection'][0]['instrument']['symbol'] == symbol and "{:.2f}".format(
                        float(order['price'])) == "{:.2f}".format(price) and order['orderLegCollection'][0][
                        'instruction'].upper() == instruction.upper() and \
                            int(order['orderLegCollection'][0]['quantity']) == int(
                        quantity) and b_time <= entered_time <= a_time:
                        print("OrderId=", order['orderId'])
                        return order['orderId']
                print('Cannot find in filled orders-----')
            else:
                print("Get Filled orders content.status!=200!!!!!!! status=", content.status_code)

            payload = {'status': 'QUEUED'}
            content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
            if int(content.status_code) == 200:
                data = content.json()
                for order in data:
                    entered_time = datetime.strptime(order['enteredTime'], "%Y-%m-%dT%H:%M:%S+%f")
                    #print('entered time:', entered_time)
                    if order['session'] == 'SEAMLESS' and order['orderType'] == 'LIMIT' and order['duration'] == 'DAY' and \
                            order['orderLegCollection'][0]['instrument']['assetType'] == asset_type and \
                            order['orderLegCollection'][0]['instrument']['symbol'] == symbol and "{:.2f}".format(
                        float(order['price'])) == "{:.2f}".format(price) and order['orderLegCollection'][0][
                        'instruction'].upper() == instruction.upper() and \
                            int(order['orderLegCollection'][0]['quantity']) == int(
                        quantity) and b_time <= entered_time <= a_time:
                        print("OrderId=", order['orderId'])
                        return order['orderId']
                print('Cannot find in queued orders-----')
            else:
                print("Get Queued orders content.status!=200!!!!!!! status=", content.status_code)

            if DEBUG_IN_NO_TRADING_TIME:
                payload = {'status': 'WORKING'}
                content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
                if int(content.status_code) == 200:
                    data = content.json()
                    for order in data:
                        entered_time = datetime.strptime(order['enteredTime'], "%Y-%m-%dT%H:%M:%S+%f")
                        #print('entered time:', entered_time)
                        if order['session'] == 'SEAMLESS' and order['orderType'] == 'LIMIT' and order['duration'] == 'DAY' and \
                                order['orderLegCollection'][0]['instrument']['assetType'] == asset_type and \
                                order['orderLegCollection'][0]['instrument']['symbol'] == symbol and "{:.2f}".format(
                            float(order['price'])) == "{:.2f}".format(price) and order['orderLegCollection'][0][
                            'instruction'].upper() == instruction.upper() and \
                                int(order['orderLegCollection'][0]['quantity']) == int(
                            quantity) and b_time <= entered_time <= a_time:
                            print("OrderId=", order['orderId'])
                            return order['orderId']
                    print('Cannot find in WORKING orders-----')
                else:
                    print("Get WORKING orders content.status!=200!!!!!!! status=", content.status_code)

            print('Can not find placed order id!!!!!!!!!!!!!!!!')
            print('place_order retry', a + 1, 'times')
            sleep_retry_time(a + 1)
        exit(21)
    else:
        print('place order content.status_code!=201!!!!!!!!!!!!!!!!! status code:', content.status_code)
        exit(28)


def cancel_order(account_num, access_token, order_id):
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/orders/{}".format(account_num, str(order_id))
    headers = {'Authorization': "Bearer {}".format(access_token)}
    for a in range(0, COMMUNICATION_RETRY_TIMES+1):
        content = requests.delete(url=endpoint, headers=headers, timeout=5)
        if int(content.status_code) == 200:
            return "CANCELED"
        order = get_order(account_num, access_token, order_id)
        if order['status'] == 'CANCELED':
            print("Order has been cancelled before cancel command")
            return "CANCELED"
        elif order['status'] == 'FILLED':
            print("Order has been filled before cancel command")
            return "FILLED"
        elif order['status'] == 'EXPIRED':
            print("Order has been expired before cancel command")
            return "EXPIRED"

        print('get_order retry', a + 1, 'times')
        print(content)
        sleep_retry_time(a + 1)
    print("cancel order status_code!=200!!!!!!! status_code=", content.status_code)
    exit(22)


def get_working_orders(account_num, access_token):
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/orders".format(account_num)
    headers = {'Authorization': "Bearer {}".format(access_token)}
    payload = {'status': 'WORKING'}
    for a in range(0, COMMUNICATION_RETRY_TIMES+1):
        content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
        if int(content.status_code) == 200:
            data = content.json()
            return data
        print('get_Queued_order retry', a+1, 'times')
        print(content)
        sleep_retry_time(a + 1)
    print("get orders status_code!=200!!!!!!! status_code=", content.status_code)
    exit(23)


def get_queued_orders(account_num, access_token):
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/orders".format(account_num)
    headers = {'Authorization': "Bearer {}".format(access_token)}
    if DEBUG_IN_NO_TRADING_TIME:
        payload = {'status': 'WORKING'}
    else:
        payload = {'status': 'QUEUED'}
    for a in range(0, COMMUNICATION_RETRY_TIMES+1):
        content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
        if int(content.status_code) == 200:
            data = content.json()
            return data
        print('get_Queued_order retry', a+1, 'times')
        print(content)
        sleep_retry_time(a + 1)
    print("get orders status_code!=200!!!!!!! status_code=", content.status_code)
    exit(26)


def get_order(account_num, access_token, order_id):
    endpoint = r"https://api.tdameritrade.com/v1/accounts/{}/orders/{}".format(account_num, order_id)
    headers = {'Authorization': "Bearer {}".format(access_token)}
    for a in range(0, COMMUNICATION_RETRY_TIMES+1):
        content = requests.get(url=endpoint, headers=headers, timeout=5)
        if int(content.status_code) == 200:
            data = content.json()
            return data
        print('get_order retry', a+1, 'times')
        print(content)
        sleep_retry_time(a + 1)
        print("get an order status_code!=200!!!!!!! status_code=", content.status_code)
    exit(24)


def get_quote(access_token, symbol):
    endpoint = r"https://api.tdameritrade.com/v1/marketdata/{}/quotes".format(symbol)
    headers = {'Authorization': "Bearer {}".format(access_token)}
    payload = {'apikey': client_id}
    for a in range(0, COMMUNICATION_RETRY_TIMES+1):
        content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
        if int(content.status_code) == 200:
            data = content.json()
            #print(data["{}".format(symbol)]["bidPrice"])
            return data
        print('get_quote retry', a+1, 'times')
        print(content)
        sleep_retry_time(a+1)
    print("get a quote status_code!=200!!!!!!! status_code=", content.status_code)
    exit(25)


def get_quotes(access_token, symbols):
    endpoint = r"https://api.tdameritrade.com/v1/marketdata/quotes"
    headers = {'Authorization': "Bearer {}".format(access_token)}
    payload = {'apikey': client_id,
               'symbol': symbols}
    for a in range(0, COMMUNICATION_RETRY_TIMES+1):
        content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
        if int(content.status_code) == 200:
            data = content.json()
            print("api",data)
            return data
        print('get_quotes retry', a+1, 'times')
        print(content)
        sleep_retry_time(a+1)
    print("get quotes status_code!=200!!!!!!! status_code=", content.status_code)
    exit(29)


def get_option_chain(access_token, symbol, from_date, to_date):
    endpoint = r"https://api.tdameritrade.com/v1/marketdata/chains"
    headers = {'Authorization': "Bearer {}".format(access_token)}
    payload = {'apikey': client_id,
               'symbol': symbol,
               'strikeCount': 6,
               'includeQuotes': 'TRUE',
               'strategy': 'SINGLE',
               'range': 'NTM',
               'fromDate': from_date,
               'toDate': to_date,
               'optionType': 'S'}
    content = requests.get(url=endpoint, params=payload, headers=headers, timeout=5)
    return content.json()


def sleep_retry_time(retry_times):
    sleep_time = RETRY_SLEEP_SECONDS * retry_times
    if sleep_time > 3:
        sleep_time = 3
    time.sleep(sleep_time)


def trading_hours():
    if DEBUG_IN_NO_TRADING_TIME:
        return True
    US_EASTERN = pytz.timezone('US/Eastern')
    now = datetime.now(US_EASTERN)
    if now.weekday() > 4:  # https://pythontic.com/datetime/date/weekday
        return False
    hour = now.hour
    if hour > 19 or hour < 7:  # 7 am until 8 pm Monday through Friday
        return False
    else:
        return True
