# encoding: UTF-8
from __future__ import print_function
from vnpy.trader.vtConstant import (DIRECTION_LONG, DIRECTION_SHORT,
                                    OFFSET_OPEN, OFFSET_CLOSE,
                                    STATUS_ALLTRADED, STATUS_CANCELLED, STATUS_REJECTED) 
import sqlite3
import time
import datetime
#use file db to store log first
#change to memory db later and do the sync between memory and file

def persisttrade(vtsymbol,strname,tradedata):
    
    cdate = datetime.date.today()
    slip = 0 # do not count slip by now, add later
    exid = ""
    contract = vtsymbol
    entryprice = tradedata.price
    orderofset = tradedata.offset
    orddir = tradedata.direction
    qty = tradedata.volume
    strname = strname
    ctime = datetime.datetime.now()
        
    rm1 = ""
    rm2 = ""
    orderdata = (cdate,exid,contract,entryprice,orderofset,orddir,qty,strname,ctime,rm1,rm2)
    insertorder(orderdata)
def insertorder(orderdata):
    insertsql = "INSERT INTO tradeorders "
    insertsql = insertsql + "(orderdate,exchangeid,contract,entryprice,"
    insertsql = insertsql + "orderoffset,orderdirection,orderqty,strategyname,"
    insertsql = insertsql + "ordertime,remark1,remark2 ) VALUES  " 
        
    insertsql = insertsql + "(?,?,?,?,?,?,?,?,?,?,?)"    
    conn = sqlite3.connect('/root/sqllitedb/tradelog_vnpy.db')
    c = conn.cursor()    
    try:

        
        c.execute(insertsql, orderdata);
        
        
        conn.commit()
    except sqlite3.Error:
        print("Exception!")
        print(orderdata)
        time.sleep(3)
        if c != None:
            c.execute(insertsql, orderdata);        
            conn.commit()

    except:
        print("Retry Exception!")
        print(orderdata)  
    c.close()
    conn.close()    
'''              
rawdata = ["2019-08-14","SFE","rb1910",3788,"OPEN","LONG",2,"Turtle","2019-08-14 09:10:10","",""]
orderdata = tuple(rawdata)   
insertorder(orderdata)
print("OK")
'''