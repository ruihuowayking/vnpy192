# encoding: UTF-8

from __future__ import print_function
import json
from datetime import datetime, timedelta, time

from pymongo import MongoClient

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME, TICK_DB_NAME
import requests
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
def countData(dbName, collectionName, start,end):
    """清洗数据"""
    print(u'\n计算数据库：%s, 集合：%s, 日期：%s' %(dbName, collectionName, start))
    
    mc = MongoClient('localhost', 27017)    # 创建MongoClient
    cl = mc[dbName][collectionName]         # 获取数据集合
                     # 获取数据指针



    totalCnt = 0
    todayCnt = 0
    tempCnt = 0
    
    cursorDt = start
    while cursorDt <= end:
        d = {'datetime':cursorDt}         # search close

        tempCnt   = cl.find(d).count()
        if (tempCnt == 1):
            totalCnt += 1
        if (tempCnt == 1) and (cursorDt == end):
            todayCnt = 1
        cursorDt = cursorDt + timedelta(hours = 24) 
    
    print(u'计算完成，数据库：%s, 集合：%s,total:%s,today:%s' %(dbName, collectionName,totalCnt,todayCnt))
    return totalCnt,todayCnt

    
def runCheckClosing():
    """运行数据统计"""
    print(u'开始数据统计工作')
    
    # 加载配置
    setting = {}
    with open("DR_setting.json") as f:
        setting = json.load(f)
    
    # 遍历执行清洗
    today = datetime.now()
    start = today   # 统计当天数据
    start = start.replace(hour=14, minute=59, second=0, microsecond=0) 
    end = start
    start = start - timedelta(hours = 24*5)  

        
    outList = []
    singleLine = []
    for l in setting['bar']:
        symbol = l[0]
        totalCnt, todayCnt = countData(MINUTE_DB_NAME, symbol, start,end)
        singleLine = ['Bar',symbol,totalCnt,todayCnt ]
        outList.append(singleLine)
    tick = [i[0] for i in outList]
    contract = [i[1] for i in outList]
    totalList = [i[2] for i in outList]
    todayList = [i[3] for i in outList]
    
    tempDict = {'DataType':tick,'Contract':contract,'zTotalClose':totalList,'TodayClose':todayList}
    cntDF = pd.DataFrame(tempDict)
    lv_out = "close" + datetime.now().strftime("%Y%m%d%H%M%S") + ".csv"
    cntDF.to_csv("../../../drOutput/"+lv_out)
    print(outList)
    print(cntDF)
    print(u'统计完成')
    return str(cntDF)
    
corpid = 'ww4228ea82202b6f2b',
corpsecret = ''
agentid = 1000002
# 报警通知联系人账号
NOTICE_USER_LIST = "@all"

class weixinClass(object):
    def __init__(self):
        self.token = self.get_token()
        self.resendcnt = 0
    def get_token(self):
        token_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
        values = {'corpid': corpid, 'corpsecret': corpsecret}
        req = requests.get(token_url, values)
        if req.status_code == 200:
            data = json.loads(req.text)
            if data.get('errcode') == 0:
                print('get token OK')
                return data["access_token"]
 
            else:
                print( data )
        else:
            print(req.text)
        return ''
 
    def send_msg(self, msg, to_user=NOTICE_USER_LIST):
        send_msg_url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=" + self.token
        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(self.token)
        if isinstance(msg, str):
            msg = msg + '<br>发送时间:' + now_time
        elif isinstance(msg, unicode):
            msg = msg + u'<br>发送时间:' + now_time
 
        data = {
            "touser": to_user,
            "msgtype":  "text",
            "agentid":  agentid,
            "text": {
                    "content": msg
                }
            }
        req = requests.post(send_msg_url, data=json.dumps(data))
        if req.status_code == 200:
            data = json.loads(req.text)
            errcode = data.get('errcode')
            # token过期或者过期，重新获取token并重新发送本条信息
            if errcode in [41001, 42001]:
                while self.resendcnt < 3:
                    self.resendcnt+=1
                    print('Send message False, to resend!')
                    self.token = self.get_token()
                    self.send_msg(msg)

            if errcode == 0:
                print('Send message OK')
        else:
            print("http_code: %s, error: %s" % (req.status_code, req.text))

if __name__ == '__main__':
    lvout = runCheckClosing()
    a = weixinClass()
    a.send_msg(lvout)    
