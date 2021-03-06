#!/usr/bin/env python3

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

from dbOPS import DB
from algo import ALGO

TEST_FLAG = False

api_key = os.environ.get("TEST_BINANCE_API")
api_sec = os.environ.get("TEST_BINANCE_SEC")
real_api_key = os.environ.get("BINANCE_API_KEY")
real_api_sec = os.environ.get("BINANCE_API_SEC")
db = None

if TEST_FLAG == False:
	client = Client(real_api_key,real_api_sec)
	db = DB("binance.db", client)
else:
	client = Client(api_key,api_sec)
	client.API_URL = 'https://testnet.binance.vision/api'
	db = DB("binanceTEST.db", client)


def getBuyablePairs():
	"""Devuelve los pares dentro del Exchange que pueden ser comprados con las monedas disponibles en el balance.
	Cuando pase a producción, sería aconsejable hardcodear los valores de las monedas que se quieren utilizar como base
	para evitar que el programa se confunda y utilice una moneda recien comprada para determinar los pares comprables.

	Returns:
		[List]: Lista de pares que se podrian comprar con las monedas disponibles.
	"""
	symList = db.getSymbols()
	buyable = []
	assets = ["BTC","BNB","ETH"] ##Monedas HARDCODED.
	'''assets = []
	for bal in client.get_account()["balances"]:
		if Decimal(bal['free']) > 0:
			assets.append(bal["asset"])'''
	for sym in symList:
		for ass in assets:
			Lass = len(ass)
			#Busca los pares cuyo asset secundario es el poseido. Eso significa que podemos comprar desde esa moneda.
			if sym[Lass-Lass*2:] == ass:
				buyable.append(sym)
	#print(len(buyable))
	return buyable

def trader(sym, lim, sto, v):
	"""Funcion que monitoriza y actua sobre los trades. Los abre y cierra según los argumentos de entrada.
	Puede recibir los PORCENTAJES limite y stop tanto en cadena como en Decimal, pero habitualmente los recibira en
	cadena por linea de comandos. La funcion no asume ninguna entrada	para estos argumentos, convirtiendo siempre al correspondiente para el uso.
	Interactua con la base de datos. Recoge el par de la tabla TRADING lo escribe en TRADED cuando este termina.

	Args:
		sym (String): Par de monedas a tradear.
		lim (String|Decimal): Porcentaje limite de venta en beneficio.
		sto (String|Decimal): Porcentaje limite de venta en perdida.
		v (Integer) : Version del algoritmo que activa el trader
	"""
	logName = sym+"-"+str(datetime.now().date())+"-"+str(v)
	actPrice = Decimal(client.get_symbol_ticker(symbol= sym)["price"])
	limPrice = (actPrice/100)*int(lim)
	stoPrice = (actPrice/100)*int(sto)
	mesARR = ["You buy at: "+str(actPrice),
			"Limit at: "+str(lim)+"%: "+f"{limPrice:.15f}",
			"StopLoss at: "+str(sto)+"%: "+f"{stoPrice:.15f}"]
	nPrice = 0
	db.tradeSTART(v,sym,datetime.timestamp(datetime.now()))
	try:
		while True:
			nPrice = Decimal(client.get_symbol_ticker(symbol=sym)["price"])
			print(sym+": "+f"{nPrice:.15f}"+" | START: "+f"{actPrice:.15f}"+" | Lim/Sto: "+f"{limPrice:.15f}"+"/"+f"{stoPrice:.15f}")
			if nPrice >= limPrice:
				mesARR.append("You win for:"+ f"{nPrice:.15f}")
				break
			elif nPrice <= stoPrice:
				mesARR.append("You lose for:"+ f"{nPrice:.15f}")
				break
			time.sleep(5)
		db.tradeEND(v,sym,actPrice,nPrice,datetime.timestamp(datetime.now()))
		logger(logName, mesARR)
	except KeyboardInterrupt:
		db.removeTrade(v,sym)
		print("Trade Manually Stopped")
		print("THIS IS TESTING. REMEMBER TO CANCEL YOUR ORDER.")
		mesARR.append("TRADE MANUALLY STOPPED")
		logger(logName, mesARR)
	#input("END OF TRADE")

