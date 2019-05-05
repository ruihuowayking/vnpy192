# encoding: UTF-8

from __future__ import print_function
import json
from datetime import datetime, timedelta, time

from pymongo import MongoClient

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME, TICK_DB_NAME


# 这里以商品期货为例
REMOVE_DAYS = 90
START_DAYS = 400


#----------------------------------------------------------------------
def cleanData(dbName, collectionName, start):
    """清洗数据"""
    print(u'\n清洗数据库：%s, 集合：%s, 起始日：%s' %(dbName, collectionName, start))
    
    mc = MongoClient('localhost', 27017)    # 创建MongoClient
    cl = mc[dbName][collectionName]         # 获取数据集合
    d = {'datetime':{'$gte':start}}         # 只过滤从start开始的数据
    cx = cl.find(d)                         # 获取数据指针
    
    today = datetime.today()

    expire_date = today - timedelta(days=REMOVE_DAYS)
    # 遍历数据
    for data in cx:
        # 获取时间戳对象
        dt = data['datetime']
        
        # 默认需要清洗
        cleanRequired = False
        
        # 如果在交易事件内，则为有效数据，无需清洗
        if (dt < expire_date):
            cleanRequired = True
        
        # 如果需要清洗
        if cleanRequired:
            print(u'删除过期数据，时间戳：%s' %data['datetime'])
            cl.delete_one(data)
    
    print(u'清洗完成，数据库：%s, 集合：%s' %(dbName, collectionName))
    


#----------------------------------------------------------------------
def runDataCleaning():
    """运行数据清洗"""
    print(u'开始数据清洗工作')
    
    # 加载配置
    setting = {}
    with open("DR_setting.json") as f:
        setting = json.load(f)
        
    # 遍历执行清洗
    today = datetime.now()
    start = today - timedelta(START_DAYS)   # 清洗过去10天数据
    start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for l in setting['tick']:
        symbol = l[0]
        cleanData(TICK_DB_NAME, symbol, start)
        
    for l in setting['bar']:
        symbol = l[0]
        cleanData(MINUTE_DB_NAME, symbol, start)
    
    print(u'数据清洗工作完成')
    

if __name__ == '__main__':
    runDataCleaning()
