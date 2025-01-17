import random
import copy

import ClosimCommonMessageObjects

class DummyAPI(object):
    def __init__(self):
        self.rateFee = 0.000
        self.unitCurrency = 100.0
        
        self.cashFile = 'cash.txt'
        self.cashBalance = self.loadCashBalance()
        
        self.bitFile = 'bit.txt'
        self.bitBalance = self.loadBitBalance()
        
        self.nowPriceAsk = 260000.0
        self.nowPriceBid = 259500.0
        
        self.fillOrders = []
        
        self.orderFile = 'orderID.txt'
        self.orderID = self.getOrderID()
        
        self.stream = self.getPriceStreamFromCSV("./korbitKRW.csv")
        self.indexStream = 0
          
    def __del__(self):
        pass
    
    def loadCashBalance(self):
        fp = open(self.cashFile)
        temp = int(fp.readline())
        fp.close()
        return temp
    
    def saveCashBalance(self):
        fp = open(self.cashFile,'w')
        fp.write(str(self.cashBalance))
        fp.close()
        
    def loadBitBalance(self):
        fp = open(self.bitFile)
        temp = float(fp.readline())
        fp.close()
        return temp
    
    def saveBitBalance(self):
        fp = open(self.bitFile,'w')
        fp.write(str(self.bitBalance))
        fp.close()
        
    def getOrderID(self):
        fp = open(self.orderFile)
        temp = int(fp.readline())
        fp.close()
        return temp
        
    def getCashBalance(self):
        return self.cashBalance

    def getStreamLength(self):
        return len(self.stream)

    def getMarketInfo(self):        
#         self.nowPriceBid += int(random.normalvariate(0,2))*self.unitCurrency
        self.nowPriceBid = self.stream[self.indexStream]
        self.indexStream += 1
        
        self.nowPriceAsk = self.nowPriceBid + 100.0
        
        valAskAmount = abs(random.normalvariate(0,3)+2.0)
        valBidAmount = abs(random.normalvariate(0,3)+2.0)
        
        infoMarket = ClosimCommonMessageObjects.InfoMarket(self.nowPriceAsk, self.nowPriceBid, valAskAmount, valBidAmount)
        
        return infoMarket

    def cancelAllOrder(self,listNotComplete):
        pass
        
    def getFillOrder(self,orderID):
#         fred = filter(lambda person: person.name == 'Fred', peeps)[0]
#         for e in self.fillOrders:
#             print e

#         searchItems = filter(lambda fill: fill.orderID == orderID, self.fillOrders)
#         if len(searchItems) > 0:
#             searchItem = copy.deepcopy(searchItems[0])
#         else:
#             searchItem = ClosimCommonMessageObjects.InfoFill()
#         
#         
#         self.fillOrders = [item for item in self.fillOrders if item.orderID == orderID]

        searchItem = infoFill = ClosimCommonMessageObjects.InfoFill()
        newList = []
        for eachItem in self.fillOrders:
            #print eachItem
            if orderID != eachItem.orderID:
                newList.append(eachItem)
            else:
                searchItem = eachItem
        self.fillOrders = newList
        
        
        return searchItem
    
    def registerOrder(self,orderQuery):
        infoOrder = ClosimCommonMessageObjects.InfoOrder()
        infoOrder.success = True        
        infoOrder.isBuy = orderQuery.state == 'Process'
        infoOrder.orderID = self.orderID
        self.orderID += 1
        fp = open(self.orderFile,'w')
        fp.write(str(self.orderID))
        
        self.processOrder(orderQuery, infoOrder)
        
        return infoOrder 
    
    def processOrder(self,orderQuery,infoOrder):
        menu = random.randint(0,2)
        infoFill = ClosimCommonMessageObjects.InfoFill()
        infoFill.orderID = infoOrder.orderID
        infoFill.isBuy = infoOrder.isBuy
        infoFill.nextSellPrice = orderQuery.nextSellPrice
                
        cash = int(orderQuery.nextSellAmount*orderQuery.nextSellPrice)
