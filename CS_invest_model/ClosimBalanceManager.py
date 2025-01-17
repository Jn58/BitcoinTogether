import copy
import sqlite3
import operator

import ClosimCalculator
import ClosimCommonMessageObjects

class ClosimBalanceManager(ClosimCalculator.ClosimCalculator):
    def __init__(self,API):
        self.nameDB = "balance.db"
        self.connectDatabase()
        
        self.dictBalanceDBIndex = {"balanceID":       0,
                                   "amountBuy":       1,
                                   "priceBuy":        2,
                                   "priceExpected":   3,
                                   "nowSteps":        4,
                                   "nextSellAmount":  5,
                                   "nextSellPrice":   6,
                                   "state":           7,
                                   "orderID":         8}

        ClosimCalculator.ClosimCalculator.__init__(self,API)

    def __del__(self):
        self.clearQuery()
        self.disconnectDatabase()
        
    def connectDatabase(self):
        import os
        existDB = os.path.isfile(self.nameDB)
        
        self.connDB = sqlite3.connect(self.nameDB)
        self.cursor = self.connDB.cursor()
        
        self.nameTable = "BITCOIN_BALANCE"
        
        if not existDB:
            self.createPriceTable(self.nameTable)
        
    def disconnectDatabase(self):
        self.connDB.commit()
        self.connDB.close()
        
    def clearQuery(self):
        self.connDB.commit()
        
    def createPriceTable(self,nameTable="BITCOIN_BALANCE"):
        #balanceID, amountBuy, priceBuy, priceExpected, nowSteps, nextSellAmount, nextSellPrice
        self.cursor.execute("CREATE TABLE " + nameTable + "(balanceID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, amountBuy float, priceBuy float, priceExpected float, nowSteps int, nextSellAmount float, nextSellPrice float, state TEXT, orderID INTEGER)")
        self.clearQuery()

    def registerBalanceByInfoBalance(self,infoBalanceBuy,isComplete=False):        
        if infoBalanceBuy.amount == 0.0:
            return True
        
        tempInfoBalance = copy.deepcopy(infoBalanceBuy)
        
        #print "registerBalanceByInfoBalance before"
        #tempInfoBalance.printBalanceInfo()
        #INSERT INTO TABLE_NAME (column1, column2, column3,...columnN) VALUES (value1, value2, value3,...valueN);        
        if isComplete:
            tempInfoBalance.nowSteps = 0
            tempInfoBalance.nextSellAmount = self.calRateSell(0)*infoBalanceBuy.amount
            tempInfoBalance.nextSellPrice = self.calPriceSell(infoBalanceBuy.priceExpected, infoBalanceBuy.price, infoBalanceBuy.nowSteps)
            tempInfoBalance.state = 'Complete'
        else:
            tempInfoBalance.amount *= (1.0-self.rateFee)            
            tempInfoBalance.nextSellAmount = tempInfoBalance.amount
        
        #print "registerBalanceByInfoBalance after"
        #tempInfoBalance.printBalanceInfo()
        self.cursor.execute("INSERT INTO " + self.nameTable + "(amountBuy, priceBuy, priceExpected, nowSteps, nextSellAmount, nextSellPrice, state) VALUES ("  + str(tempInfoBalance) + ")")
        self.clearQuery()
        
    def searchBalanceToSell(self,priceToSell):        
        #balanceID, amountBuy, priceBuy, priceExpected, nowSteps, nextSellAmount, nextSellPrice
        self.cursor.execute("SELECT * FROM " + self.nameTable + " WHERE nextSellPrice < " + str(priceToSell) + " AND state LIKE 'Complete'")
        listFetchQuery = self.cursor.fetchall()
        listFetchQuery.sort(key=operator.itemgetter(self.dictBalanceDBIndex["nextSellPrice"]))

        return self.convertListFetchToListInfoObjects(listFetchQuery)
    
    def searchBalanceToSale(self,priceToSell):        
        #balanceID, amountBuy, priceBuy, priceExpected, nowSteps, nextSellAmount, nextSellPrice
        self.cursor.execute("SELECT * FROM " + self.nameTable + " WHERE nextSellPrice > " + str(priceToSell) + " AND state LIKE 'Complete'")
        listFetchQuery = self.cursor.fetchall()
        listFetchQuery.sort(key=operator.itemgetter(self.dictBalanceDBIndex["nextSellPrice"]), reverse=True)

        return self.convertListFetchToListInfoObjects(listFetchQuery)
    
    def getBalanceInfoByID(self,balanceID):        
        self.cursor.execute("SELECT * FROM " + self.nameTable + " WHERE balanceID = " + str(balanceID))
        listFetchQuery = self.cursor.fetchall()
        
        if len(listFetchQuery) != 1:
            print "Fail to load balance from ID."
            return False
        
        infoBalance = self.generateOrderObjectFromFetchQuery(listFetchQuery[0])
        
        return infoBalance
        
    def proceedBalance(self,balanceID):
        infoQueriedBalance = self.getBalanceInfoByID(balanceID) 
                
        if infoQueriedBalance.nowSteps != 4:            
            self.processBalanceNextStep(infoQueriedBalance)
            self.updateBalanceComplete(balanceID)
        else:            
            self.destructBalance(balanceID)
        self.clearQuery()
            
    def destructBalance(self,balanceID):
        self.cursor.execute("DELETE FROM " + self.nameTable + " WHERE balanceID = " + str(balanceID))
        self.clearQuery()
        
    def processBalanceNextStep(self,tupleQueried):
