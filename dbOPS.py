#!/usr/bin/env python3

import sqlite3
from binance.client import Client

class DB:
	"""Clase que engloba todas las operaciones de base de datos. Se ha hecho necesaria ya que la modularización del programa está causando
	que haya muchas llamadas desperdigadas por las funciones y mucho codigo duplicado (apertura, commit, cierre) en cada una de ellas.
	"""
	def __init__(self, name, client):
		"""Inicializacion de la clase. Sencilla, simplificada. Solo requiere un nombre de base de datos y una instancia de cliente
		de BINANCE para funcionar.

		Args:
			name (String): Nombre de la base de datos. Existe el argumento debido a que pueden utilizarse dos bases de datos. La de prueba
			y la de produccion. Las API de binance de prueba y produccion son diferentes.
			client (binance.Client): Instancia de cliente de binance, utilizado para obtener informacion del exchange y poco más. 
		"""
		self.name = name
		self.client = client
	def updateSymbols(self):
		"""Borra y reescribe completamente la tabla de simbolos en la base de datos
		"""
		old = self.getSymbols() #Lista actual de simbolos
		diff = [] #Lista diferencial de simbolos
		db = sqlite3.connect(self.name)
		cur = db.cursor()
		#Borra toda la tabla
		cur.execute("DELETE FROM symbols")
		db.commit()
		#Obtiene todos los simbolos del exchange e itera sobre ellos.
		for sym in self.client.get_exchange_info()["symbols"]:
			#Añade los simbolos a la tabla. Los dos campos rellenos con guiones son de una version previa, sin uso ahora mismo.
			cur.execute('INSERT INTO symbols VALUES("'+sym["symbol"]+'","-","-")')
			db.commit()
			if sym["symbol"] in old:
				pass
			else:
				diff.append(sym["symbol"])
		db.close()
		print("Symbol Database Fully Updated")
		print("- DIFF: "+str(diff))
	def getSymbols(self):
		"""Obtiene una lista de pares limpia de la base de datos.
		Requiere tratamiento porque la base de datos devuelve tuplas, aunque sean de un solo elemento.

		Returns:
			[List]: Lista con todos los simbolos en formato de cadenas de texto.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT symbol FROM symbols")
		symList = cur.fetchall()
		db.close()
		clean = []
		#Itera sobre la lista obtenida de la base de datos y convierte las tuplas de un solo elemento en cadenas.
		for i in symList:
			clean.append(i[0])
		return clean
	def getTRADING(self, version):
		"""Obtiene los simbolos en trading activo de la version del algoritmo proporcionada.

		Args:
			version (String|Integer): Numero de la version del algoritmo de trading.

		Returns:
			List: Lista de simbolos en trading activo.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT symbol FROM trading"+str(version))
		symList = cur.fetchall()
		monitored = []
		for i in symList:
			monitored.append(i[0])
		return monitored
	def tradeEND(self, version, sym, buyP, sellP, endTS):
		"""Transfiere un trade terminado de la tabla TRADING a TRADED. Incluye el numero de version del algoritmo para identificar correctamente
		las tablas.

		Args:
			version (String|Integer): Version del algoritmo utilizada
			sym (String): Par cuyo trade se cierra
			buyP (Decimal): Precio de apertura
			sellP (Decimal): Precio de cierre
			endTS (String): Timestamp LOCAL de cierre 
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT startTS FROM trading"+str(version)+" WHERE symbol = '"+sym+"'")
		startTS = cur.fetchall()[0][0]
		cur.execute("DELETE FROM trading"+str(version)+" WHERE symbol = '"+sym+"'")
		db.commit()
		cur.execute("INSERT INTO traded"+str(version)+" VALUES('"+sym+"','"+f"{buyP:.15f}"+"','"+f"{sellP:.15f}"+"','"+startTS+"','"+str(endTS)+"')")
		db.commit()
		db.close()
	def tradeSTART(self, version, sym, startTS):
		"""Introduce el par en la tabla TRADING correspondiente a la version del algoritmo que efectua la operacion.

		Args:
			version (String|Integer): Version del algoritmo que inicia el trade
			sym (String): Par del trade
			startTS (String): Timestamp LOCAL de apertura. Se proporciona y no se genera dentro de la función para evitar posibles derivas.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("INSERT INTO trading"+str(version)+" VALUES('"+sym+"','"+startTS+"')")
		db.commit()
		db.close()