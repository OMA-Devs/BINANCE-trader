#!/usr/bin/env python3

class ALGO:
	__retired__ = ["01"]
	__versions__ = ["02","03"]
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
		"""Pasa a segunda ronda contra v01. Activa.
			Informe de efectividad 12h.
			|	DESDE: 29/12/20 08:43	HASTA: 01/01/21 13:36
			|	Trader Version: 02
			|	Beneficio BTC: 0.00459591000000000000000 €
			|	Beneficio ETH: -0.00006674470000000000000 €
			|	Beneficio BNB: -0.00265227000000000000000 €
			|	Beneficio TOTAL: 0.00187689530000000000000€
			|	Win/Lose/TOTAL: 1/5/6
			|	Efectividad: 16.667 %
			------------------------------
			Anda muy justa respecto a v01 de efectividad. Abre muchisimos menos trades, pero incurre en menos perdidas,
			cayendo en negativo solo en BNB. Genera beneficio, pero solo por la cualidad conservadora de sus aperturas.
			A mayor plazo es muy probable que incurra en las mismas perdidas que v01

			A plazo mas largo, la efectividad se reduce, pero continua con el balance positivo. De cualquier modo, es infimo.
			Solo se mantiene como version de prueba porque no incurre en tanto riesgo como v01.

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
		weight = 0
		if self.at.grow1hTOT >= self.at.monitorPERC:
			min3 = self.at.grow1h[-3:]
			for ind, val in enumerate(min3):
				if val >= 0.5:
					weight = weight + ((ind+1)*2)
				else:
					weight = weight - ((ind+1)*2)
			'''if min3[0] > 0:
				weight = weight + 2
			else:
				weight = weight + 2
			if min3[1] > 0:
				weight = weight + 4
			else:
				weight = weight - 4
			if min3[1] > 0:
				weight = weight + 6
			else:
				weight = weight - 6'''
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