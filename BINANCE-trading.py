#!/usr/bin/env python3

import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from binance.client import Client
from binance.websockets import BinanceSocketManager
from twisted.internet import reactor

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
	"""Borra y reescribe completamente la tabla de simbolos en la base de datos"""
	db = sqlite3.connect(DB_NAME)
	cur = db.cursor()
	#Borra toda la tabla
	cur.execute("DELETE FROM symbols")
	db.commit()
	#Obtiene todos los simbolos del exchange e itera sobre ellos.
	for sym in client.get_exchange_info()["symbols"]:
		#Añade los simbolos a la tabla. Los dos campos rellenos con guiones son de una version previa, sin uso ahora mismo.
		cur.execute('INSERT INTO symbols VALUES("'+sym["symbol"]+'","-","-")')
		db.commit()
	db.close()
	print("Symbol Database Fully Updated")

def getSymbolList():
	"""Obtiene una lista de pares limpia de la base de datos.
	Requiere tratamiento porque la base de datos devuelve tuplas, aunque sean de un solo elemento.

	Returns:
		[List]: Lista con todos los simbolos en formato de cadenas de texto.
	"""
	db = sqlite3.connect(DB_NAME, timeout=30)
	cur = db.cursor()
	cur.execute("SELECT symbol FROM symbols")
	symList = cur.fetchall()
	db.close()
	clean = []
	#Itera sobre la lista obtenida de la base de datos y convierte las tuplas de un solo elemento en cadenas.
	for i in symList:
		clean.append(i[0])
	return clean

def getBuyablePairs():
	"""Devuelve los pares dentro del Exchange que pueden ser comprados con las monedas disponibles en el balance.
	Cuando pase a producción, sería aconsejable hardcodear los valores de las monedas que se quieren utilizar como base
	para evitar que el programa se confunda y utilice una moneda recien comprada para determinar los pares comprables.

	Returns:
		[List]: Lista de pares que se podrian comprar con las monedas disponibles.
	"""
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

def trader(sym, lim, sto):
	"""Funcion que monitoriza y actua sobre los trades. Los abre y cierra según los argumentos de entrada.
	Puede recibir los precios limite y stop tanto en cadena como en Decimal. La funcion no asume ninguna entrada
	para estos argumentos, convirtiendo siempre al correspondiente para el uso.
	Interactua con la base de datos. Recoge el par de la tabla TRADING lo escribe en TRADED cuando este termina.

	Args:
		sym (String): Par de monedas a tradear.
		lim (String|Decimal): Precio limite de venta en beneficio.
		sto (String|Decimal): Precio limite de venta en perdida.
	"""
	logName = sym+"-"+str(datetime.now().date())+"-"+str(lim)
	Log = logging.getLogger(logName)
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
	Log.info("Open: "+str(actPrice))
	Log.info("Limit: "+str(lim))
	Log.info("Stop: "+str(sto))
	nPrice = 0
	try:
		while True:
			nPrice = Decimal(client.get_symbol_ticker(symbol=sym)["price"])
			print(sym+": "+f"{nPrice:.15f}"+" | START: "+f"{actPrice:.15f}"+" | Lim/Sto: "+f"{lim:.15f}"+"/"+f"{sto:.15f}")
			if nPrice >= Decimal(lim):
				print("You win for:"+ f"{nPrice:.15f}")
				Log.info("You win for:"+ f"{nPrice:.15f}")
				break
			elif nPrice <= Decimal(sto):
				print("You lose for:"+ f"{nPrice:.15f}")
				Log.info("You lose for:"+ f"{nPrice:.15f}")
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
		Log.info("TRADE MANUALLY STOPPED")
	input("END OF TRADE")

