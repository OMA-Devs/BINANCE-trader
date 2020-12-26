#!/usr/bin/env python3

import os
import requests
from binance.client import Client
from binance.websockets import BinanceSocketManager
from twisted.internet import reactor
from datetime import datetime, timedelta
import sqlite3
import time
import sys
from decimal import Decimal


TEST_FLAG = False

api_key = os.environ.get("TEST_BINANCE_API")
api_sec = os.environ.get("TEST_BINANCE_SEC")
real_api_key = os.environ.get("BINANCE_API_KEY")
real_api_sec = os.environ.get("BINANCE_API_SEC")

if TEST_FLAG == False:
	client = Client(real_api_key,real_api_sec)
	DB_NAME = "binance.db"
else:
	client = Client(api_key,api_sec)
	client.API_URL = 'https://testnet.binance.vision/api'
	DB_NAME = "binanceTEST.db"

def dbWriteSymbols():
	'''Borra y reescribe completamente la tabla de simbolos en la base de datos'''
	db = sqlite3.connect(DB_NAME)
	cur = db.cursor()
	cur.execute("DELETE FROM symbols")
	db.commit()
	for sym in client.get_exchange_info()["symbols"]:
		cur.execute('INSERT INTO symbols VALUES("'+sym["symbol"]+'","-","-")')
		db.commit()
	db.close()
	print("Symbol Database Fully Updated")

def getSymbolTicker(sym):
	db = sqlite3.connect(DB_NAME, timeout=30)
	cur = db.cursor()
	t = str(int(time.time()))
	price = client.get_symbol_ticker(symbol=sym)
	#print(sym+" | "+price["price"]+" | "+str(datetime.utcfromtimestamp(int(t))))
	try:
		cur.execute("DELETE FROM symbols WHERE symbol = '"+sym+"'")
		db.commit()
		cur.execute('INSERT INTO symbols VALUES("'+sym+'","'+price["price"]+'","'+t+'")')
		db.commit()
		cur.execute("CREATE TABLE IF NOT EXISTS "+sym+"price"+" (timestamp text, price text)")
		db.commit()
		cur.execute('INSERT INTO '+sym+'price'+' VALUES("'+t+'","'+price["price"]+'")')
		db.commit()
	except sqlite3.OperationalError:
		print("Database Locked. Skipping DB log")
	except requests.exceptions.ReadTimeout:
		print("HTTP Read TimeOut. Skipping DB log")
	db.close()
	#print(sym+" Updated in Database")
	return price

def getSymbolList():
	db = sqlite3.connect(DB_NAME, timeout=30)
	cur = db.cursor()
	cur.execute("SELECT symbol FROM symbols")
	symList = cur.fetchall()
	db.close()
	clean = []
	for i in symList:
		clean.append(i[0])
	return clean

def getRelevantPairs():
	'''EN PROGRESO. DEVUELVE LOS PARES RELACIONADOS COMPLETAMENTE CON LAS MONEDAS EN POSESION. ESTO PERMITE COMPRAS Y VENTAS SIN PROBLEMAS.
	¿QUE FALTA?
	- PUEDE INTERESAR VENDER UNA MONEDA QUE SE TIENE A UNA QUE NO SE POSEE. ESTA LISTA NO CONTEMPLARIA ESA POSIBILIDAD.
	- PUEDE INTERESAR COMPRAR DESDE UNA MONEDA QUE NO SE POSEE. HABRIA QUE CONTEMPLAR ESA OPCION, PERO ES UN CAMINO MAS COMPLEJO.'''
	symList = getSymbolList()
	relevant = []
	assets = []
	for bal in client.get_account()["balances"]:
		if Decimal(bal['free']) > 0:
			assets.append(bal["asset"])
	for sym in symList:
		for ass in assets: #AHAHAHAHAHAH
			if ass in sym[0:len(ass)]:
				if sym[len(ass):] in assets:
					relevant.append(sym)
	#print("Relevant Pairs: "+str(len(relevant)))
	#print(relevant)
	return relevant

def getBuyablePairs():
	symList = getSymbolList()
	buyable = []
	assets = []
	for bal in client.get_account()["balances"]:
		if Decimal(bal['free']) > 0:
			assets.append(bal["asset"])
	for sym in symList:
		for ass in assets:
			Lass = len(ass)
			#Busca los pares cuyo asset secundario es el poseido. Eso significa que podemos comprar desde esa moneda.
			if sym[Lass-Lass*2:] == ass:
				buyable.append(sym)
	#print(len(buyable))
	return buyable