#         print cash, orderQuery.nextSellAmount, orderQuery.nextSellPrice, self.cashBalance, infoOrder.isBuy
        if cash+int(cash*self.rateFee) > self.cashBalance and infoOrder.isBuy:
#             print "OVER CASH BALANCE!!!", cash, orderQuery.nextSellAmount, orderQuery.nextSellPrice, self.cashBalance
            infoFill.amount = self.cashBalance/orderQuery.nextSellPrice
#             print "REARRANGE", infoFill.amount, self.cashBalance, orderQuery.nextSellPrice 
        elif menu == 0:
            #full trade
            infoFill.amount = orderQuery.nextSellAmount
        elif menu == 1:
            #partially trade
            infoFill.amount = random.uniform(0,orderQuery.nextSellAmount)
        else:
            #not trade
            infoFill.amount = 0
        
        if orderQuery.state == 'Process':        
            infoFill.amount = infoFill.amount*(1.0-self.rateFee)

        self.fillOrders.append(infoFill)
        self.processCashBalance(infoFill,orderQuery)

        return False
    
    def processCashBalance(self,infoFill,orderQuery):
        if infoFill.amount > 0:
            cash = int(infoFill.amount*infoFill.nextSellPrice)
            if infoFill.isBuy:
                #print "BUY : ", cash, infoFill.amount, orderQuery.nextSellAmount, orderQuery.balanceID, orderQuery.nowSteps
                self.cashBalance -= cash
                self.bitBalance += infoFill.amount
            else:
                #print "SELL: ", cash, infoFill.amount, orderQuery.nextSellAmount, orderQuery.balanceID, orderQuery.nowSteps
                self.cashBalance += cash-int(cash*self.rateFee)
                self.bitBalance -= infoFill.amount
            self.saveCashBalance()
            self.saveBitBalance()

    def getPriceStreamFromCSV(self, nameFile):
        fileOpened = open(nameFile)
        listRawAll = fileOpened.readlines()
        fileOpened.close()
        
        listPrice = []
        
        for eachLine in listRawAll:
            listLine = eachLine.split(',')
            listPrice.append(float(listLine[1]))
            
        return listPrice
        
def testStreamProcessing(nameFile):
    listStream = getPriceStreamFromCSV(nameFile)

    stats.createPriceTable("testStream")
    for eachData in listStream:
        stats.proceedStep(eachData)
    stats.clearQuery()
    
    stats.selectAllTable()

def calInverseDownRateByRatio(ratioDown):
    return (1-ratioDown)/ratioDown

def calDigByPrices(pricePeak,priceBuy):
    return pricePeak-priceBuy

def calDigByRatioAndPeak(ratioDown,pricePeak):
    return (1-ratioDown)*pricePeak
    
def calRatioByFallAndNow(valFall,priceNow):
    return float(priceNow)/(float(priceNow)+float(valFall))

def getExpectationRatio(nowDig):
    #6000/1.1062902622635594*^7*103.79133081279231^(-x/8559.704161857346)
    #0.000542353

    #find constant to make 1 in x is zero
    #valZero = scipy.stats.norm(0,devDigs).pdf(0)
    #3ampExpectation = 1.0 - valZero
    
    #mapping   nowDig:avgDigs = x:Sigma(devDigs)
    #valMappingAvgToSigma = float(devDigs)/float(avgDigs)
    #valMapped = float(valMappingAvgToSigma)*float(nowDig)
    #print valMapped, ampExpectation
    
    return 103.79133081279231**(-nowDig/8559.704161857346)+0.26960604565535746

def calMaxRate(ratioDown,valExpect):
    #in defensive strategy
    #1.0 * 30% = 0.30
    #0.8 * 30% = 0.24
    #0.6 * 20% = 0.12
    #0.4 * 10% = 0.04
    #0.2 * 10% = 0.02
    #sum = 0.72
    
    return 0.72*valExpect*calInverseDownRateByRatio(ratioDown)