#         priceNext = priceBuy+(priceExpected-priceBuy)/5.0*(nowSteps+1.0)
        priceNext = self.calPriceSell(tupleQueried.priceExpected, tupleQueried.price, tupleQueried.nowSteps+1)
        amtNext = tupleQueried.amount*self.getRateToSell(tupleQueried.nowSteps+1)
        
        sqlQuery = "UPDATE " + self.nameTable + " SET nowSteps = " + str(tupleQueried.nowSteps+1)
        sqlQuery += ", nextSellAmount = " + str(amtNext) + ", nextSellPrice = " + str(priceNext)
        sqlQuery += " WHERE balanceID = " + str(tupleQueried.balanceID)
        
        self.cursor.execute(sqlQuery)
        return False        
        
    def getNotComletedOrders(self):        
        self.cursor.execute("SELECT * FROM " + self.nameTable + " WHERE state NOT LIKE 'Complete'")
        listFetchQuery = self.cursor.fetchall()
        
        return self.convertListFetchToListInfoObjects(listFetchQuery)
    
    def getProcessBalanceInfo(self):        
        self.cursor.execute("SELECT * FROM " + self.nameTable + " WHERE state LIKE 'Process'")
        listFetchQuery = self.cursor.fetchall()
        
        return self.convertListFetchToListInfoObjects(listFetchQuery)
    
    def convertListFetchToListInfoObjects(self,listFetchQuery):        
        newList = []
        for eachQuery in listFetchQuery:
            newList.append(self.generateOrderObjectFromFetchQuery(eachQuery))
            
        return newList

    def processBuyBalance(self,balanceID,newAmount):        
        if newAmount == 0.0:            
            self.destructBalance(balanceID)
        else:
            self.updateBalanceBuyAmt(balanceID, newAmount)
        self.clearQuery()
            
    def updateBalanceBuyAmt(self,balanceID,newAmount):
        self.cursor.execute("UPDATE " + self.nameTable + " SET amountBuy = " + str(newAmount) + " WHERE balanceID = " + str(balanceID))
        self.cursor.execute("UPDATE " + self.nameTable + " SET nextSellAmount = " + str(newAmount) + " WHERE balanceID = " + str(balanceID))
        
        #print "updateBalanceBuyAmt"
        #self.getBalanceInfoByID(balanceID).printBalanceInfo()
        
        return False

    def updateBalanceSellAmt(self,balanceID,selledAmount):
        infoQueriedBalance = self.getBalanceInfoByID(balanceID)        
        newAmount = infoQueriedBalance.nextSellAmount - selledAmount
        
        #print newAmount, infoQueriedBalance.nextSellAmount, selledAmount
        if newAmount == 0.0:
            self.proceedBalance(balanceID)
        else:
            self.cursor.execute("UPDATE " + self.nameTable + " SET nextSellAmount = " + str(newAmount) + " WHERE balanceID = " + str(balanceID))
        return False
        
    def updateBalanceComplete(self,balanceID):
        self.cursor.execute("UPDATE " + self.nameTable + " SET state = 'Complete' WHERE balanceID = " + str(balanceID))        
        return False
        
    def updateBalanceStart(self,infoBalance,amountBuy):
        infoBalance.amount = amountBuy
        #print "updateBalanceStart" 
        #self.getBalanceInfoByID(infoBalance.balanceID).printBalanceInfo()
        self.updateBalanceBuyAmt(infoBalance.balanceID, amountBuy)
        #self.getBalanceInfoByID(infoBalance.balanceID).printBalanceInfo()        
        self.processBalanceNextStep(infoBalance)
        #self.getBalanceInfoByID(infoBalance.balanceID).printBalanceInfo()
        self.updateBalanceComplete(infoBalance.balanceID)
        #self.getBalanceInfoByID(infoBalance.balanceID).printBalanceInfo()
        
        return False
    
    def updateStateOrdered(self,infoOrder,balanceID):
        newState = ''
        if infoOrder.isBuy:
            newState = 'Buy'
        else:
            newState = 'Sell'
            
        strQuery = "UPDATE " + self.nameTable + " SET state = '" + newState + "', orderID = " + str(infoOrder.orderID)
        strQuery += " WHERE balanceID = " + str(balanceID)       
            
        self.cursor.execute(strQuery)
        return False
    
    def getSumOfTotalCoins(self):
        self.clearQuery()
