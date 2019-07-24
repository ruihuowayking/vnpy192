# encoding: UTF-8

from __future__ import print_function
import json
from datetime import datetime, timedelta, time

from pymongo import MongoClient

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME, TICK_DB_NAME
from vnpy.trader.vtUtility import get_VolSize
# 这里以商品期货为例
MORNING_START = time(9, 0)
MORNING_REST = time(10, 15)
MORNING_RESTART = time(10, 30)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 30)
AFTERNOON_END = time(15, 0)
NIGHT_START = time(21, 0)
NIGHT_END = time(2, 30)


#----------------------------------------------------------------------
def cleanData(dbName, collectionName, start):
    """清洗数据"""
    print(u'\n清洗数据库：%s, 集合：%s, 起始日：%s' %(dbName, collectionName, start))
    
    mc = MongoClient('localhost', 27017)    # 创建MongoClient
    cl = mc[dbName][collectionName]         # 获取数据集合
    d = {'datetime':{'$gte':start}}         # 只过滤从start开始的数据
    cx = cl.find(d)                         # 获取数据指针
    
    # 遍历数据
    for data in cx:
        # 获取时间戳对象
        dt = data['datetime'].time()
        
        # 默认需要清洗
        cleanRequired = True
        
        # 如果在交易事件内，则为有效数据，无需清洗
        if ((MORNING_START <= dt < MORNING_REST) or
            (MORNING_RESTART <= dt < MORNING_END) or
            (AFTERNOON_START <= dt < AFTERNOON_END) or
            (dt >= NIGHT_START) or
            (dt < NIGHT_END)):
            cleanRequired = False
            
        if (data['time']=="15:14:00.000000" or data['time']=="15:14:00" )and (collectionName[:2] == 'T1' or collectionName[:2] == 'T2' or collectionName[:2] == 'IF' or collectionName[:2] == 'IC' or collectionName[:2] == 'IH'):
            cleanRequired = False
        theTime = data['time']
        if theTime == '':
            cleanRequired = True
        # 如果需要清洗
        if cleanRequired:
            print(u'删除无效数据，时间戳：%s' %data['datetime'])
            cl.delete_one(data)
    
    print(u'清洗完成，数据库：%s, 集合：%s' %(dbName, collectionName))
    
def fillCloseData(dbName, collectionName, start,cfgdata):
    """
    如果收盘数据,比如14点59数据没有，使用前一根K线的数据。
    """
    print(u'\n补充收盘数据：%s, 集合：%s, 起始日：%s' %(dbName, collectionName, start))
    
    var_Symbol = ""
    var_Symbol = var_Symbol.join(list(filter(lambda x: x.isalpha(),collectionName)))            
    var_Time = cfgdata[var_Symbol][1]
    timeList = var_Time.split(":")
    startDate = start.replace(hour=int(timeList[0]), minute=int(timeList[1]), second=int(timeList[2]), microsecond=0)

    mc = MongoClient('localhost', 27017)    # 创建MongoClient
    cl = mc[dbName][collectionName]         # 获取数据集合 

    while startDate <  datetime.now():
        searchItem = {'datetime':startDate}  
        searchResult = cl.find_one(searchItem)
        if searchResult == None:
            for xMinAgo in range (1,30):
                searchTime = startDate - timedelta(minutes = xMinAgo)
                tempItem = {'datetime':searchTime}  
                tempResult = cl.find_one(tempItem)  
                if tempResult != None:
                    #print(tempResult)
                    tempResult["datetime"] = startDate
                    tempResult["time"] = var_Time
                    tempResult["date"] = startDate.strftime("%Y%m%d")
                    del tempResult["_id"]                  
                    insertResult = cl.insert_one(tempResult)
                    print("fill in data for:",startDate)
                    break
                else:
                    pass
            
                                
        else:
            pass
        startDate = startDate + timedelta(1)  
    print(u'\n补充收盘数据完成：%s, 集合：%s, 起始日：%s' %(dbName, collectionName, start))        
#----------------------------------------------------------------------
def runDataCleaning():
    """运行数据清洗"""
    print(u'开始数据清洗工作')
    
    # 加载配置
    setting = {}
    with open("DR_setting.json") as f:
        setting = json.load(f)
    
    volSize = get_VolSize()    
    # 遍历执行清洗
    today = datetime.now()
    start = today - timedelta(10)   # 清洗过去10天数据
    start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for l in setting['tick']:
        symbol = l[0]
        cleanData(TICK_DB_NAME, symbol, start)
        
    for l in setting['bar']:
        symbol = l[0]
        cleanData(MINUTE_DB_NAME, symbol, start)
        fillCloseData(MINUTE_DB_NAME, symbol, start,volSize)
    
    print(u'数据清洗工作完成')
    

if __name__ == '__main__':
    runDataCleaning()
