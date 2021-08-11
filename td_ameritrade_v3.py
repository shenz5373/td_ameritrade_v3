from tda_trade_file import read_trade_paras_from_file, append_trade_record, save_trade_paras_to_file, \
    get_account_stock_from_file
from td_ameritrade_api_v3 import place_order, get_access_token, account_available, get_order, cancel_order, \
    refresh_token, get_working_orders, get_queued_orders, trading_hours, get_quotes
import time
from datetime import datetime, timedelta
import pytz
import requests
import sys

UTC = pytz.utc
REFRESH_TIME = 1800
QUOTE_TIME = 30
EXCEPTION_LIMITS = 3
exception_count = 0


def get_optimized_buy_price(tradeParas):
    if tradeParas['OptiState'] == 0 or tradeParas['OptiState'] == 1 or tradeParas['SmallPriceOpti'] <= 0:
        return tradeParas['LastBuyPrice']
    elif 1 < tradeParas['OptiState'] <= tradeParas['SmallPriceOpti'] + 1:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        return tradeParas['LastBuyPrice'] - (tradeParas['OptiState'] - 2) * tradeParas[
            'PriceStep'] + (tradeParas['OptiState'] - 2) * d
    elif -1 >= tradeParas['OptiState'] >= -1 - tradeParas['SmallPriceOpti']:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        return tradeParas['LastBuyPrice'] + tradeParas['ProfitStep'] - (tradeParas['OptiState'] + 1) * tradeParas[
            'PriceStep'] + tradeParas['OptiState'] * d
    else:
        print('优化状态OptiState错误')
        exit()


def get_optimized_sell_price(tradeParas):
    if tradeParas['OptiState'] == 0 or tradeParas['OptiState'] == -1 or tradeParas['SmallPriceOpti'] <= 0:
        return tradeParas['LastBuyPrice'] + tradeParas['ProfitStep'] + tradeParas['PriceStep']
    elif 1 <= tradeParas['OptiState'] <= tradeParas['SmallPriceOpti'] + 1:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        return tradeParas['LastBuyPrice'] - (tradeParas['OptiState'] - 2) * tradeParas[
            'PriceStep'] + tradeParas['OptiState'] * d
    elif -1 > tradeParas['OptiState'] >= -1 - tradeParas['SmallPriceOpti']:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        return tradeParas['LastBuyPrice'] + tradeParas['ProfitStep'] - (tradeParas['OptiState'] + 1) * tradeParas[
            'PriceStep'] + (tradeParas['OptiState'] + 2) * d
    else:
        print('优化状态OptiState错误')
        exit()