def buyableMonitor(buyable):
	"""Es el bucle principal del programa. Itera sobre la lista de pares comprables generada por getBuyablePairs.
	Como bucle principal, actua como interfaz entre la clase AT y la base de datos.
	Cuando un par pasa el analisis de AT, se añade a la tabla TRADING de la base de datos, excluyendolo de sucesivas
	vueltas hasta que el trade termina (y es eliminado de esa tabla por la funcion trader)

	Args:
		buyable (List): Tabla de pares posibles para comprar.
	"""
	print("Comenzando Comprobacion - "+str(datetime.utcnow()))
	if sys.argv[2] == "TEST":
		for b in buyable:
			kline = client.get_historical_klines(b, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
			#print(kline)
			for i in ALGO.__versions__:
				at = AT(client,b, kline, i)
				at.display()
	else:
		for b in buyable:
			kline = client.get_historical_klines(b, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
			at = AT(client,b, kline, sys.argv[2])
			at.display()


class AT:
	"""Clase de analisis tecnico. Ejecuta la clasificacion de los datos y luego el algoritmo de cualificacion
	y, si cumplen los parametros, ejecuta la funcion Trader en un proceso externo.
	"""
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
		if len(self.dayKline) > 0:
			for line in self.dayKline[-60:]:
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
				if Decimal(line[2]) > maximum:
					maximum = Decimal(line[2])
				#Minimo
				if Decimal(line[3]) < minimum:
					minimum = Decimal(line[3])
		return[minimum,maximum]
	def _getMedium(self,kline):
		nums = []
		med = 0
		if len(kline) > 0:
			for line in kline:
				minimum = Decimal(line[3])
				maximum = Decimal(line[4])
				num = (minimum+maximum)/2
				nums.append(num)
		for num in nums:
			med = med + num
		med = med/len(nums)
		return med
	def getDay(self):
		"""[summary]
		"""
		##Obtenemos las Kline de las ultimas 24 horas por seguridad. 
		#dayKline = self.client.get_historical_klines(self.pair, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
		MinMax = self._getMinMax(self.dayKline)
		self.minDay = MinMax[0]
		self.maxDay = MinMax[1]
		self.medDay = self._getMedium(self.dayKline)
		self.growDay = self._getPercentage(self.dayKline)
	def getHour(self):
		"""[summary]
		"""
		MinMax = self._getMinMax(self.dayKline[-60:])
		self.min1h = MinMax[0]
		self.max1h = MinMax[1]
		self.med1h = self._getMedium(self.dayKline[-60:])
		self.grow1h = self._getGrow()
	def setLimits(self):
		"""Marca los porcentajes de limite y stop para pasarlos al Trader. El porcentaje marcado
		depende de la maxima y minima diaria. Intentará marcar un 5-10% de limite y un 5-8% de perdida
		teniendo en cuenta esos parametros.

		Si la funcion no puede determinar porcentajes beneficio/perdida, hace fallback a un 5-5% de limite/stop
		"""
		act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
		for i in range(105,111):
		#Comprueba si puede generar un beneficio superior al 5%
			if (act/100)*i < self.maxDay and act <= (self.medDay/100)*105:
				self.limitPrice = i
		#if self.limitPrice == 0:
		#	self.limitPrice = 105
		########################################################
		'''for i in range(92, 96):
		#Comprueba si puede marcar un stop menor al 8%
			if (act/100)*i > self.min1h:
				self.stopPrice = i'''
		if self.stopPrice == 0:
			self.stopPrice = 95
	def startingAnalisys(self):
		"""[summary]
		"""
		self.monitor = ALGO(self, self.version).analisis()
		if self.monitor == True:
			'''act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
			mesARR = ["-"*60,
					self.pair+" PRE MONITOR v"+str(self.version),
					str(datetime.now()),
					"DAY min/med/max: "+ f"{self.minDay:.15f}"+" / "+f"{self.medDay:.15f}"+" / "+f"{self.maxDay:.15f}",
					"HOUR min/med/max: "+ f"{self.min1h:.15f}"+" / "+f"{self.med1h:.15f}"+" / "+f"{self.max1h:.15f}",
					"Day/1h grow: "+ str(self.growDay)+"% / "+str(self.grow1hTOT)+"%",
					"Price: "+f"{act:.15f}",
					"Limit: "+str(self.limitPrice)+"%: "+f"{(act/100)*self.limitPrice:.15f}",
					"Stop: "+str(self.stopPrice)+"%: "+f"{(act/100)*self.stopPrice:.15f}"
					]
			for mes in mesARR:
				print(mes)'''
			##Esto significa que en la funcion setLimits el limite se ha detectado como superior al precio medio.
			##En este caso se cancela el monitoreo.
			if self.limitPrice == 0:
				self.monitor = False
		#print(self.monitor)
	def __init__(self, client, pair, dayKline, version):
		"""[summary]

		Args:
			client ([type]): [description]
			pair ([type]): [description]
			monitorPERC ([type]): [description]
		"""
		if db.getTRADINGsingle(version,pair) == False and len(dayKline) > 0:
			#print("NOT IN TRADING")
			self.client = client
			self.pair = pair
			self.dayKline = dayKline #kline de la ultima hora, minuto a minuto.
			self.minDay = 0 #Precio minimo del dia
			self.maxDay = 0 #Precio maximo del dia
			self.medDay = 0 #Precio medio del dia
			self.min1h = 0 #Precio minimo 1h
			self.max1h = 0 #Precio maximo 1h
			self.med1h = 0 #Precio medio 1h
			self.growDay = 0 #Crecimiento (en porcentaje) del día
			self.grow1hTOT = self._getPercentage(self.dayKline[-60:]) #Crecimiento (en porcentaje) de una hora en total
			self.grow1h = [] #Crecimiento (en porcentaje) de la ultima hora, minuto a minuto.
			self.monitorPERC = 1 #Porcentaje en el que si inician las operaciones y el monitoreo
			self.monitor = False
			self.limitPrice = 0 # Precio maximo para salir de la posicion.
			self.stopPrice = 0 # Precio minimo para vender.
			self.version = version
			#self.algo = ALGO(self, self.version)
			self.getHour()
			self.getDay()
			self.setLimits()
			self.startingAnalisys()
		else:
			self.monitor = False
	def display(self):
		"""[summary]
		"""
		if self.monitor == True:
			logName = self.pair+"-"+str(datetime.now().date())+"-"+str(self.version)
			mesARR = ["-"*60,
					self.pair+" MONITOR v"+str(self.version),
					str(datetime.now()),
					"DAY min/med/max: "+ f"{self.minDay:.15f}"+" / "+f"{self.medDay:.15f}"+" / "+f"{self.maxDay:.15f}",
					"HOUR min/med/max: "+ f"{self.min1h:.15f}"+" / "+f"{self.med1h:.15f}"+" / "+f"{self.max1h:.15f}",
					"Day/1h grow: "+ str(self.growDay)+"% / "+str(self.grow1hTOT)+"%"]
			for line in self.grow1h[-3:]:
				mesARR.append("--: "+str(line)+"%")
			logger(logName,mesARR)
			launch = "x-terminal-emulator -e python3 "+sys.argv[0]+" trader "+self.pair+" "+str(self.limitPrice)+" "+str(self.stopPrice)+" "+str(self.version)
			#print(launch)
			os.system(launch)

def traderCounter(v):
	"""[summary]

	Args:
		v ([type]): [description]
	"""
	logName = "Efectividad"
	symList = db.getTRADED(v)
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
	BTCEUR = Decimal(client.get_symbol_ticker(symbol="BTCEUR")["price"])*BTCprofit
	ETHEUR = Decimal(client.get_symbol_ticker(symbol="ETHEUR")["price"])*ETHprofit
	BNBEUR = Decimal(client.get_symbol_ticker(symbol="BNBEUR")["price"])*BNBprofit
	perc = round(good/len(symList)*100,3)
	mesARR = [str(datetime.now()),
			"Trader Version: "+str(v),
			"Beneficio BTC: "+str(BTCEUR)+" €",
			"Beneficio ETH: "+str(ETHEUR)+" €",
			"Beneficio BNB: "+str(BNBEUR)+" €",
			"Beneficio TOTAL: "+str(BTCEUR+ETHEUR+BNBEUR)+"€",
			"Win/Lose/TOTAL: "+str(good)+"/"+str(bad)+"/"+str(len(symList)),
			"Efectividad: "+str(perc)+ " %"]
	if profit > 0:
		mesARR.append("Beneficio No Cuantificable: "+str(profit))
	mesARR.append("-"*30)
	logger(logName, mesARR)

def logger(logName, mesARR):
	f = open("logs/"+logName+".log", "a+")
	for line in mesARR:
		f.write(line+"\n")
		print(line)
	f.close()

if __name__ == "__main__":
	'''
	argv[1]
	- symbolMonitor- Ejecuta el monitoreo de pares para comprobar nuevos pares o retirados. Deberia ejecutarse cada 1h como maximo.
	- relevantMonitor- Ejecuta un monitoreo de los precios de pares relevantes. Se ejecutara cada 30s
	- buyMonitor- Busca los pares comprables con crecidas sensibles y ejecuta fnciones de seguimiento sobre ellos.
		-argv[2] version de algoritmo
	- trader- Ejecuta el bot trader
		-argv[2] par
		-argv[3] porcentaje limite. CONVERTIR A INT
		-argv[4] porcentaje stop. CONVERTIR A INT
		-argv[5] version del algoritmo
 	- counter- Ejecuta el control de efectividad de las versiones de algoritmo.
	 	-argv[2] version del algoritmo o FULL. Si esta ausente, se efectuará el control de la ultima version implementada
	'''
	#print(sys.argv)
	if sys.argv[1] == "symbolMonitor":
		t = datetime.now()
		lap = timedelta(hours=12)
		db.updateSymbols()
		'''try:
			while True:
				if datetime.now() >= t+lap :
					t = datetime.now()
					db.updateSymbols()
				else:
					pass
		except KeyboardInterrupt:
			print("Symbol Monitor Manually Stopped")'''
	elif sys.argv[1] == "buyMonitor": ##UTILIZABLE
		t = datetime.now()
		lap = timedelta(minutes=5)
		buyable = getBuyablePairs()
		buyableMonitor(buyable)
		while True:
			try:
				if datetime.now() >= t+lap:
					t = datetime.now()
					buyableMonitor(buyable)
			except requests.exceptions.Timeout:
				print("Could not connect to API")
				pass
	elif sys.argv[1] == "trader":
		if sys.argv[2] == "test":
			pair = "BTCUSDT"
			buy = Decimal(client.get_symbol_ticker(symbol = pair)["price"])
			lim = 105
			sto = 95
			trader(pair, lim, sto, ALGO.__versions__[-1])
		else:
			trader(sys.argv[2],int(sys.argv[3]), int(sys.argv[4]),sys.argv[5])
	elif sys.argv[1] == "counter":
		try:
			if sys.argv[2] == "FULL":
				for i in ALGO.__versions__:
					traderCounter(i)
			else:
				traderCounter(sys.argv[2])
		except IndexError:
			traderCounter(ALGO.__versions__[-1])
