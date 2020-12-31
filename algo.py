#!/usr/bin/env python3

class ALGO:
	__retired__ = []
	__versions__ = ["01","02"]
	def v01(self):
		"""Version inicial. RETIRADA.
			Informe efectividad 12h
			|	2020-12-29	DESDE: 08:43	HASTA: 21:30
			|	Trader Version: 0.1
			|	Beneficio BTC: -20.96523446710000000000000 €
			|	Beneficio ETH: -0.76744838300000000000000 €
			|	Beneficio BNB: -0.01748806116000000000000 €
			|	Beneficio TOTAL: -21.75017091126000000000000€
			|	Win/Lose/TOTAL: 13/38/51
			|	Efectividad: 25.49 %
			------------------------------
			A pesar de que genera una efectividad muy similar a v02, abre demasiados trades y arriesga demasiado.
			Incurre en perdidas en las 3 monedas utilizadas, siendo especialmente llamativo el balance BTC.
			Inasumible.

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
			|	2020-12-29	DESDE: 08:43	HASTA: 21:30
			|	Trader Version: 0.2
			|	Beneficio BTC: 0.00746137820000000000000 €
			|	Beneficio ETH: 0 €
			|	Beneficio BNB: -0.00259932516000000000000 €
			|	Beneficio TOTAL: 0.00486205304000000000000€
			|	Win/Lose/TOTAL: 1/3/4
			|	Efectividad: 25.0 %
			------------------------------
			Anda muy justa respecto a v01 de efectividad. Abre muchisimos menos trades, pero incurre en menos perdidas,
			cayendo en negativo solo en BNB. Genera beneficio, pero solo por la cualidad conservadora de sus aperturas.
			A mayor plazo es muy probable que incurra en las mismas perdidas que v01

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
	def __init__(self, at, ver):
		self.at = at #Instancia analisis tecnico.
		self.ver = ver #Version requerida. Una de las versiones o TEST
	def analisis(self):
		if self.ver in ALGO.__retired__:
			return False
		else:
			return getattr(self,"v"+str(self.ver))()