def getFULLHistoricPair(symbol):
	print("Requesting "+symbol+" Full Historic")
	timestamp = client._get_earliest_valid_timestamp(symbol, '1d')
	#print(type(timestamp))
	#dt = datetime.utcfromtimestamp(timestamp/1000)
	#print(dt)
	db = sqlite3.connect(DB_NAME)
	cur = db.cursor()
	cur.execute("CREATE TABLE IF NOT EXISTS "+symbol+" (timestamp text, open text, high text, low text, close text, volume text)")
	db.commit()
	cur.execute("DELETE FROM "+symbol)
	#commit the changes to db
	db.commit()
	#close the connection
	bars = client.get_historical_klines(symbol, '30m', timestamp, limit=1000)
	#print(len(bars))
	#print(bars[0])
	for i in bars:
		cur.execute('INSERT INTO '+symbol+' VALUES("'+str(i[0])+'","'+i[1]+'","'+i[2]+'","'+i[3]+'","'+i[4]+'","'+i[5]+'")')
		db.commit()
		#print(datetime.utcfromtimestamp(i[0]/1000))
	db.close()


def trader(sym, lim, sto):
	db = sqlite3.connect(DB_NAME, timeout=30)
	cur = db.cursor()
	kline = client.get_historical_klines(sym, Client.KLINE_INTERVAL_1MINUTE, "1 hour ago UTC")
	#perc = getPercentage(kline)
	LastPrice = Decimal(kline[-1][4])
	print("Last Price at: "+ str(LastPrice))
	actPrice = Decimal(client.get_symbol_ticker(symbol= sym)["price"])
	print("You buy at: "+str(actPrice))
	print("You want to sell at: "+str(lim))
	print("StopLoss at: "+str(sto))
	nPrice = 0
	try:
		while True:
			nPrice = Decimal(client.get_symbol_ticker(symbol=sym)["price"])
			print(sym+": "+str(nPrice)+" | START: "+str(actPrice)+" | Lim/Sto: "+str(lim)+"/"+str(sto))
			if nPrice >= Decimal(lim):
				print("You win for:"+ str(nPrice))
				break
			elif nPrice <= Decimal(sto):
				print("You lose for: "+str(nPrice))
				break
			time.sleep(5)
		cur.execute("DELETE FROM trading WHERE symbol = '"+sym+"'")
		db.commit()
		cur.execute("INSERT INTO traded VALUES('"+sym+"','"+str(actPrice)+"','"+str(nPrice)+"')")
		db.commit()
		db.close()
	except KeyboardInterrupt:
		cur.execute("DELETE FROM trading WHERE symbol = '"+sym+"'")
		db.commit()
		db.close()
		print("Trade Manually Stopped")
		print("THIS IS TESTING. REMEMBER TO CANCEL YOUR ORDER")
	input("END OF TRADE") 

def buyableMonitor(buyable):
	db = sqlite3.connect(DB_NAME, timeout=30)
	cur = db.cursor()
	cur.execute("SELECT symbol FROM trading")
	symList= cur.fetchall()
	monitored = []
	for i in symList:
		monitored.append(i[0])
	print("Comenzando Comprobacion- "+str(datetime.utcnow()))
	print("Pares en TRADING: "+ str(monitored))
	for b in buyable:
		#print("Checking: "+b)
		if b in monitored:
			pass
		else:
			kline = client.get_historical_klines(b, Client.KLINE_INTERVAL_1MINUTE, "1 hour ago UTC")
			sym = AT(client, b, kline, int(sys.argv[2]))
			sym.display()
			if sym.monitor == True:
				cur.execute("INSERT INTO trading VALUES('"+b+"')")
				db.commit()
	db.close()