def buyableMonitor(buyable):
	"""Es el bucle principal del programa. Itera sobre la lista de pares comprables generada por getBuyablePairs.
	Como bucle principal, actua como interfaz entre la clase AT y la base de datos.
	Cuando un par pasa el analisis de AT, se añade a la tabla TRADING de la base de datos, excluyendolo de sucesivas
	vueltas hasta que el trade termina (y es eliminado de esa tabla por la funcion trader)

	Args:
		buyable (List): Tabla de pares posibles para comprar.
	"""
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
	"""Clase de analisis tecnico. Ejecuta el analisis de los pares y, si cumplen los parametros, ejecuta la funcion Trader.
	"""
	__traderVersion__ = "0.2a"
	def _getPercentage(self, kline):
		"""[summary]

		Args:
			kline ([type]): [description]

		Returns:
			[type]: [description]
		"""
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
		"""[summary]

		Returns:
			[type]: [description]
		"""
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
		"""[summary]

		Args:
			kline ([type]): [description]
		"""
		maximum = 0
		minimum = 99999
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
		"""[summary]
		"""
		##Obtenemos las Kline de las ultimas 24 horas por seguridad. 
		dayKline = self.client.get_historical_klines(self.pair, Client.KLINE_INTERVAL_1HOUR, "1 hour ago UTC")
		MinMax = self._getMinMax(dayKline)
		self.minDay = MinMax[0]
		self.maxDay = MinMax[1]
		self.growDay = self._getPercentage(dayKline)
	def getHour(self):
		"""[summary]
		"""
		MinMax = self._getMinMax(self.hourKline)
		self.min1h = MinMax[0]
		self.max1h = MinMax[1]
		self.grow1h = self._getGrow()
	def setLimits(self):
		"""[summary]
		"""
		## 5% de perdida/beneficio fijo. Ya trabajaremos eso mejor.
		act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
		self.limitPrice = (act/100)*105
		self.stopPrice = (act/100)*95
	def startingAnalisys(self):
		"""[summary]
		"""
		count = 0
		perc = 0
		if self.grow1hTOT > self.monitorPERC:
			for m in self.grow1h[-7:]:
				perc = perc+m
				if m > 0.4:
					count = count + 1
				elif m <= 0:
					count = count - 1
			if count >= 4 and perc >= 5:
				self.monitor = True
	def __init__(self, client, pair, hourKline, monitorPERC):
		"""[summary]

		Args:
			client ([type]): [description]
			pair ([type]): [description]
			hourKline ([type]): [description]
			monitorPERC ([type]): [description]
		"""
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
		"""[summary]
		"""
		if self.monitor == True:
			logName = self.pair+"-"+str(datetime.now().date())+"-"+str(self.limitPrice)
			Log = logging.getLogger(logName)
			Log.setLevel(logging.DEBUG)
			fh = logging.FileHandler(logName+".log")
			fh.setLevel(logging.DEBUG)
			Log.addHandler(fh)
			print("-"*60)
			print(self.pair+" MONITOR")
			print(datetime.now())
			print("DAY min/max: "+ f"{self.minDay:.15f}"+" / "+f"{self.maxDay:.15f}")
			print("HOUR min/max: "+ f"{self.min1h:.15f}"+" / "+f"{self.max1h:.15f}")
			print("Day/1h grow: "+ str(self.growDay)+"% / "+str(self.grow1hTOT)+"%")
			for line in self.grow1h[-7:]:
				print("--: "+str(line)+"%")
			print("EL PAR CUALIFICA, LANZANDO TRADER")
			Log.info("-"*60)
			Log.info(AT.__traderVersion__)
			Log.info(self.pair+" MONITOR")
			Log.info(datetime.now())
			Log.info("DAY min/max: "+ f"{self.minDay:.15f}"+" / "+f"{self.maxDay:.15f}")
			Log.info("HOUR min/max: "+ f"{self.min1h:.15f}"+" / "+f"{self.max1h:.15f}")
			Log.info("Day/1h grow: "+ str(self.growDay)+"% / "+str(self.grow1hTOT)+"%")
			for line in self.grow1h[-7:]:
				Log.info("--: "+str(line)+"%")
			launch = "x-terminal-emulator -e python3 BINANCE-trading.py trader "+self.pair+" "+str(self.limitPrice)+" "+str(self.stopPrice)
			#print(launch)
			os.system(launch)

def traderCounter():
	"""[summary]
	"""
	effLog = logging.getLogger("EfectividadLog")
	effLog.setLevel(logging.DEBUG)
	fh = logging.FileHandler("Efectividad.log")
	fh.setLevel(logging.DEBUG)
	effLog.addHandler(fh)
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
	BTCEUR = Decimal(client.get_symbol_ticker(symbol="BTCEUR")["price"])*BTCprofit
	ETHEUR = Decimal(client.get_symbol_ticker(symbol="ETHEUR")["price"])*ETHprofit
	BNBEUR = Decimal(client.get_symbol_ticker(symbol="BNBEUR")["price"])*BNBprofit
	effLog.info(datetime.now())
	effLog.info("Trader Version: "+AT.__traderVersion__)
	if profit > 0:
		effLog.info("Beneficio No Cuantificable: "+str(profit))
	effLog.info("Beneficio BTC: "+str(BTCEUR)+" €")
	effLog.info("Beneficio ETH: "+str(ETHEUR)+" €")
	effLog.info("Beneficio BNB: "+str(BNBEUR)+" €")
	effLog.info("Beneficio TOTAL: "+str(BTCEUR+ETHEUR+BNBEUR)+"€")
	effLog.info("Win/Lose/TOTAL: "+str(good)+"/"+str(bad)+"/"+str(len(symList)))
	perc = round(good/len(symList)*100,3)
	effLog.info("Efectividad: "+str(perc)+ " %")
	effLog.info("-"*30)


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
	- sysInfo- Ejecuta tareas de sistema cada 24h. De momento solo ejecuta el traderCounter
	'''
	#print(sys.argv)
	try:
		if sys.argv[1] == "symbolMonitor":
			t = datetime.now()
			lap = timedelta(hours=12)
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
		elif sys.argv[1] == "trader":
			if sys.argv[2] == "test":
				pair = "BTCUSDT"
				buy = Decimal(client.get_symbol_ticker(symbol = pair)["price"])
				lim = (buy/100)*105
				sto = (buy/100)*95
				trader(pair, lim, sto)
			else:
				trader(sys.argv[2],Decimal(sys.argv[3]), Decimal(sys.argv[4]))
		elif sys.argv[1] == "sysInfo":
			t = datetime.now()
			lap = timedelta(days=1)
			try:
				traderCounter()
				print("Trader Counter Executed. Check Efectividad.log")
				dbWriteSymbols()
				while True:
					if datetime.now() >= t+lap:
						t = datetime.now()
						traderCounter()
						print("Trader Counter Executed. Check Efectividad.log")
						dbWriteSymbols()
			except KeyboardInterrupt:
				print("sysInfo Manually Stopped")
	except IndexError:
		print("Faltan argumentos para ejecutar el script.")
		traderCounter()
	except requests.exceptions.ConnectionError:
		print("Could not connect to API")
