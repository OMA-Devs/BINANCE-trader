#!/usr/bin/env python3

import os
from algo import ALGO

cwd = os.getcwd()

totalVersions = []
manual = 0

for i in ALGO.__versions__:
	totalVersions.append(i)
for  i in ALGO.__retired__:
	totalVersions.append(i)

def removeManuallyStopped(fName):
	path = cwd+"/logs/v"+i+"/details/"+fName
	f = open(path,"r")
	for line in f.readlines():
		if "MANUALLY STOPPED" in line:
			f.close()
			os.remove(path)
			return True
	f.close()
	return False


for i in totalVersions:
	for f in os.listdir(cwd+"/logs/v"+i+"/details"):
		manual = 0
		if f[-3:] == "log":
			if removeManuallyStopped(f) == True:
				manual = manual + 1
			else:
				pass
	print("v"+i+" MANUALLY STOPPED: "+ str(manual))