class AT:
	def _getPercentage(self, kline):
		##Obtenemos el crecimiento completo en un Kline dado.
		## NO FUNCIONA CON LINES DE KLINES, ya que busca apertura del primer kline y cierre del ultimo.
		if len(kline) > 0:
			op = Decimal(kline[0][1])
			cl = Decimal(kline[-1][4])
			perc = round((cl-op)/op*100,3)
			return perc
		else:
			return 0
	def _getGrow(self):
		##Obtiene el crecimiento de cada line en el Kline de 1 hora.
		growARR = []
		if len(self.hourKline) > 0:
			for line in self.hourKline:
				op = Decimal(line[1])
				cl = Decimal(line[4])
				perc = round((cl-op)/op*100,3)
				growARR.append(perc)
		return growARR
	def _getMinMax(self, kline):
		maximum = 0
		minimum = 0
		if len(kline) > 0:
			#Determinamos el minimo y el maximo de un kline dado mirando aperturas y cierres.
			for line in kline:
				##Maximo
				if Decimal(line[1]) > maximum:
					maximum = Decimal(line[1])
				elif Decimal(line[4]) > maximum:
					maximum = Decimal(line[4])
				#Minimo
				if Decimal(line[1]) < minimum:
					minimum = Decimal(line[1])
				elif Decimal(line[4]) < minimum:
					minimum = Decimal(line[4])
		return[minimum,maximum]
	def getDay(self):
		##Obtenemos las Kline de las ultimas 24 horas por seguridad. 
		dayKline = self.client.get_historical_klines(self.pair, Client.KLINE_INTERVAL_1HOUR, "1 hour ago UTC")
		MinMax = self._getMinMax(dayKline)
		self.minDay = MinMax[0]
		self.maxDay = MinMax[1]
		self.growDay = self._getPercentage(dayKline)
	def getHour(self):
		MinMax = self._getMinMax(self.hourKline)
		self.min1h = MinMax[0]
		self.max1h = MinMax[1]
		self.grow1h = self._getGrow()
	def setLimits(self):
		## 5% de perdida/beneficio fijo. Ya trabajaremos eso mejor.
		act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
		self.limitPrice = (act/100)*105
		self.stopPrice = (act/100)*95
	def startingAnalisys(self):
		count = 0
		perc = 0
		if self.grow1hTOT > self.monitorPERC:
			for m in self.grow1h[-7:]:
				perc = perc+m
				if m > 0.4:
					count = count + 1
			if count >= 4 and perc >= 5:
				#price = self.client.get_symbol_ticker(symbol=self.pair)["price"]
				#if price <= self.maxDay and price <= self.max1h:
				self.monitor = True
	def __init__(self, client, pair, hourKline, monitorPERC):
		self.client = client
		self.pair = pair
		self.hourKline = hourKline #kline de la ultima hora, minuto a minuto.
		self.minDay = 0 #Precio minimo del dia
		self.maxDay = 0 #Precio maximo del dia
		self.min1h = 0 #Precio minimo 1h
		self.max1h = 0 #Precio maximo 1h
		self.growDay = 0 #Crecimiento (en porcentaje) del día
		self.grow1hTOT = self._getPercentage(hourKline) #Crecimiento (en porcentaje) de una hora en total
		self.grow1h = [] #Crecimiento (en porcentaje) de la ultima hora, minuto a minuto.
		self.monitorPERC = monitorPERC #Porcentaje en el que si inician las operaciones y el monitoreo
		self.monitor = False
		self.limitPrice = 0 # Precio maximo para salir de la posicion.
		self.stopPrice = 0 # Precio minimo para vender.
		self.getHour()
		self.startingAnalisys()
		if self.monitor == True:
			self.getDay()
			self.setLimits()
	def display(self):
		if self.monitor == True:
			print("-"*60)
			print(self.pair+" MONITOR")
			print(datetime.utcnow())
			print("DAY min/max: "+ f"{self.minDay:.10f}"+" / "+f"{self.maxDay:.10f}")
			print("HOUR min/max: "+ f"{self.min1h:.10f}"+" / "+f"{self.max1h:.10f}")
			print("Day/1h grow: "+ str(self.growDay)+"% / "+str(self.grow1hTOT)+"%")
			for line in self.grow1h[-7:]:
				print("--: "+str(line)+"%")
			print("EL PAR CUALIFICA, LANZANDO TRADER")
			launch = "x-terminal-emulator -e python3 BINANCE-trading.py trader "+self.pair+" "+str(self.limitPrice)+" "+str(self.stopPrice)
			#print(launch)
			os.system(launch)