def calMinRate(ratioDown,valExpect):
    return 0.02*valExpect*calInverseDownRateByRatio(ratioDown)


    
def checkFeeConditionVal(priceNow,valFall,valFeePercent=0.000):
    ratioDown = calRatioByFallAndNow(valFall,priceNow)
    valExpect = getExpectationRatio(valFall)

    #print calMinRate(ratioDown,valExpect) , valFeePercent*(2+calMaxRate(ratioDown,valExpect))
    return calMinRate(ratioDown,valExpect) > valFeePercent*(2+calMaxRate(ratioDown,valExpect))
    
# def checkFeeConditionRatio(ratioDown,valExpect,valFeePercent=0.000):
#     return getMinRate(ratioDown,valExpect) > valFeePercent*(2+calMaxRate(ratioDown,valExpect))

def calBuyAmount(fundRemain,valExpect):
    return fundRemain*(valExpect**2)

def getRateToSell(numStep):
    #step = 5 => 30%
    #step = 4 => 30%
    #step = 3 => 20%
    #step = 2 => 10%
    #step = 1 => 10%
    #-1/6*(x^3-6x^2+5x-6)
    
    return -1.0*((numStep**3.0)-6.0*(numStep**2.0)+5.0*numStep)/60.0+0.1
    
def calSellAmount(amountBitCoin,numStep=0):
    return amountBitCoin*getRateToSell(numStep)

def getAccumRateToSell(numStep):
    accum = getRateToSell(numStep)
    for i in range(numStep):
        accum += getRateToSell(i)
    return accum

def calSellPrice(pricePeak,priceBuy,numStep=0,unitCurrency=100.0):
    priceSellReal = (numStep+1)*0.2*calDigByPrices(pricePeak,priceBuy)+priceBuy
    priceSellUnit = math.ceil(priceSellReal/unitCurrency)
    priceSellQuantized = priceSellUnit*unitCurrency
    
    return priceSellQuantized
    
def calFee(price,valFeePercent=0.000):
    return price*valFeePercent
    
def getRealTotalSell(priceNow,valFall,steps=5):
    totalCost = 0.0
    
    for i in range(steps):
        totalCost += calSellPrice(priceNow+valFall,priceNow,i,500.0)*calSellAmount(1.0,i)
        
    return totalCost
    
def calTotalFee(priceNow,valFall,valFeePercent=0.000,steps=5):  
    totalCost = getRealTotalSell(priceNow,valFall,steps)
        
    return (totalCost+priceNow)*valFeePercent

def getRealTotalProfit(priceNow,valFall,valFeePercent=0.000,steps=5):
    #print getRealTotalSell(priceNow,valFall)
    priceSell = getRealTotalSell(priceNow,valFall,steps+1)

    priceNowAcuum = priceNow*getAccumRateToSell(steps)
    fee = calTotalFee(priceNow,valFall,valFeePercent,steps+1)
#     print priceSell, priceNowAcuum, fee
    
    return priceSell - priceNowAcuum - fee

# for i in range(5):
#     valFeePercent = 0.001
#     printData = [[0 for _ in range(20)]for _ in range(61)]
#     fileOpen = open("asd"+str(i)+".csv",'w')
#     fileOpen.write(','+','.join([str(d) for d in range(500,10500,500)])+'\n')
#     fileOpen.close()
#     
#     for pricePeak in range(250000,280500,500):
#         y = (pricePeak-250000)/500
#         for valFall in range(500,10500,500):
#             x = (valFall-500)/500
#             priceNow = pricePeak-valFall
#             ratioDown = calRatioByFallAndNow(valFall,priceNow)
#             valExpect = getExpectationRatio(valFall)
#             printData[y][x] = getRealTotalProfit(priceNow,valFall,valFeePercent,i)
#     
#     fileOpen = open("asd"+str(i)+".csv",'a')
#     for pricePeak in range(250000,280500,500):
#         fileOpen.write(str(pricePeak)+','+','.join([str(h) for h in printData[(pricePeak-250000)/500]])+'\n')    
#     fileOpen.close()