#         SELECT column_name,column_name FROM table_name;
        self.cursor.execute("SELECT amountBuy, nowSteps, nextSellAmount FROM " + self.nameTable + " WHERE state LIKE 'Complete'")
        listFetchQuery = self.cursor.fetchall()
        
        listLeftAmount = []
        for eachTuple in listFetchQuery:
            listLeftAmount.append(self.getLeftAmountByQueries(eachTuple))
        
        return sum(listLeftAmount)
    
    def getAllOnceSellBalanceOver(self,priceNow):
        pass
        
    def getAllOnceSellBalanceLess(self,priceNow):
        priceSale = priceNow*1.05 
        
        
        self.searchBalanceToSale(priceSale)
        
        
    def getLeftAmountByQueries(self, leftQuery):
        listRate = []
        for i in range(leftQuery[1]+1,5):
            listRate.append(self.getRateToSell(i))
            
        return leftQuery[0]*sum(listRate)+leftQuery[2]
    
    def getLeftAmountByInfoBalance(self,infoBalance):
        listRate = []
        for i in range(infoBalance.nowSteps+1,5):
            listRate.append(self.getRateToSell(i))
            
        return infoBalance.amount*sum(listRate)+infoBalance.nextSellAmount    
 
    def generateInfoBalanceByVariables(self,amount,price,priceExpected):
        listData = []
        listData.append(amount)          #listData[0]
        listData.append(price)           #listData[1]
        listData.append(priceExpected)   #listData[2]
        listData.append(-1)
        listData.append(amount)
#         listData.append(self.calRateSell(0)*listData[0])
        listData.append(self.calPriceSell(priceExpected, price, 0))
        
        infoBalance = ClosimCommonMessageObjects.InfoBalance()
        infoBalance.initByList(listData)
        
        return infoBalance
 
    def generateInfoBalanceByQuery(self,queryOrder):
        #amountBuy, priceBuy, priceExpected, nowSteps, nextSellAmount, nextSellPrice        
        listData = []
        listData.append(queryOrder.amount)          #listData[0]
        listData.append(queryOrder.price)           #listData[1]
        listData.append(queryOrder.priceExpected)   #listData[2]
        listData.append(-1)
        listData.append(queryOrder.amount)
#         listData.append(self.calRateSell(0)*listData[0])
        listData.append(self.calPriceSell(queryOrder.priceExpected, queryOrder.price, 0))
        
        infoBalance = ClosimCommonMessageObjects.InfoBalance()
        infoBalance.initByList(listData)
        
        return infoBalance
    
    def generateOrderObjectFromFetchQuery(self,fetchQuery):
        #amount, price, priceExpected, nowSteps, nextSellAmount, nextSellPrice, balanceID, state
        listData = [fetchQuery[self.dictBalanceDBIndex["amountBuy"]]]
        listData.append(fetchQuery[self.dictBalanceDBIndex["priceBuy"]])
        listData.append(fetchQuery[self.dictBalanceDBIndex["priceExpected"]])        
        listData.append(fetchQuery[self.dictBalanceDBIndex["nowSteps"]])        
        listData.append(fetchQuery[self.dictBalanceDBIndex["nextSellAmount"]])
        listData.append(fetchQuery[self.dictBalanceDBIndex["nextSellPrice"]])
        
        listData.append(fetchQuery[self.dictBalanceDBIndex["balanceID"]])
        listData.append(fetchQuery[self.dictBalanceDBIndex["state"]])
        listData.append(fetchQuery[self.dictBalanceDBIndex["orderID"]])
           
        infoOrder = ClosimCommonMessageObjects.InfoBalance()
        infoOrder.initByList(listData)
        
        return infoOrder
            
# import DummyAPI
#           
# dumAPI = DummyAPI.DummyAPI()
# clobalman = ClosimBalanceManager(dumAPI)
#   
# listQuery = clobalman.searchBalanceToSell(268000)
# for eQ in listQuery:
#     eQ.printBalanceInfo()
# 
# clobalman.proceedBalance(3)

