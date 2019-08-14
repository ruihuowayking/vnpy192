# encoding: UTF-8
from __future__ import print_function
import sqlite3
#use file db to store log first
#change to memory db later and do the sync between memory and file

def insertorder(orderdata):
    try:
        conn = sqlite3.connect('/home/leon/sqllitedb/tradelog_vnpy')
        c = conn.cursor()
        
        insertsql = "INSERT INTO tradeorders "
        insertsql = insertsql + "(orderdate,exchangeid,contract,entryprice,"
        insertsql = insertsql + "orderoffset,orderdirection,orderqty,strategyname,"
        insertsql = insertsql + "ordertime,remark1,remark2 ) VALUES  " 
        
        insertsql = insertsql + "(?,?,?,?,?,?,?,?,?,?,?)"
        
        c.execute(insertsql, orderdata);
        
        
        conn.commit()
        conn.close()
    except:
        print("Exception!")
        print(orderdata)
        conn.close()
rawdata = ["2019-08-14","SFE","rb1910",3788,"OPEN","LONG",2,"Turtle","2019-08-14 09:10:10","",""]
orderdata = tuple(rawdata)   
insertorder(orderdata)
print("OK")