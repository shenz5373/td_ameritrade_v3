from datetime import datetime
import json
import os

def append_debug_record(str):
    now = datetime.now()
    filename = 'Debug' + now.strftime("%Y") + now.strftime("%m") + now.strftime("%d")
    fhand = open(filename, "a")
    fhand.write(str + " Append@" + now.strftime("%H:%M:%S") + "\n")
    fhand.close()


def append_trade_record(stock_name, trade_str):
    path = stock_name
    if not os.path.exists(path):
        os.makedirs(path)
    now = datetime.now()
    filename = stock_name + now.strftime("%Y") + now.strftime("%m") + now.strftime("%d")
    fhand = open(os.path.join(path, filename), "a")
    fhand.write(trade_str + "   ----Append@" + now.strftime("%H:%M:%S") + "\n")
    fhand.close()


def read_trade_paras_from_file(stock_name):
    file_name = 'last'+stock_name+'rec.txt'
    fr = open(file_name, 'r+')
    trade_paras = eval(fr.read())  # 读取的str转换为字典
    fr.close()
    #print(trade_paras)
    return trade_paras


def save_trade_paras_to_file(stock_name, trade_paras):
    file_name = 'last'+stock_name+'rec.txt'
    fw = open(file_name, 'w+')
    fw.write(str(trade_paras))  # 把字典转化为str
    fw.close()
    print('Save last', stock_name, 'rec.txt successfully!')


def get_account_stock_from_file():
    fr = open('account_stock_list.txt', 'r+')
    account_stock_list = json.loads(fr.readline())
    fr.close()
    print(account_stock_list)
    return account_stock_list


'''
append_trade_record("OGN", "test dir   aaaa!  ")
append_trade_record("METX", "test dir   aaaa!  ")

a= read_trade_paras_from_file('METX')
print(a)

asl = get_account_stock_from_file()
for account in asl:
    print(account['account_number'])
    print('stock list')
    for stock in account['stock_list']:
        print("  ", stock)
'''