def traderCounter():
	db = sqlite3.connect(DB_NAME, timeout=30)
	cur = db.cursor()
	cur.execute("SELECT * FROM traded")
	symList= cur.fetchall()
	BTCprofit = 0
	ETHprofit = 0
	BNBprofit = 0
	profit = 0
	good = 0
	bad = 0
	for i in symList:
		op = Decimal(i[2])-Decimal(i[1])
		if "BTC" in i[0]:
			BTCprofit = BTCprofit + op
		elif "ETH" in i[0]:
			ETHprofit = ETHprofit + op
		elif "BNB" in i[0]:
			BNBprofit = BNBprofit + op
		else:
			profit = op + profit
		if op >= 0:
			good = good + 1
		else:
			bad  = bad + 1
	db.close()
	print("Fecha de comienzo: 24/12")
	BTCEUR = Decimal(client.get_symbol_ticker(symbol="BTCEUR")["price"])*BTCprofit
	ETHEUR = Decimal(client.get_symbol_ticker(symbol="ETHEUR")["price"])*ETHprofit
	BNBEUR = Decimal(client.get_symbol_ticker(symbol="BNBEUR")["price"])*BNBprofit
	if profit > 0:
		print("Beneficio No Cuantificable: "+str(profit))
	print("Beneficio BTC: "+str(BTCEUR)+" €")
	print("Beneficio ETH: "+str(ETHEUR)+" €")
	print("Beneficio BNB: "+str(BNBEUR)+" €")
	print("Beneficio TOTAL: "+str(BTCEUR+ETHEUR+BNBEUR)+"€")
	print("Win/Lose/TOTAL: "+str(good)+"/"+str(bad)+"/"+str(len(symList)))
	perc = round(good/len(symList)*100,3)
	print("Efectividad: "+str(perc)+ " %")


if __name__ == "__main__":
	'''
	argv[1]
	- symbolMonitor- Ejecuta el monitoreo de pares para comprobar nuevos pares o retirados. Deberia ejecutarse cada 1h como maximo.
	- relevantMonitor- Ejecuta un monitoreo de los precios de pares relevantes. Se ejecutara cada 30s
	- buyableMonitor- Busca los pares comprables con crecidas sensibles y ejecuta fnciones de seguimiento sobre ellos.
		-argv[2] porcentaje que activa el seguimiento. Recordar convertirlo a INT
	- trader- Ejecuta el bot trader
		-argv[2] par
		-argv[3] precio limite. CONVERTIR A STR
		-argv[4] precio stop. CONVERTIR A STR
	'''
	#print(sys.argv)
	try:
		if sys.argv[1] == "symbolMonitor":
			t = datetime.now()
			lap = timedelta(hours=1)
			dbWriteSymbols()
			try:
				while True:
					if datetime.now() >= t+lap :
						t = datetime.now()
						dbWriteSymbols()
					else:
						pass
			except KeyboardInterrupt:
				print("Symbol Monitor Manually Stopped")
		elif sys.argv[1] == "relevantMonitor": #POSIBLEMENTE INUTIL
			t = datetime.now()
			lap = timedelta(seconds=30)
			relevant = getRelevantPairs()
			for r in relevant:
				getSymbolTicker(r)
			print("-"*60)
			try:
				while True:
					if datetime.now() >= t+lap:
						t = datetime.now()
						relevant = getRelevantPairs()
						for r in relevant:
							getSymbolTicker(r)
						print("-"*60)
			except KeyboardInterrupt:
				print("Relevant Monitor Manually Stopped")
		elif sys.argv[1] == "buyableMonitor": ##UTILIZABLE 
			t = datetime.now()
			lap = timedelta(minutes=5)
			buyable = getBuyablePairs()
			try:
				buyableMonitor(buyable)
				while True:
					if datetime.now() >= t+lap:
						t = datetime.now()
						buyableMonitor(buyable)
			except KeyboardInterrupt:
				print("Monitor Manually Stopped")
		elif sys.argv[1] == "relevantFULLdata": #WHY NOT
			relevant = getRelevantPairs()
			for r in relevant:
				getFULLHistoricPair(r)
			print("Task Done")
		elif sys.argv[1] == "trader":
			trader(sys.argv[2],sys.argv[3], sys.argv[4])
	except IndexError:
		print("Faltan argumentos para ejecutar el script.")
		traderCounter()
	except requests.exceptions.ConnectionError:
		print("Could not connect to API")
