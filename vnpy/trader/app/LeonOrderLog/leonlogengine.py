# encoding: UTF-8
from __future__ import print_function
import sqlite3
import time
#use file db to store log first
#change to memory db later and do the sync between memory and file

def insertorder(orderdata):
    insertsql = "INSERT INTO tradeorders "
    insertsql = insertsql + "(orderdate,exchangeid,contract,entryprice,"
    insertsql = insertsql + "orderoffset,orderdirection,orderqty,strategyname,"
    insertsql = insertsql + "ordertime,remark1,remark2 ) VALUES  " 
        
    insertsql = insertsql + "(?,?,?,?,?,?,?,?,?,?,?)"    
    conn = sqlite3.connect('/home/leon/sqllitedb/tradelog_vnpy.db')
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
        print("Re try Exception!")
        print(orderdata)  
    c.close()
    conn.close()    
'''              
rawdata = ["2019-08-14","SFE","rb1910",3788,"OPEN","LONG",2,"Turtle","2019-08-14 09:10:10","",""]
orderdata = tuple(rawdata)   
insertorder(orderdata)
print("OK")
'''