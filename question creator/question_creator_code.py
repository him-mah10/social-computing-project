import os 
import sys
import random

files=os.listdir('chemical_elements')
first_file=random.choice(files)
second_file=first_file
while second_file==first_file:
	second_file=random.choice(files)

file=open('chemical_elements/'+first_file,'r')
temp=file.readlines()
first=set()
for i in temp:
	first.add(i.strip())

file=open('chemical_elements/'+second_file,'r')
temp=file.readlines()
second=set()
for i in temp:
	second.add(i.strip())

difference=list(first-second)
value=random.choice(difference)

print('तत्व '+str(second_file)+ ' का '+str(value)+' क्या है?')