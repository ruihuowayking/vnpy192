# encoding: UTF-8
import json
import logging
import sys
import os
import csv
import re
from pathlib import Path
from typing import Callable, Dict
from decimal import Decimal
from math import floor, ceil
from time import time
from datetime import datetime, timedelta
from functools import wraps
import numpy as np
import talib
import io

from vnpy.trader.vtObject import VtBarData as BarData, VtTickData as TickData
from ExchangeValue import Exchange, Interval

log_formatter = logging.Formatter('[%(asctime)s] %(message)s')


def func_time(over_ms = 0):
    """
    简单记录执行时间
    :param :over_ms 超过多少毫秒, 提示信息
    :return:
    """

    def run(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time()
            result = func(*args, **kwargs)
            end = time()
            execute_ms = (int(round(end * 1000))) - (int(round(start * 1000)))
            if execute_ms > over_ms:
                print('{} took {} ms'.format(func.__qualname__, execute_ms))
            return result

        return wrapper

    return run



def get_underlying_symbol(symbol):
    """
    取得合约的短号.  rb2005 => rb
    :param symbol:
    :return: 短号
    """
    # 套利合约
    if symbol.find(' ') != -1:
        # 排除SP SPC SPD
        s = symbol.split(' ')
        if len(s) < 2:
            return symbol
        symbol = s[1]

        # 只提取leg1合约
        if symbol.find('&') != -1:
            s = symbol.split('&')
            if len(s) < 2:
                return symbol
            symbol = s[0]

    p = re.compile(r"([A-Z]+)[0-9]+", re.I)
    underlying_symbol = p.match(symbol)

    if underlying_symbol is None:
        return symbol

    return underlying_symbol.group(1)



def get_stock_exchange(code, vn=True):
    """根据股票代码，获取交易所"""
    # vn：取EXCHANGE_SSE 和 EXCHANGE_SZSE
    code = str(code)
    if len(code) < 6:
        return ''

    market_id = 0  # 缺省深圳
    code = str(code)
    if code[0] in ['5', '6', '9'] or code[:3] in ["009", "126", "110", "201", "202", "203", "204"]:
        market_id = 1  # 上海
    try:
        from vnpy.trader.constant import Exchange
        if vn:
            return Exchange.SSE.value if market_id == 1 else Exchange.SZSE.value
        else:
            return 'XSHG' if market_id == 1 else 'XSHE'
    except Exception as ex:
        print(u'加载数据异常:{}'.format(str(ex)))

    return ''



def get_full_symbol(symbol):
    """
    获取全路径得合约名称, MA005 => MA2005, j2005 => j2005
    """
    if symbol.endswith('SPD'):
        return symbol

    underlying_symbol = get_underlying_symbol(symbol)
    if underlying_symbol == symbol:
        return symbol

    symbol_month = symbol.replace(underlying_symbol, '')
    if len(symbol_month) == 3:
        if symbol_month[0] == '0':
            # 支持2020年合约
            return '{0}2{1}'.format(underlying_symbol, symbol_month)
        else:
            return '{0}1{1}'.format(underlying_symbol, symbol_month)
    else:
        return symbol


def get_real_symbol_by_exchange(full_symbol, vn_exchange):
    """根据交易所，返回真实合约"""
    if vn_exchange == Exchange.CFFEX:
        return full_symbol.upper()

    if vn_exchange in [Exchange.DCE, Exchange.SHFE, Exchange.INE]:
        return full_symbol.lower()

    if vn_exchange == Exchange.CZCE:
        underlying_symbol = get_underlying_symbol(full_symbol).upper()
        yearmonth_len = len(full_symbol) - len(underlying_symbol) - 1
        return underlying_symbol.upper() + full_symbol[-yearmonth_len:]

    return full_symbol


def get_trading_date(dt = None):
    """
    根据输入的时间，返回交易日的日期
    :param dt:
    :return:
    """
    if dt is None:
        dt = datetime.now()

    if dt.isoweekday() in [6, 7]:
        # 星期六,星期天=>星期一
        return (dt + timedelta(days=8 - dt.isoweekday())).strftime('%Y-%m-%d')

    if dt.hour >= 20:
        if dt.isoweekday() == 5:
            # 星期五=》星期一
            return (dt + timedelta(days=3)).strftime('%Y-%m-%d')
        else:
            # 第二天
            return (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        return dt.strftime('%Y-%m-%d')


def extract_vt_symbol(vt_symbol):
    """
    :return: (symbol, exchange)
    """
    symbol, exchange_str = vt_symbol.split(".")
    return symbol, Exchange(exchange_str)

def generate_vt_symbol(symbol, exchange):
    """
    return vt_symbol
    """
    return "{symbol}.{exchange.value}"

def format_number(n):
    """格式化数字到字符串"""
    rn = round(n, 2)  # 保留两位小数
    return format(rn, ',')  # 加上千分符

def _get_trader_dir(temp_name):
    """
    Get path where trader is running in.
    """
    # by incenselee
    # 原方法，当前目录必须自建.vntrader子目录，否则在用户得目录下创建
    # 为兼容多账号管理，取消此方法。
    return Path.cwd(), Path.cwd()

    cwd = Path.cwd()
    temp_path = cwd.joinpath(temp_name)

    # If .vntrader folder exists in current working directory,
    # then use it as trader running path.
    if temp_path.exists():
        return cwd, temp_path

    # Otherwise use home path of system.
    home_path = Path.home()
    temp_path = home_path.joinpath(temp_name)

    # Create .vntrader folder under home path if not exist.
    if not temp_path.exists():
        temp_path.mkdir()

    return home_path, temp_path


TRADER_DIR, TEMP_DIR = _get_trader_dir(".vntrader")
sys.path.append(str(TRADER_DIR))
print("sys.path append: {str(TRADER_DIR)}")


def get_file_path(filename):
    """
    Get path for temp file with filename.
    """
    return TEMP_DIR.joinpath(filename)


def get_folder_path(folder_name):
    """
    Get path for temp folder with folder name.
    """
    folder_path = TEMP_DIR.joinpath(folder_name)
    if not folder_path.exists():
        folder_path.mkdir()
    return folder_path


def get_icon_path(filepath, ico_name):
    """
    Get path for icon file with ico name.
    """
    ui_path = Path(filepath).parent
    icon_path = ui_path.joinpath("ico", ico_name)
    return str(icon_path)


def load_json(filename):
    """
    Load data from json file in temp path.
    """
    filepath = get_file_path(filename)
    print(filename)
    if filepath.exists():
        with io.open(str(filepath), mode="r", encoding="UTF-8") as f:
            data = json.load(f)
        return data
    else:
        save_json(filename, {})
        return {}


def save_json(filename, data):
    """
    Save data into json file in temp path.
    """
    filepath = get_file_path(filename)
    print("abc",filepath)
    print(data)
    with io.open(str(filepath), mode="w+", encoding="UTF-8") as f:
        f.write(unicode(json.dumps(data, ensure_ascii=False)))

def round_to(value, target) :
    """
    Round price to price tick value.
    """
    value = Decimal(str(value))
    target = Decimal(str(target))
    rounded = float(int(round(value / target)) * target)
    return rounded


def floor_to(value, target) :
    """
    Similar to math.floor function, but to target float number.
    """
    value = Decimal(str(value))
    target = Decimal(str(target))
    result = float(int(floor(value / target)) * target)
    return result


def ceil_to(value, target):
    """
    Similar to math.ceil function, but to target float number.
    """
    value = Decimal(str(value))
    target = Decimal(str(target))
    result = float(int(ceil(value / target)) * target)
    return result


def print_dict(d):
    """返回dict的字符串类型"""
    return '\n'.join(['{key}:{d[key]}' for key in sorted(d.keys())])


def append_data(self, file_name, dict_data, field_names = []):
    """
    添加数据到csv文件中
    :param file_name:  csv的文件全路径
    :param dict_data:  OrderedDict
    :return:
    """
    dict_fieldnames = sorted(list(dict_data.keys())) if len(field_names) == 0 else field_names

    try:
        if not os.path.exists(file_name):
            print(u'create csv file:{}'.format(file_name))
            with open(file_name, 'a', encoding='utf8', newline='\n') as csvWriteFile:
                writer = csv.DictWriter(f=csvWriteFile, fieldnames=dict_fieldnames, dialect='excel')
                print(u'write csv header:{}'.format(dict_fieldnames))
                writer.writeheader()
                writer.writerow(dict_data)
        else:
            with open(file_name, 'a', encoding='utf8', newline='\n') as csvWriteFile:
                writer = csv.DictWriter(f=csvWriteFile, fieldnames=dict_fieldnames, dialect='excel',
                                        extrasaction='ignore')
                writer.writerow(dict_data)
    except Exception as ex:
        print(u'append_data exception:{}'.format(str(ex)))


def import_module_by_str(import_module_name):
    """
    动态导入模块/函数
    :param import_module_name:
    :return:
    """
    import traceback
    from importlib import import_module, reload

    # 参数检查
    if len(import_module_name) == 0:
        print('import_module_by_str parameter error,return None')
        return None

    print('trying to import {}'.format(import_module_name))
    try:
        import_name = str(import_module_name).replace(':', '.')
        modules = import_name.split('.')
        if len(modules) == 1:
            mod = import_module(modules[0])
            return mod
        else:
            loaded_modules = '.'.join(modules[0:-1])
            print('import {}'.format(loaded_modules))
            mod = import_module(loaded_modules)

            comp = modules[-1]
            if not hasattr(mod, comp):
                loaded_modules = '.'.join([loaded_modules,comp])
                print('realod {}'.format(loaded_modules))
                mod = reload(loaded_modules)
            else:
                print('from {} import {}'.format(loaded_modules,comp))
                mod = getattr(mod, comp)
            return mod

    except Exception as ex:
        print('import {} fail,{},{}'.format(import_module_name,str(ex),traceback.format_exc()))

        return None