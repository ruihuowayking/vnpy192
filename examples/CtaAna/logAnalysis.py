# encoding: UTF-8
from __future__ import print_function
import sqlite3
import pandas as pd
from vnpy.trader.vtFunction import getJsonPath
from vnpy.trader.vtUtility import get_VolSize
result = pd.read_csv("./pal_templt.csv")
tr = result
volSize = get_VolSize()  
#print(volSize)
def match_transaction(data,result):
    #print("hello")
    data["closestatus"] = 0 # 0 not process yet;1 match closed;2 partial match, partial close
    data["qty"] = data["orderqty"]
    data.loc[data.orderoffset == u'平昨', 'orderoffset'] = u'平仓'
    #print(data[['contract','orderoffset']])
    #data["qty"]=data.apply(lambda r:judgeLevel(r),axis=1)
    #data[data["orderdirection"]=="空"]["qty"] = data[data["orderdirection"]=="空"]["qty"]*(-1)
    #data.to_csv("./test.csv")
    opens = data[data["orderoffset"]==u"开仓"]
    opens = opens.reset_index(drop=True)
    closes = data[data["orderoffset"]==u"平仓"]
    closes = closes.reset_index(drop=True)
    #print("123",opens)
    partial = []
    for index,row in opens.iterrows():
        #print(index, row["qty"])
        #continue
        #print(index)
        cursymbol = row["contract"]
        otime = row["ordertime"] 
        odir = row["orderdirection"]
        oprice = row["entryprice"]
        oqty = row["qty"]      
        #if odir == "空":
        #    oqty = oqty * -1    
        ctime = otime
        cprice = 0
        cstatus = 0
        cmatch = False  
        tomatch = oqty
        closes = closes.reset_index(drop=True)
        
        for ix,rw in closes.iterrows():
            partial = []
            pt = ("",0,0)
            if tomatch == oqty:
                if cursymbol == rw["contract"]  and otime < rw["ordertime"]:
                    if odir != rw["orderdirection"] and oqty == rw["qty"]:
                        ctime = rw["ordertime"]
                        cprice = rw["entryprice"]
                        cstatus = 1
                        cmatch = True
                        closes.drop(index = ix,inplace = True)
                        #del(ix)
                        break
                    elif odir != rw["orderdirection"] and oqty < rw["qty"]:
                        ctime = rw["ordertime"]
                        cprice = rw["entryprice"]
                        cstatus = 1
                        cmatch = True
                        d_index = list(closes.columns).index('qty')
                        #print(closes.iloc[ ix,d_index])
                        closes.iloc[ ix,d_index] = rw["qty"] - oqty
                        #closes.del(ix)
                        break                    
                    
                    elif odir != rw["orderdirection"] and oqty > rw["qty"]:
                        
                        ctime = rw["ordertime"]
                        cprice = rw["entryprice"]
                        cstatus = 2
                        #cmatch = True 
                        pt = (ctime,cprice,rw["qty"])
                        tomatch = oqty - rw["qty"]   
                        partial = partial.append(pt)
                        closes.drop(index = ix,inplace = True)
                        continue
                    else:
                        pass
            else:
                if cursymbol == rw["contract"]  and otime < rw["ordertime"]:
                    if odir != rw["orderdirection"] and tomatch == rw["qty"]:
                        ctime = rw["ordertime"]
                        cprice = rw["entryprice"]
                        cstatus = 1
                        cmatch = True
                        pt = (ctime,cprice,rw["qty"])
                        partial = partial.append(pt)
                        closes.drop(index = ix,inplace = True)                 
                        break
                    elif odir != rw["orderdirection"] and tomatch < rw["qty"]:
                        ctime = rw["ordertime"]
                        cprice = rw["entryprice"]
                        cstatus = 1
                        cmatch = True
                        #closes[ix]["qty"] = rw["qty"] - oqty
                        d_index = list(closes.columns).index('qty')
                        #print(d_index)
                        #print(ix)
                        #closes.to_csv("./test.csv")
                        #print(closes.iloc[ ix,d_index])
                        closes.iloc[ ix,d_index] = rw["qty"] - oqty
                        pt = (ctime,cprice,rw["qty"])
                        partial = partial.append(pt)
                        #closes.del(ix)
                        break                                
                    elif odir != rw["orderdirection"] and tomatch > rw["qty"]:
                        
                        ctime = rw["ordertime"]
                        cprice = rw["entryprice"]
                        cstatus = 2
                        #cmatch = True 
                        pt = (ctime,cprice,rw["qty"])
                        tomatch = tomatch - rw["qty"]   
                        partial = partial.append(pt)
                        closes.drop(index = ix,inplace = True)
                        continue
                    else:
                        pass
                else:
                    pass
        
                                                
        oneline = dict(result.iloc[0])
        oneline["strategyname"] = row["strategyname"]
        oneline["contract"] = row["contract"]
        oneline["entryprice"] = row["entryprice"]
        oneline["orderoffset"] = row["orderoffset"]
        oneline["orderdirection"] = row["orderdirection"]  
        oneline["orderqty"] = row["orderqty"]  
        oneline["ordertime"] = row["ordertime"]  

                      
        
        if cmatch != True:
            print("there may have something wrong or open")
            oneline["closestatus"] = 0 
            oneline["closetime"] = ""
            oneline["closeprice"] = 0             
            #oneline["orderdirection"] = row["orderdirection"]              
        else:
            if partial :
                #print(partial)
                cprice = 0
                tqty = 0
                for sub in partial:
                    #print(sub)
                    ctime = sub[0]
                    cprice = cprice + sub[1]
                    tqty = tqty + sub[2]
                if tqty != oqty:
                    print("Amount is not match, check!")
                cprice = cprice /len(pt)
            else:
                oneline["closetime"] = ctime
                oneline["closeprice"] = cprice
            #oneline["closestatus"] = 1
            
        sss = pd.Series(oneline,name = "temp")
        result =  result.append(sss,ignore_index = True)      
    print(closes)
    return result
                        

