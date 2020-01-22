# encoding: UTF-8

"""
DualThrust交易策略 by Leon 
"""

from datetime import time
import talib
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate, BarGenerator, ArrayManager
from sqlalchemy.sql.expression import false
from vnpy.trader.app.LeonOrderLog.leonlogengine import persisttrade
import pandas as pd
from datetime import datetime
########################################################################
class EMAC_IntraDayCommonStrategy(CtaTemplate):
    """DualThrust交易策略"""
    className = 'EMAC_IntraDayCommonStrategy'
    author = u'Leon Zhao'

    # 策略参数
    fixedSize = 1
    fast1 = 5
    slow1 = 21
    
    fast2 = 8
    slow2 = 34
    
    fast3 = 13
    slow3 = 55
    dbpath = "./sr.csv"
    cumrange = 0
    shreshhold = 0.3
    atrDays = 20
    atrValue = 0
    initDays = 35
    # 策略变量
    barList = []                # K线对象的列表

    longEntry = 0
    shortEntry = 0
    exitTime = time(hour=15, minute=20) #will not cover position when day close

    longEntered = False
    shortEntered = False

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol'
                 ]    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'cumrange',
               'longEntry',
               'shortEntry',
               'exitTime']
    range = 0 
    longEntry1 = 0
    shortEntry1 = 0
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos','range','longEntry1','shortEntry1']    

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(EMAC_IntraDayCommonStrategy, self).__init__(ctaEngine, setting) 
        
        self.bg = BarGenerator(self.onBar,onDayBar = self.ondayBar,vtSymbol =self.vtSymbol)
        self.am = ArrayManager()
        self.indexam = ArrayManager()
        self.barList = []
        self.longEntry1 = 0
        self.shortEntry1 = 0        
        # Read Parameters from Setting files
        if 'strParams' in setting:
            self.params = setting['strParams']
            if len(self.params)>=3:
                for p in self.params:
                    if p[0] == 'unit':
                        self.fixedSize = p[1]
                    if p[0] == 'p1':
                        self.fast1 = p[1]
                    if p[0] == 'p2':
                        self.slow1 = p[1]
                    if p[0] == 'p3':
                        self.fast2 = p[1]
                    if p[0] == 'p4':
                        self.slow2 = p[1]  
                    if p[0] == 'p5':
                        self.fast3 = p[1]                                                 
                    if p[0] == 'p6':
                        self.slow3 = p[1] 
                    if p[0] == 'p7':
                        self.dbpath = p[1] 
        else:
            # 策略参数
            self.fast1 = 5
            self.slow1 = 21
            
            self.fast2 = 8
            self.slow2 = 34
            
            self.fast3 = 13
            self.slow3 = 55
            self.dbpath = "./sr.csv"
        #print(self.fixedSize,self.k1,self.k2,self.rangeDays,self.initDays)             
        self.cumrange = 0
        self.shreshhold = 0.3
        self.atrDays = 20
        self.atrValue = 0
        self.initDays = 100
        self.longEntry = 0
        self.shortEntry = 0
        self.exitTime = time(hour=15, minute=20) #will not cover position when day close
        self.longEntered = False
        self.shortEntered = False
        self.emac_kpi = 0
        self.emac1scalar = 7.5
        self.emac2scalar = 5.3
        self.emac3scalar = 3.7
        self.pcstd = 0
        self.weights = [0.35,0.3,0.35]

    def loadIndexBar(self,dbpath):
        csvfile = "../TdxData/bar_data/"+dbpath
        #print(csvfile)
        dfindex = pd.read_csv(csvfile,parse_dates=True,index_col = 0)
        #print(dbpath)
        dfindex["pc"] =dfindex["close"]- dfindex["close"].shift(-1)
        #dfordered = dfindex.sort_index( ascending=False)
        daybar  = VtBarData()
       
        dt = datetime.now()
        for idx,indexbar in dfindex.iterrows():
            #print(idx)
            daybar.vtSymbol = self.vtSymbol
            daybar.symbol = self.vtSymbol
            daybar.exchange = ""
        
            daybar.open = indexbar["open"]
            daybar.high = indexbar["high"]
            daybar.low = indexbar["low"]  
            daybar.close = indexbar["close"]     
            #dt = datetime.strptime(str(indexbar["trade_date"]),"%Y%m%d")      
            #change bar Date to next day if time is night
            #nextDay = 
            daybar.datetime = idx    # 以第一根分钟K线的开始时间戳作为X分钟线的时间戳
            daybar.date = daybar.datetime.strftime('%Y%m%d')
            daybar.time = daybar.datetime.strftime('%H:%M:%S.%f')      
            #print(daybar.datetime,daybar.close)
            self.indexam.updateBar(daybar)       
        temp = dfindex["pc"].rolling(20,min_periods=20).std()
        temp = temp.dropna()
        self.pcstd = temp.iloc[-1]
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
    
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        #dbpath = ""
        self.loadIndexBar(self.dbpath)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        #ignore data before real open
        if (tick.datetime.hour == 8 or tick.datetime.hour ==20):
            return
        self.bg.updateTick(tick)
        
    def calcUnitNo(self,atr,fixSize):
        dtCap = 0.0
        defaultCap = 0.0
        unitNo = 0
        cust = []
        var_sizelist = CtaTemplate.vol_Size
        var_size = 0.0
        var_Symbol = ""
        if len(var_sizelist) == 0:
            return fixSize
        else:
            var_Symbol = var_Symbol.join(list(filter(lambda x: x.isalpha(),self.vtSymbol)))            
            var_size = float(var_sizelist[var_Symbol][0])
            if var_size -0 < 0.01:
                return fixSize
        
        var_temp = 0.0
        if len(CtaTemplate.cust_Setting) > 0:
            cust = CtaTemplate.cust_Setting
        for cs in cust:
            if cs["StrategyGroup"] == "DT" and cs["Status"] == 'True':
                dtCap = cs["CaptialAmt"]
                break
            if cs["StrategyGroup"] == "Default" and cs["Status"] == 'True':
                defaultCap = cs["CaptialAmt"]
        if dtCap > 0:
            self.capConfig = float(dtCap)
        elif defaultCap > 0 :
            self.capConfig = float(defaultCap)
        else:
            self.capConfig = 0.0
        
        unitNo = 0
        if self.capConfig -0 < 0.0001:
            unitNo = fixSize
        elif var_size - 0 < 0.001:
            unitNo = fixSize
        else:
            unitNo = int(self.capConfig * 0.0088 /(atr*var_size))
        if unitNo < 1:
            unitNo = 1

        return unitNo    
       
    #---------calcuate range for the last several days 
    def getUnitNo(self):
        if self.am.count >= self.atrDays + 1 :
            self.atrValue = self.am.atr(self.atrDays,False)
            if self.atrValue > 0 :
                self.fixedSize = self.calcUnitNo(self.atrValue, self.fixedSize)          
        else:
            pass          
    
    def CalcKPI(self):
        #pass
        emafast1 = self.indexam.ema(self.fast1)
        emaslow1 = self.indexam.ema(self.slow1)
        emafast2 = self.indexam.ema(self.fast2)
        emaslow2 = self.indexam.ema(self.slow2)       
        emafast3 = self.indexam.ema(self.fast3)
        emaslow3 = self.indexam.ema(self.slow3)
        
        kpi = self.emac1scalar * (emafast1-emaslow1)*self.weights[0]/self.pcstd + self.emac2scalar *(emafast2-emaslow2)*self.weights[1]/self.pcstd + self.emac3scalar *(emafast3-emaslow3)*self.weights[2]/self.pcstd
        return kpi   
        #indexvol = self.indexam
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        
        if self.reduceCountdown() > 0:
            return
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）

        self.cancelAll()

        self.bg.updateBar(bar)
        barLength = 0
        barLength = self.atrDays   + 1      
        if self.am.count < barLength:
            return        
        # 计算指标数值
        self.barList.append(bar)
        
        if len(self.barList) <= 2:
            return
        else:
            self.barList.pop(0)
        lastBar = self.barList[-2]
        
        self.getUnitNo()
        self.emac_kpi = self.CalcKPI()
        #print(self.emac_kpi,bar.close)
        pos_multiple = 1
        if abs(self.emac_kpi) > 30:
            pos_multiple = 2
        else:
            pos_multiple = 1
        #print(self.emac_kpi)    
        if True: # Trade Time, no matter when, just send signal
            if self.pos == 0:
                self.longEntered = False
                self.shortEntered = False                
                if self.emac_kpi > 1 :
                        self.buy(bar.close,self.fixedSize*pos_multiple)
                elif self.emac_kpi < -1:
                        self.short(bar.close,self.fixedSize*pos_multiple)
                else:
                    pass
                
    
            # 持有多头仓位
            elif self.pos > 0:
                self.longEntered = True
                self.shortEntered = False
                # 多头止损单
                if self.emac_kpi < 1 and self.emac_kpi > -1:
                    #self.sell(self.shortEntry -2 , self.fixedSize)
                    self.sell(bar.close,abs(self.pos))
                    # 空头开仓单
                elif self.emac_kpi < -1:   
                    self.sell(bar.close,abs(self.pos))# close first then open new 
                    if not self.shortEntered:
                        #self.short(self.shortEntry -2 , self.fixedSize)
                        self.short(bar.close,self.fixedSize*pos_multiple)
            # 持有空头仓位
            elif self.pos < 0:
                self.shortEntered = True
                self.longEntered = False
                # 空头止损单
                if self.emac_kpi > -1 and self.emac_kpi < 1:
                    #self.cover(self.longEntry + 2, self.fixedSize)                
                    self.cover(bar.close,abs(self.pos))
                     # 多头开仓单
                    
                elif self.emac_kpi > 1:
                    self.cover(bar.close,abs(self.pos))# close first then open new
                    if not self.longEntered:
                        #self.buy(self.longEntry + 2, self.fixedSize)
                        self.buy(bar.close,self.fixedSize)
        # 收盘平仓 This will not execute
        else:
            if self.pos > 0:
                self.sell(bar.close * 0.99, abs(self.pos))
            elif self.pos < 0:
                self.cover(bar.close * 1.01, abs(self.pos))
 
        # 发出状态更新事件
        self.putEvent()
    #update day chart
    def ondayBar(self, dayBar):
        """收到日线推送（必须由用户继承实现）"""
        self.am.updateBar(dayBar)
        self.range = None
        self.dayOpen = 0
        # 发出状态更新事件
        self.putEvent() 
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        persisttrade(self.vtSymbol,self.className ,trade)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
