import os 
import sys
import random
import sqlite3
from collections import defaultdict

# con=sqlite3.connect('questions.db')
# con.execute('CREATE TABLE IF NOT EXISTS theorems (SERIAL_NO Int NOT NULL, QUESTION TEXT NOT NULL) ;')
# conn=con.cursor()

files=os.listdir('chemical_elements')
properties=defaultdict(int)
for i in files:
	# print(i)
	i=i.strip()
	file=open('chemical_elements/'+i,'r')
	temp=file.readlines()
	first=set()
	for j in temp:
		first.add(j.strip())
	for j in first:
		properties[j]+=1

final_properties=[]
for i in properties:
	properties[i]/=len(files)
	if properties[i]>=0.75:
		final_properties.append(i)

print(final_properties)

# count=1
# for i in files:
# 	i=i.strip()
# 	file=open('chemical_elements/'+i,'r')
# 	temp=file.readlines()
# 	first=set()
# 	for j in temp:
# 		first.add(j.strip())
# 	for j in final_properties:
# 		if j not in first:
# 			question='प्रमेय '+str(i)+ ' का '+str(j)+' क्या है?'
# 			conn.execute("INSERT INTO theorems (SERIAL_NO, QUESTION) VALUES (?,?);",(count,question))
# 			con.commit()
# 			print(count)
# 			count+=1
# print(count)