def calcpal(row,vs): 
    lvsign = 1
    mult = 10
    pal = 0
    mult = vs[row["comdt"]][0]
    if row["closestatus"] == 1 :   
        if(row["orderdirection"] != u"多"):
            lvsign = -1
        else:
            lvsign = 1
        pal = (float(row["closeprice"])-float(row["entryprice"]))* mult*lvsign
    else:
        pal = 0
    return pal                   

conn = sqlite3.connect('../../../sqllitedb/tradelog_vnpy.db')



sqlstr = "select strategyname,upper(contract) as contract,entryprice,orderoffset,orderdirection,orderqty,ordertime from tradeorders where strategyname = :st order by  upper(contract) asc,ordertime  asc"

strlist = "select distinct strategyname from tradeorders"

c1 = conn.cursor()
c2 = conn.cursor()
c1 = c1.execute(strlist)
i = 0
for row in c1:
    #print(str(row[0]))
    data = pd.read_sql(sql=sqlstr, con=conn, params={'st': str(row[0])})
    #print(data)
    #data.to_csv("./log.csv")
    temp = match_transaction(data,result)
    tr = tr.append(temp)
    #break
    
tr.drop(index = 0,inplace = True)
tr = tr.reset_index(drop=True)

#tr["comdt"] = tr["contract"][:2]
tr["comdt"] = tr["contract"].apply(lambda x:x[:2] if x[:2].isalpha() else x[0])
upvol =  {k.upper(): v for k, v in volSize.items()}
tr.to_csv("./tr.csv",encoding='utf-8')
#lambda f: calcpal
tr["pal"] = tr.apply(lambda row: calcpal(row,upvol), axis=1 )

#tr["pal"] = tr.apply(lambda row:ccc(row), axis=1)
tr.to_csv("./tr.csv",encoding='utf-8')
conn.close()  






















