# encoding: UTF-8

from __future__ import print_function
import json
from datetime import datetime, timedelta, time
import requests
from pymongo import MongoClient

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME, TICK_DB_NAME
from vnpy.trader.vtUtility import get_VolSize
from vnpy.trader.vtFunction import getJsonPath
# 这里以商品期货为例
from bson.son import SON
import sys


def getSymbolMapping(): 
    symbolMap = {}
    dataContent = ""
    settingFileName = 'DR_mapping.json'
    settingfilePath = getJsonPath(settingFileName, __file__)      
    with open(settingfilePath, 'r') as fileObj:
        #print(f.read())
        dataContent = fileObj.read()
        #print(dataContent)
    symbolMap = json.loads(dataContent)   
    return symbolMap     
 
def removeRepeat(repeatDt, mgClient,var_CloseTime):
    

    try:

        for record in repeatDt:
            if record["time"]=="14:59:00" or record["time"]=="14:59:00.000" or record["time"]=="14:59:00.000000" :
                continue
            elif record["time"]=="15:14:00" or record["time"]=="115:14:00.000" or record["time"]=="15:14:00.000000" :
                continue
            elif record["time"] < var_CloseTime:
                continue 
            else:
                wCnt = mgClient.remove({'_id': record['_id']})
                #WriteResult.nRemoved
                print("removed " + str(wCnt["n"])+" duplicated with time:"+str(record["time"])+"!")


    except Exception as e:
        print("Mongo error when deleting duplicates %s", str(e))          
def findRepeatData(dbName, collectionName, start,end,cfgdata,cfgMap):
    """
    如果当日数据没有，从新浪抓取，补充开（9点）高，低收4根K线。
    """
    print(u'\n补充日线数据：%s, 集合：%s, 起始日：%s' %(dbName, collectionName, start))
    
    var_Symbol = ""
    var_Symbol = var_Symbol.join(list(filter(lambda x: x.isalpha(),collectionName)))            

    startDate = start.replace(hour=9, minute=0, second=0, microsecond=0)
    endDate = end.replace(hour=15, minute=30, second=0, microsecond=0)
    conMonth = collectionName[-3:]
    if conMonth == '901':
        return
    
    var_CloseTime = "14:59:00"            
    var_CloseTime = cfgdata[var_Symbol][1] 
    var_CloseTimeList =  var_CloseTime.split(":")   
  
    
    contractCode = cfgMap[collectionName][0]
    urlType = cfgMap[collectionName][1]
    startString = datetime.strftime(startDate,'%Y-%m-%d %H:%M:%S') 
    endString = datetime.strftime(endDate,'%Y-%m-%d %H:%M:%S') 
    
    mc = MongoClient('localhost', 27017)    # 创建MongoClient
    cl = mc[dbName][collectionName]         # 获取数据集合 
    tempDate = startDate
    recDate = ""
    while tempDate < endDate:
        recDate = tempDate.strftime( '%Y%m%d' ) 
        pipeline = {"$and":[{"date":recDate},{"time":{"$lte":"15:16:00.000000"}},{"time":{"$gt":"14:59:00"}}]}
        
        #pprint.pprint(list(db.things.aggregate(pipeline)))
        closeDataCursor = cl.find(pipeline) 
        closeData = list(closeDataCursor[:])
        if (len(closeData)>0):
            removeRepeat(closeData,cl,var_CloseTime)
        tempDate = tempDate + timedelta(1)
        
        
    print(u'\n清理重复数据完成：%s, 集合：%s, 起始日：%s' %(dbName, collectionName, start))          
#----------------------------------------------------------------------
def runDataChecking():
    """运行数据清洗"""
    print(u'开始数据清洗工作')
    
    # 加载配置
    setting = {}
    with open("DR_setting.json") as f:
        setting = json.load(f)
    
    volSize = get_VolSize()  
    symbolMap = getSymbolMapping() 
    print(symbolMap)
    # 遍历执行清洗
    today = datetime.now()
    start = today - timedelta(10)   # 清洗过去10天数据
    end = start + timedelta(9)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = today.replace(hour=16, minute=0, second=0, microsecond=0)
    #start = datetime.strptime('2019-03-13 00:00:00', '%Y-%m-%d %H:%M:%S')
    #end = datetime.strptime('2019-07-01 16:00:00', '%Y-%m-%d %H:%M:%S')
        
    for l in setting['bar']:
        symbol = l[0]
        
        #fillMissingData(MINUTE_DB_NAME, symbol, start,volSize,symbolMap)
        findRepeatData(MINUTE_DB_NAME, symbol, start,end,volSize,symbolMap)
    
    print(u'数据清洗工作完成')
    

if __name__ == '__main__':
    runDataChecking()