def generate_buy_order(account_number, stock_symbol, quantity):
    tradeParas["BuyOrderSendTime"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    save_trade_paras_to_file(stock_symbol, tradeParas)

    if tradeParas["LowestExecPrice"] >= tradeParas['LastBuyPrice']:
        print("exceed lowest price!!!!")
        exit(200)
    # small price Optimize Code begin
    if tradeParas['OptiState'] == 0 or tradeParas['OptiState'] == 1 or tradeParas['SmallPriceOpti'] <= 0:
        optimized_buy_price = tradeParas['LastBuyPrice']
    elif 1 < tradeParas['OptiState'] <= tradeParas['SmallPriceOpti'] + 1:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        optimized_buy_price = tradeParas['LastBuyPrice'] - (tradeParas['OptiState'] - 2) * tradeParas['PriceStep'] + (
                    tradeParas['OptiState'] - 2) * d
    elif -1 >= tradeParas['OptiState'] >= -1 - tradeParas['SmallPriceOpti']:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        optimized_buy_price = tradeParas['LastBuyPrice'] + tradeParas['ProfitStep'] - (tradeParas['OptiState'] + 1) * \
                              tradeParas['PriceStep'] + tradeParas['OptiState'] * d
    else:
        print('优化状态OptiState错误')
        exit()
    # small price Optimize Code end

    if optimized_buy_price > stock_quotes[stock_symbol]['askPrice'] * 1.02:
        d_price = stock_quotes[stock_symbol]['askPrice'] * 1.02
    else:
        d_price = optimized_buy_price
    m_buy_order_id = place_order(
        account_num=account_number,
        access_token=access_token,
        symbol=stock_symbol,
        asset_type="EQUITY",
        instruction="Buy",
        price=d_price,
        quantity=quantity
    )
    return m_buy_order_id


def generate_sell_order(account_number, stock_symbol, quantity):
    tradeParas["SellOrderSendTime"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    save_trade_paras_to_file(stock_symbol, tradeParas)

    if tradeParas["HighestExecPrice"] <= tradeParas['LastBuyPrice'] + tradeParas['ProfitStep'] + tradeParas[
        'PriceStep']:
        print("exceed highest price!!!!")
        exit(200)
    # small price Optimize Code begin
    if tradeParas['OptiState'] == 0 or tradeParas['OptiState'] == -1 or tradeParas['SmallPriceOpti'] <= 0:
        optimized_sell_price = tradeParas['LastBuyPrice'] + tradeParas['ProfitStep'] + tradeParas['PriceStep']
    elif 1 <= tradeParas['OptiState'] <= tradeParas['SmallPriceOpti'] + 1:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        optimized_sell_price = tradeParas['LastBuyPrice'] - (tradeParas['OptiState'] - 2) * tradeParas['PriceStep'] + \
                               tradeParas['OptiState'] * d
    elif -1 > tradeParas['OptiState'] >= -1 - tradeParas['SmallPriceOpti']:
        d = (tradeParas['SmallPriceOpti'] * tradeParas['PriceStep'] + tradeParas['ProfitStep']
             ) / (tradeParas['SmallPriceOpti'] + 1)
        optimized_sell_price = tradeParas['LastBuyPrice'] + tradeParas['ProfitStep'] - (tradeParas['OptiState'] + 1) * \
                               tradeParas['PriceStep'] + (tradeParas['OptiState'] + 2) * d
    else:
        print('优化状态OptiState错误')
        exit()
    # small price Optimize Code end

    if optimized_sell_price < stock_quotes[stock_symbol]['bidPrice'] * 0.98:
        d_price = stock_quotes[stock_symbol]['bidPrice'] * 0.98
    else:
        d_price = optimized_sell_price
    m_sell_order_id = place_order(
        account_num=account_number,
        access_token=access_token,
        symbol=stock_symbol,
        asset_type="EQUITY",
        instruction="Sell",
        price=d_price,
        quantity=quantity
    )
    return m_sell_order_id


stocks = ''

access_token = get_access_token()
last_refresh_time = datetime.now()
last_quotes_time = last_refresh_time

asl = get_account_stock_from_file()
for account in asl:
    account_available(account_num=account['account_number'], access_token=access_token)
    for stock in account['stock_list']:
        tradeParas = read_trade_paras_from_file(stock)
        print("Buy  ", tradeParas['TradeQty'], " ", stock, " @",
              "{:.2f}".format(get_optimized_buy_price(tradeParas=tradeParas)), "  and  Sell ",
              tradeParas['TradeQty'], " ", stock, " @",
              "{:.2f}".format(get_optimized_sell_price(tradeParas=tradeParas)))
        if input('Do you confirm the initial orders?') != 'y':
            exit(1)
        if len(stocks) == 0:
            stocks = stocks + stock
        else:
            stocks = stocks + ',' + stock
print(
    "Program are running, during trading hours(7 am until 8 pm US EASTERN | Monday through Friday) you can monitor the orders on the TD Ameritrade website->Trade->Order Status")

stock_quotes = get_quotes(access_token, stocks)
first_time_enter_trading_hours = True
while True:
    try:
        time.sleep(0.4)
        d_now = datetime.now()
        if (d_now - last_refresh_time).seconds > REFRESH_TIME - 120:
            access_token = refresh_token()
            last_refresh_time = d_now

        if (d_now - last_quotes_time).seconds > QUOTE_TIME:
            stock_quotes = get_quotes(access_token, stocks)
            last_quotes_time = d_now

        if trading_hours():
            # print('trading hours process')
            for account in asl:
                queued_orders = get_queued_orders(account_num=account['account_number'], access_token=access_token)
                for stock in account['stock_list']:
                    tradeParas = read_trade_paras_from_file(stock)

                    if tradeParas["BuyOrderSendTime"] != "0" or tradeParas["SellOrderSendTime"] != "0":
                        if tradeParas["BuyOrderSendTime"] == "0" and tradeParas['BuyOrderId'] != 0:
                            for order in queued_orders:
                                if order['orderId'] == tradeParas['BuyOrderId']:
                                    cancel_order(account_num=account['account_number'], access_token=access_token,
                                                 order_id=tradeParas['BuyOrderId'])
                                    print('tradeParas["SellOrderSendTime"]!="0", Buy order canceled, orderId:',
                                          order['orderId'])
                        if tradeParas["SellOrderSendTime"] == "0" and tradeParas['SellOrderId'] != 0:
                            for order in queued_orders:
                                if order['orderId'] == tradeParas['SellOrderId']:
                                    cancel_order(account_num=account['account_number'], access_token=access_token,
                                                 order_id=tradeParas['SellOrderId'])
                                    print('tradeParas["BuyOrderSendTime"]!="0", Sell order canceled, orderId:',
                                          order['orderId'])
                        for order in queued_orders:
                            entered_time = datetime.strptime(order['enteredTime'], "%Y-%m-%dT%H:%M:%S+%f")
                            if order['orderLegCollection'][0]['instruction'].upper() == "BUY":
                                b_time = datetime.strptime(tradeParas["BuyOrderSendTime"], "%Y-%m-%dT%H:%M:%S")
                                a_time = b_time + timedelta(seconds=3)
                                if order['session'] == 'SEAMLESS' and order['orderType'] == 'LIMIT' and order[
                                    'duration'] == 'DAY' and \
                                        order['orderLegCollection'][0]['instrument'][
                                            'symbol'] == stock and a_time >= entered_time >= b_time:
                                    print("find uncanceled buy order before loop. OrderId=", order['orderId'])
                                    cancel_order(account_num=account['account_number'], access_token=access_token,
                                                 order_id=order['orderId'])
                                    tradeParas["BuyOrderSendTime"] = "0"
                                    save_trade_paras_to_file(stock, tradeParas)
                            elif order['orderLegCollection'][0]['instruction'].upper() == "SELL":
                                b_time = datetime.strptime(tradeParas["SellOrderSendTime"], "%Y-%m-%dT%H:%M:%S")
                                a_time = b_time + timedelta(seconds=3)
                                if order['session'] == 'SEAMLESS' and order['orderType'] == 'LIMIT' and order[
                                    'duration'] == 'DAY' and \
                                        order['orderLegCollection'][0]['instrument'][
                                            'symbol'] == stock and a_time >= entered_time >= b_time:
                                    print("find uncanceled sell order before loop. OrderId=", order['orderId'])
                                    cancel_order(account_num=account['account_number'], access_token=access_token,
                                                 order_id=order['orderId'])
                                    tradeParas["SellOrderSendTime"] = "0"
                                    save_trade_paras_to_file(stock, tradeParas)

                    if tradeParas['BuyOrderId'] == 0 and tradeParas['SellOrderId'] == 0:
                        tradeParas['BuyOrderId'] = generate_buy_order(account_number=account['account_number'],
                                                                      stock_symbol=stock,
                                                                      quantity=tradeParas['TradeQty'])
                        tradeParas['SellOrderId'] = generate_sell_order(account_number=account['account_number'],
                                                                        stock_symbol=stock,
                                                                        quantity=tradeParas['TradeQty'])
                        tradeParas['FilledBuyQty'] = 0
                        tradeParas['FilledSellQty'] = 0
                        tradeParas["SellOrderSendTime"] = "0"
                        tradeParas["BuyOrderSendTime"] = "0"
                        save_trade_paras_to_file(stock, tradeParas)
                    else:
                        buy_order_found = False
                        sell_order_found = False
                        for order in queued_orders:
                            if order['orderId'] == tradeParas['BuyOrderId']:
                                buy_order_found = True
                            elif order['orderId'] == tradeParas['SellOrderId']:
                                sell_order_found = True
                        if not (buy_order_found and sell_order_found):
                            print("deal with orders")
                            buy_order = get_order(account_num=account['account_number'], access_token=access_token,
                                                  order_id=tradeParas['BuyOrderId'])
                            sell_order = get_order(account_num=account['account_number'], access_token=access_token,
                                                   order_id=tradeParas['SellOrderId'])

                            if (int(buy_order['filledQuantity']) == int(buy_order['quantity'])) and (
                                    int(sell_order['filledQuantity']) == int(sell_order['quantity'])):
                                append_trade_record(stock, "Buy " + str(int(buy_order['filledQuantity']))
                                                    + ' ' + stock + " @LmtPrice:" + str(buy_order['price'])
                                                    + '(orderID:' + str(buy_order['orderId']) + ") and Sell "
                                                    + str(int(sell_order['filledQuantity'])) + ' ' + stock
                                                    + " @LmtPrice:" + str(sell_order['price']) + '(orderID:'
                                                    + str(sell_order['orderId']) + ")")
                                tradeParas['BuyOrderId'] = generate_buy_order(account_number=account['account_number'],
                                                                              stock_symbol=stock,
                                                                              quantity=tradeParas['TradeQty'])
                                tradeParas['SellOrderId'] = generate_sell_order(
                                    account_number=account['account_number'],
                                    stock_symbol=stock, quantity=tradeParas['TradeQty'])
                                tradeParas['FilledBuyQty'] = 0
                                tradeParas['FilledSellQty'] = 0
                                tradeParas["SellOrderSendTime"] = "0"
                                tradeParas["BuyOrderSendTime"] = "0"
                                save_trade_paras_to_file(stock, tradeParas)

                            elif (int(buy_order['filledQuantity']) == int(buy_order['quantity'])) and (
                                    int(sell_order['filledQuantity']) + tradeParas['FilledSellQty'] == 0):
                                append_trade_record(stock, "Buy " + str(int(buy_order['filledQuantity']))
                                                    + ' ' + stock + " @LmtPrice:" + str(buy_order['price'])
                                                    + '(orderID:' + str(buy_order['orderId']) + ")")
                                cancel_order(account_num=account['account_number'], access_token=access_token,
                                             order_id=tradeParas['SellOrderId'])
                                tradeParas['LastBuyPrice'] = tradeParas['LastBuyPrice'] - tradeParas['PriceStep']

                                # small price Optimize Code begin
                                if tradeParas['SmallPriceOpti'] > 0:  # 如果等于0表示不需要小差价优化
                                    if tradeParas['OptiState'] == 0:
                                        tradeParas['OptiState'] = 1  # 如果状态0，买入成交，转入状态1---n+1
                                    elif 1 <= tradeParas['OptiState'] <= tradeParas['SmallPriceOpti'] + 1:
                                        # 如果状态1----n+1，当state大于1则减减，当state等于1则状态不变
                                        if tradeParas['OptiState'] > 1:
                                            tradeParas['OptiState'] = tradeParas['OptiState'] - 1
                                    elif -1 >= tradeParas['OptiState'] >= -1 - tradeParas['SmallPriceOpti']:
                                        # 如果状态-1--- -n-1，如果state等于-n-1，切换到买入到底的状态1，否则状态减减
                                        if tradeParas['OptiState'] == -1 - tradeParas['SmallPriceOpti']:
                                            tradeParas['OptiState'] = 1
                                        else:
                                            tradeParas['OptiState'] = tradeParas['OptiState'] - 1
                                # small price Optimize Code end

                                tradeParas['BuyOrderId'] = generate_buy_order(account_number=account['account_number'],
                                                                              stock_symbol=stock,
                                                                              quantity=tradeParas['TradeQty'])
                                tradeParas['SellOrderId'] = generate_sell_order(
                                    account_number=account['account_number'],
                                    stock_symbol=stock, quantity=tradeParas['TradeQty'])
                                tradeParas['FilledBuyQty'] = 0
                                tradeParas['FilledSellQty'] = 0
                                tradeParas["SellOrderSendTime"] = "0"
                                tradeParas["BuyOrderSendTime"] = "0"
                                save_trade_paras_to_file(stock, tradeParas)

                            elif (int(buy_order['filledQuantity']) == int(buy_order['quantity'])) and (
                                    int(sell_order['filledQuantity']) + tradeParas['FilledSellQty'] > 0):
                                append_trade_record(stock, "Buy " + str(int(buy_order['filledQuantity']))
                                                    + ' ' + stock + " @LmtPrice:" + str(buy_order['price'])
                                                    + '(orderID:' + str(buy_order['orderId']) + ") and Sell "
                                                    + str(int(sell_order['filledQuantity'])) + ' ' + stock
                                                    + " @LmtPrice:" + str(sell_order['price']) + '(orderID:'
                                                    + str(sell_order['orderId']) + ")")
                                cancel_order(account_num=account['account_number'], access_token=access_token,
                                             order_id=tradeParas['SellOrderId'])
                                tradeParas['BuyOrderId'] = generate_buy_order(account_number=account['account_number'],
                                                                              stock_symbol=stock,
                                                                              quantity=int(
                                                                                  sell_order['filledQuantity']) +
                                                                                       tradeParas['FilledSellQty'])
                                tradeParas['SellOrderId'] = generate_sell_order(
                                    account_number=account['account_number'],
                                    stock_symbol=stock,
                                    quantity=int(sell_order['quantity']) - int(sell_order['filledQuantity']) - tradeParas[
                                        'FilledSellQty'] + int(buy_order['quantity']))
                                tradeParas['FilledBuyQty'] = 0
                                tradeParas['FilledSellQty'] = 0
                                tradeParas["SellOrderSendTime"] = "0"
                                tradeParas["BuyOrderSendTime"] = "0"
                                save_trade_paras_to_file(stock, tradeParas)

                            elif (int(sell_order['filledQuantity']) == int(sell_order['quantity'])) and (
                                    int(buy_order['filledQuantity']) + tradeParas['FilledBuyQty'] == 0):
                                append_trade_record(stock, "Sell "
                                                    + str(int(sell_order['filledQuantity'])) + ' ' + stock
                                                    + " @LmtPrice:" + str(sell_order['price']) + '(orderID:'
                                                    + str(sell_order['orderId']) + ")")
                                cancel_order(account_num=account['account_number'], access_token=access_token,
                                             order_id=tradeParas['BuyOrderId'])
                                tradeParas['LastBuyPrice'] = tradeParas['LastBuyPrice'] + tradeParas['PriceStep']

                                # small price Optimize Code begin
                                if tradeParas['SmallPriceOpti'] > 0:  # 如果等于0表示不需要小差价优化
                                    if tradeParas['OptiState'] == 0:
                                        tradeParas['OptiState'] = -1  # 如果状态0，卖出成交，转入状态-1-- -n-1
                                    elif 1 <= tradeParas['OptiState'] <= tradeParas['SmallPriceOpti'] + 1:
                                        # 如果状态1----n+1，当state等于n+1，切换到卖出到底状态-1，否则状态加加
                                        if tradeParas['OptiState'] == tradeParas['SmallPriceOpti'] + 1:
                                            tradeParas['OptiState'] = -1
                                        else:
                                            tradeParas['OptiState'] = tradeParas['OptiState'] + 1
                                    elif -1 >= tradeParas['OptiState'] >= -1 - tradeParas['SmallPriceOpti']:
                                        # 如果状态-1--- -n-1，如果state小于-1，则state++
                                        if tradeParas['OptiState'] < -1:
                                            tradeParas['OptiState'] = tradeParas['OptiState'] + 1
                                # small price Optimize Code end

                                tradeParas['BuyOrderId'] = generate_buy_order(account_number=account['account_number'],
                                                                              stock_symbol=stock,
                                                                              quantity=tradeParas['TradeQty'])
                                tradeParas['SellOrderId'] = generate_sell_order(
                                    account_number=account['account_number'],
                                    stock_symbol=stock, quantity=tradeParas['TradeQty'])
                                tradeParas['FilledBuyQty'] = 0
                                tradeParas['FilledSellQty'] = 0
                                tradeParas["SellOrderSendTime"] = "0"
                                tradeParas["BuyOrderSendTime"] = "0"
                                save_trade_paras_to_file(stock, tradeParas)

                            elif (int(sell_order['filledQuantity']) == int(sell_order['quantity'])) and (
                                    int(buy_order['filledQuantity']) + tradeParas['FilledBuyQty'] > 0):
                                append_trade_record(stock, "Buy " + str(int(buy_order['filledQuantity']))
                                                    + ' ' + stock + " @LmtPrice:" + str(buy_order['price'])
                                                    + '(orderID:' + str(buy_order['orderId']) + ") and Sell "
                                                    + str(int(sell_order['filledQuantity'])) + ' ' + stock
                                                    + " @LmtPrice:" + str(sell_order['price']) + '(orderID:'
                                                    + str(sell_order['orderId']) + ")")
                                cancel_order(account_num=account['account_number'], access_token=access_token,
                                             order_id=tradeParas['BuyOrderId'])
                                tradeParas['BuyOrderId'] = generate_buy_order(account_number=account['account_number'],
                                                                              stock_symbol=stock,
                                                                              quantity=int(buy_order['quantity']) - int(
                                                                                  buy_order['filledQuantity']) -
                                                                                       tradeParas['FilledBuyQty'] +
                                                                              int(sell_order['quantity']))
                                tradeParas['SellOrderId'] = generate_sell_order(
                                    account_number=account['account_number'],
                                    stock_symbol=stock,
                                    quantity=int(buy_order['filledQuantity']) + tradeParas['FilledBuyQty'])
                                tradeParas['FilledBuyQty'] = 0
                                tradeParas['FilledSellQty'] = 0
                                tradeParas["SellOrderSendTime"] = "0"
                                tradeParas["BuyOrderSendTime"] = "0"
                                save_trade_paras_to_file(stock, tradeParas)

                            elif first_time_enter_trading_hours and (
                                    buy_order['status'] == 'CANCELED' or buy_order['status'] == 'EXPIRED') and (
                                    sell_order['status'] == 'CANCELED' or sell_order['status'] == 'EXPIRED'):
                                tradeParas['BuyOrderId'] = generate_buy_order(
                                    account_number=account['account_number'],
                                    stock_symbol=stock,
                                    quantity=int(buy_order['quantity']) - int(buy_order['filledQuantity']))
                                tradeParas['SellOrderId'] = generate_sell_order(
                                    account_number=account['account_number'],
                                    stock_symbol=stock,
                                    quantity=int(sell_order['quantity']) - int(sell_order['filledQuantity']))
                                append_trade_record(stock, "Last day, the last order: Buy "
                                                    + str(int(buy_order['filledQuantity']))
                                                    + ' ' + stock + " @LmtPrice:" + str(buy_order['price'])
                                                    + '(orderID:' + str(buy_order['orderId']) + ") and Sell "
                                                    + str(int(sell_order['filledQuantity'])) + ' ' + stock
                                                    + " @LmtPrice:" + str(sell_order['price']) + '(orderID:'
                                                    + str(sell_order['orderId']) + ")")
                                tradeParas['FilledBuyQty'] = int(buy_order['filledQuantity'])
                                tradeParas['FilledSellQty'] = int(sell_order['filledQuantity'])
                                tradeParas["SellOrderSendTime"] = "0"
                                tradeParas["BuyOrderSendTime"] = "0"
                                save_trade_paras_to_file(stock, tradeParas)
                                print("Enter trading hours.", stock, " old orders are canceled, new orders placed")
                            else:
                                print(stock, " buy sell orders can not be found in Queued orders and be processed")
                        else:
                            if first_time_enter_trading_hours:
                                print(stock, " buy sell order found in Queued orders!")
            first_time_enter_trading_hours = False
        else:
            first_time_enter_trading_hours = True

    except requests.RequestException as e:
        print("requests exception:", e)
        time.sleep(10)
        pass
    except:
        exception_count = exception_count + 1
        if exception_count > EXCEPTION_LIMITS:
            print(datetime.now(), "Too many unknown exceptions exceed the EXCEPTION_LIMIT:", EXCEPTION_LIMITS)
            print("Unexpected error:", sys.exc_info()[0])
            exit(100)
        else:
            print(datetime.now(), "Exception happened ", exception_count, " times")
            print("Unexpected error:", sys.exc_info()[0])
            time.sleep(10)
            pass
