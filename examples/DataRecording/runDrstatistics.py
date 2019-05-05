# encoding: UTF-8

from __future__ import print_function
import json
from datetime import datetime, timedelta, time

from pymongo import MongoClient

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME, TICK_DB_NAME

import pandas as pd
# 这里以商品期货为例,Index Futures have problems
MORNING_START = time(9, 0)
MORNING_REST = time(10, 15)
MORNING_RESTART = time(10, 30)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 30)
AFTERNOON_END = time(15, 0)
NIGHT_START = time(21, 0)
NIGHT_END = time(2, 30)


#----------------------------------------------------------------------
def countData(dbName, collectionName, start,intervalStart):
    """清洗数据"""
    print(u'\n计算数据库：%s, 集合：%s, 日期：%s' %(dbName, collectionName, start))
    
    mc = MongoClient('localhost', 27017)    # 创建MongoClient
    cl = mc[dbName][collectionName]         # 获取数据集合
                     # 获取数据指针

    #dt = datetime.time()
    ts = datetime.now()
    dt = ts.time()

    totalCnt = 0
    deltaCnt = 0
    
    # 如果在交易事件内，则为有效数据，无需清洗
    if ((MORNING_START <= dt < MORNING_REST) or
        (MORNING_RESTART <= dt < MORNING_END) or
        (AFTERNOON_START <= dt < AFTERNOON_END) or
        (dt >= NIGHT_START) or
        (dt < NIGHT_END)):
        d = {'datetime':{'$gte':start}}         # 只过滤从start开始的数据
        e = {'datetime':{'$gte':intervalStart}}         # 只过滤从start开始的数据
        totalCnt  = cl.find(d).count()
        deltaCnt  = cl.find(e).count()

    
    print(u'计算完成，数据库：%s, 集合：%s,总数:%s,Delta:%s' %(dbName, collectionName,totalCnt,deltaCnt))
    return totalCnt,deltaCnt

    
def runDataCleaning():
    """运行数据统计"""
    print(u'开始数据统计工作')
    
    # 加载配置
    setting = {}
    with open("DR_setting.json") as f:
        setting = json.load(f)
    
    # 遍历执行清洗
    today = datetime.now()
    start = today   # 统计当天数据
    start.replace(hour=0, minute=0, second=0, microsecond=0)
    countInterval = 30
    intervalStart = today - timedelta(minutes = countInterval)  
    # 默认时间间隔
        
    outList = []
    singleLine = []
    for l in setting['tick']:
        symbol = l[0]
        totalCnt, deltaCnt = countData(TICK_DB_NAME, symbol, start,intervalStart)
        singleLine = ['Tick',symbol,totalCnt,deltaCnt]
        outList.append(singleLine)
    for l in setting['bar']:
        symbol = l[0]
        totalCnt, deltaCnt = countData(MINUTE_DB_NAME, symbol, start,intervalStart)
        singleLine = ['Bar',symbol,totalCnt,deltaCnt]
        outList.append(singleLine)
    tick = [i[0] for i in outList]
    contract = [i[1] for i in outList]
    total = [i[2] for i in outList]
    deltaCnt = [i[3] for i in outList]
    
    tempDict = {'DataType':tick,'Contract':contract,'TodayTotal':total,'DeltaValue':deltaCnt}
    cntDF = pd.DataFrame(tempDict)
    lv_out = "report" + datetime.now().strftime("%Y%m%d%H%M%S") + ".csv"
    cntDF.to_csv("../../../drOutput/"+lv_out)
    print(outList)
    print(cntDF)
    print(u'统计完成')
    

if __name__ == '__main__':
    runDataCleaning()
