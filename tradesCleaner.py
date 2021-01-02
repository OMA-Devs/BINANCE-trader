#!/usr/bin/env python3

import os
from algo import ALGO

cwd = os.getcwd()

totalVersions = []

for i in ALGO.__versions__:
	totalVersions.append(i)
for  i in ALGO.__retired__:
	totalVersions.append(i)

def removeManuallyStopped(fName,v):
	path = cwd+"/logs/v"+v+"/details/"+fName
	f = open(path,"r")
	for line in f.readlines():
		if "MANUALLY STOPPED" in line:
			f.close()
			os.remove(path)
			print(fName+" REMOVED")
	f.close()

def moveTo(fName, v):
	path = cwd+"/logs/v"+v+"/details/"+fName
	winPath = cwd+"/logs/v"+v+"/details/wins/"
	losePath = cwd+"/logs/v"+v+"/details/losses/"
	f = open(path, "r")
	for line in f.readlines():
		if "You win for" in line:
			f.close()
			os.rename(path, winPath+fName)
			print(fName+" Moved to WINS")
		if "You lose for" in line:
			f.close()
			os.rename(path, losePath+fName)
			print(fName+" Moved to LOSSES")

if __name__ == "__main__":
	for i in totalVersions:
		for f in os.listdir(cwd+"/logs/v"+i+"/details"):
			if f[-3:] == "log":
				try:
					removeManuallyStopped(f,i)
					moveTo(f,i)
				except FileNotFoundError:
					print(f+" File Moved Previously")