#!/usr/bin/env python3

class ALGO:
	__versions__ = [1,2]
	def v1(self):
		count = 0
		perc = 0
		if self.at.grow1hTOT > self.at.monitorPERC:
			#print(self.at.pair)
			#print(self.at.grow1h)
			for m in self.at.grow1h[-7:]:
				#print(m)
				perc = perc+m
				if m > 0.3:
					count = count + 1
			if count >= 4 and perc >= 4:
				#print(self.at.pair+": QUALIFY")
				return True
			else:
				#print(self.at.pair+": NOT QUALIFY")
				return False
		else:
			return False
	def v2(self):
		count = 0
		perc = 0
		if self.at.grow1hTOT > self.at.monitorPERC:
			for m in self.at.grow1h[-7:]:
				perc = perc+m
				if m > 0.4:
					count = count + 1
				elif m <= 0:
					count = count - 1
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
		if self.ver == "TEST":
			d = {}
			for i in self.__versions__:
				d[str(i)] = getattr(self, "v"+str(i))()
			return d
		else:
			return getattr(self,"v"+str(self.ver))()