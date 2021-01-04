#!/usr/bin/env python3

from decimal import Decimal

class ALGO:
	__retired__ = ["01","02"]
	__versions__ = ["03", "04"]
	def v01(self):
		"""Version inicial. RETIRADA.
			Informe efectividad
			|	DESDE: 29/12/20 08:43	HASTA: 01/01/21 13:36
			|	Trader Version: 01
			|	Beneficio BTC: -22.80949190030000000000000 €
			|	Beneficio ETH: -0.79818166420000000000000 €
			|	Beneficio BNB: -0.12799260000000000000000 €
			|	Beneficio TOTAL: -23.73566616450000000000000€
			|	Win/Lose/TOTAL: 26/54/80
			|	Efectividad: 32.5 %
			------------------------------
			A pesar de que genera una efectividad muy similar a v02 en el lapso de 12h, abre demasiados trades y arriesga demasiado.
			Incurre en perdidas en las 3 monedas utilizadas, siendo especialmente llamativo el balance BTC.
			Inasumible.

			A plazo mas largo, aumenta su efectividad respecto a v02, pero continua incurriendo en perdidas.

		Returns:
			Boolean: Cualifica o no cualifica para abrir trade
		"""
		#print("Checking "+self.at.pair+": V01")
		count = 0
		perc = 0
		if self.at.grow1hTOT > self.at.monitorPERC:
			for m in self.at.grow1h[-7:]:
				perc = perc+m
				if m > 0.3:
					count = count + 1
			if count >= 4 and perc >= 4:
				return True
			else:
				return False
		else:
			return False
	def v02(self):
		"""Pasa a segunda ronda contra v01. RETIRADA.
			Informe de efectividad
			|	DESDE: 29/12/20 08:43	HASTA: 02/01/21 16:23
			|	Trader Version: 02
			|	Beneficio BTC: -0.03067053600000000000000 €
			|	Beneficio ETH: -0.00006842220000000000000 €
			|	Beneficio BNB: -0.00189100610000000000000 €
			|	Beneficio TOTAL: -0.03262996430000000000000€
			|	Win/Lose/TOTAL: 7/9/16
			|	Efectividad: 43.75 %
			------------------------------
			------------------------------
			Anda muy justa respecto a v01 de efectividad. Abre muchisimos menos trades, pero incurre en menos perdidas,
			cayendo en negativo solo en BNB. Genera beneficio, pero solo por la cualidad conservadora de sus aperturas.
			A mayor plazo es muy probable que incurra en las mismas perdidas que v01

			A plazo mas largo, la efectividad se reduce, pero continua con el balance positivo. De cualquier modo, es infimo.
			Solo se mantiene como version de prueba porque no incurre en tanto riesgo como v01.

			Efectivamente, a largo plazo termina generando pérdidas. Aunque la efectividad ha aumentado drasticamente, las
			perdidas tambien aumentan. Se retira la version.

		Returns:
			Boolean: cualifica o no para abrir trade
		"""
		#print("Checking "+self.at.pair+": v02")
		count = 0
		perc = 0
		#Primero comprueba que el crecimiento en una hora sea el marcado por el AT.
		if self.at.grow1hTOT > self.at.monitorPERC:
			#Comprueba los ultimos 7 minutos.
			for m in self.at.grow1h[-7:]:
				#Suma los porcentajes de crecimiento por minuto.
				perc = perc+m
				#Si el porcentaje de ese minuto supera el 0.4, se suma uno a la cuenta de peso.
				if m > 0.4:
					count = count + 1
				#Si el porcentaje es 0 o negativo, se resta uno. Se utiliza este contrapeso para evitar klines donde hay bajadas.
				elif m <= 0:
					count = count - 1
			#Si la cuenta de peso es mayor que 4 y el porcentaje sumado es del 5%, cualifica.
			if count >= 4 and perc >= 5:
				return True
			else:
				return False
		else:
			return False
	def v03(self):
		"""Pruebas iniciales contra v02. ACTIVA
			Informe de efectividad
			|	01/01/21 a 02/01/21
			|	Trader Version: 03
			|	Beneficio BTC: -0.02274499130000000000000 €
			|	Beneficio ETH: -0.02483103840000000000000 €
			|	Beneficio BNB: -0.12347339830000000000000 €
			|	Beneficio TOTAL: -0.17104942800000000000000€
			|	Win/Lose/TOTAL: 29/37/66
			|	Efectividad: 43.939 %
			------------------------------
			Mantiene una efectividad alta con un gran numero de trades. Es la primera version con un sistema de pesos dinamico
			para identificar la relevancia de los ultimos porcentajes. Basicamente asigna puntos en base a los ultimos 3 minutos,
			asignando más cuanto más cerca estan en el tiempo para localizar las subidas.

			Al ser la primera versión y analizando los trades, se han identificado varias vulnerabilidades que se intentaran paliar
			en v04, contra la que se va a medir. 


		Returns:
			[type]: [description]
		"""
		weight = 0
		if self.at.grow1hTOT >= self.at.monitorPERC:
			min3 = self.at.grow1h[-3:]
			for ind, val in enumerate(min3):
				if val >= 0.5:
					weight = weight + ((ind+1)*2)
				else:
					weight = weight - ((ind+1)*2)
			if weight >= 5:
				return True
			else:
				return False
		else:
			return False
	def v04(self):
		"""Pruebas iniciales contra v03. ACTIVA
			Informe de efectividad
			|	
			------------------------------
			Posee el mismo esquema basico de pesos que v03 pero añade una condicion AND a la puntuación. Cada porcentaje debe ser mayor que
			el anterior para identificar las oportunidades ganadoras mucho mejor. Esto va a cortar muchos trades perdedores de la v03, aunque
			he identificado otros ganadores que tambien se perderán.
			Se añade además una condicion para que el limite no sea nunca superior al maximo diario encontrado.


		Returns:
			[type]: [description]
		"""
		weight = 0
		if self.at.grow1hTOT >= self.at.monitorPERC:
			min3 = self.at.grow1h[-3:]
			for ind, val in enumerate(min3):
				try:
					if val >= 0.6 and val < min3[ind+1]:
						weight = weight + ((ind+1)*2)
					else:
						weight = weight - ((ind+1)*2)
				except IndexError:
					if val >= 0.6 :
						weight = weight + ((ind+1)*2)
					else:
						weight = weight - ((ind+1)*2)
			if weight >= 5:
				return True
			else:
				return False
		else:
			return False
	def __init__(self, at, ver):
		self.at = at #Instancia analisis tecnico.
		self.ver = ver #Version requerida. Una de las versiones
	def analisis(self):
		if self.ver in ALGO.__retired__:
			return False
		else:
			return getattr(self,"v"+str(self.ver))()