1: account_stock_list.txt
[{"account_number":"012345678","stock_list":["METX","OGN"]},{"account_number":"012345678","stock_list":[]}]

2:lastMETXrec.txt
{'Version': '2.00', 'BuyOrderId': 3680271668, 'BuyOrderSendTime': 0, 'FilledBuyQty': 0, 'SellOrderId': 3680271669, 'SellOrderSendTime': 0, 'FilledSellQty': 0, 'TradeQty': 1, 'HighestExecPrice': 3.0, 'LowestExecPrice': 0.5, 'PriceStep': 0.01, 'ProfitStep': 0.05, 'SmallPriceOpti': 0, 'OptiState': -1, 'MainContract': 'STOCK', 'LastBuyPrice': 0.96, 'AlarmHighPrice': 2.5, 'AlarmLowPrice': 1.1}

3:lastOGNrec.txt
{'Version': '2.00', 'BuyOrderId': 3687982042, 'BuyOrderSendTime': 0, 'FilledBuyQty': 0, 'SellOrderId': 3687982043, 'SellOrderSendTime': 0, 'FilledSellQty': 21, 'TradeQty': 40, 'HighestExecPrice': 32.6, 'LowestExecPrice': 25.0, 'PriceStep': 0.01, 'ProfitStep': 0.3, 'SmallPriceOpti': 2, 'OptiState': -1, 'MainContract': 'STOCK', 'LastBuyPrice': 29.580000000000002, 'AlarmHighPrice': 32.0, 'AlarmLowPrice': 28.0}


install step:
1 based on "Ubuntu 20.04.2 LTS"
2 install google chrome
3 install Chrome WebDriver        https://splinter.readthedocs.io/en/latest/drivers/chrome.html
4 edit "chromedriver_path" in config.py      chromedriver_path = r"/home/shenz1973/bin/chromedriver"

06/13/2021
增加余股处理：
当买入卖出定单同时全部成交，LastBuyPrice不变，价格不变，(买入订单的数量+FilledBuyQty)和(卖出订单+FilledSellQty)的数量对调
当买入订单全部成交，卖出订单没有零股成交，变更LastBuyPrice，新订单数量均为配置文件中的买卖数量
当卖出订单全部成交，买入订单没有零股成交，变更LastBuyPrice，新订单数量均为配置文件中的买卖数量
当买入订单全部成交，卖出订单有零股成交，不变更LastBuyPrice，新买入订单数量为前次卖出订单的成交量+FilledSellQty，新卖出订单数量是配置文件买卖数量减去当前买入订单数量
当卖出订单全部成交，买入订单有零股成交，不变更LastBuyPrice，新卖出订单数量为前次买入订单的成交量+FilledBuyQty，新买入订单数量是配置文件买卖数量减去当前卖出订单数量
第一次启动，买入订单的数量=原买入订单数量-原买入订单成交量，卖出订单数量=原卖出订单数量-原卖出订单成交量,将买入和卖出订单成交数量保存到FilledBuyQty和FilledSellQty

06/13/2021
增加小区间优化

07/01
v3 修正了零股成交：
当买入卖出定单同时全部成交，LastBuyPrice不变，价格不变，数量就是配置文件中的数量
当买入订单全部成交，卖出订单没有零股成交，变更LastBuyPrice，新订单数量均为配置文件中的买卖数量
当卖出订单全部成交，买入订单没有零股成交，变更LastBuyPrice，新订单数量均为配置文件中的买卖数量
当买入订单全部成交，卖出订单有零股成交，不变更LastBuyPrice，新买入订单数量为前次卖出订单的成交量+FilledSellQty，新卖出订单数量是前次卖出提交数量减去前次卖出成交数量，再加上前次买入数量
当卖出订单全部成交，买入订单有零股成交，不变更LastBuyPrice，新卖出订单数量为前次买入订单的成交量+FilledBuyQty，新买入订单数量是前次买入提交数量减去前次买入成交数量，再加上前次卖出数量
第一次启动，买入订单的数量=原买入订单数量-原买入订单成交量，卖出订单数量=原卖出订单数量-原卖出订单成交量,将买入和卖出订单成交数量保存到FilledBuyQty和FilledSellQty

增加了30秒一次的股价查询，在生成订单时，已经将和市价相差太远的订单价格修订。在place order中取消了get quote过程，将filled的查询排到第一位，增加成交速度。

将request的异常单独列出

08/08
request加入timeout参数，发生timeout会触发request异常，而不会死等。这是一个重要修复。
