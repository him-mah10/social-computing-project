from flask import Flask,request, render_template, flash, redirect, url_for, session, logging 
from wtforms import Form,StringField,IntegerField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import sqlite3,os
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from random import randint 
import random,re
from collections import defaultdict
from googletrans import Translator
import requests
from bs4 import BeautifulSoup
import re
import sys
from SPARQLWrapper import SPARQLWrapper, JSON
#import pywikibot

endpoint_url = "https://query.wikidata.org/sparql"

app=Flask(__name__)

UPLOAD_FOLDER = './static/'
ALLOWED_EXTENSIONS = set(['svg', 'tft', 'png', 'jpg', 'jpeg', 'gif'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.',1)[1].lower()


users_db=sqlite3.connect('users.db')
users_db.execute('CREATE TABLE IF NOT EXISTS USERS (NAME TEXT NOT NULL, USERNAME TEXT NOT NULL, PASSWORD TEXT NOT NULL,SCHOOL TEXT NOT NULL,IMAGE TEXT NOT NULL,LOG INT) ;')
users_db.close()

class RegisterForm(Form):
	name=StringField('पूरा नाम: ', [validators.Length(min=2,max=200), validators.DataRequired()])
	user_name=StringField('उपयोगकर्ता नाम (अद्वितीय होना चाहिए): ', [validators.Length(min=2,max=100),validators.DataRequired()])
	school_name=StringField('विद्यालय का नाम: ', [validators.Length(min=2,max=200),validators.DataRequired()])
	password=PasswordField('पासवर्ड: ', [
		validators.DataRequired(),
		validators.EqualTo('confirm',message='पासवर्ड मेल नहीं खाते')
		])
	confirm=PasswordField('पासवर्ड की पुष्टि कीजिये: ',[validators.DataRequired()])

class LoginForm(Form):
	user_name=StringField('उपयोगकर्ता नाम:',[validators.Length(min=2,max=100),validators.DataRequired()])
	password=PasswordField('पासवर्ड: ', [
		validators.DataRequired()])

class singleplayerForm(Form):
	answer=StringField('')

class multiplayerForm(Form):
	answer1=StringField('यहाँ अपना उत्तर दर्ज करें:')
	source1=StringField('स्रोत')
	answer2=StringField('यहाँ अपना उत्तर दर्ज करें:')
	source2=StringField('स्रोत')
	answer3=StringField('यहाँ अपना उत्तर दर्ज करें:')
	source3=StringField('स्रोत')

def check_sources(source,answer):
	try:
		translator = Translator()
		ans_hi = translator.translate(str(answer), dest='hi')
		ans_en = translator.translate(str(answer), dest='en')
		r = requests.get(source)
		soup = BeautifulSoup(r.content, 'html.parser')
		match_hi = re.findall(ans_hi,str(soup))
		match_en = re.findall(ans_en,str(soup))
		if (len(match_en) > 0) or (len(match_hi) > 0):
			return True
		else:
			return False
	except:
		return False

def getScoreAndOptions(l):
	helper = defaultdict(dict)
	there_is_a_source=0
	for i in l:
		# if i['answer']=='<-- Does not exist -->':
		# 	continue

		if helper[i['answer']] == {}:
			source=i['source']
			if i['source'] != '<-- Does not exist -->':
				truth=check_sources(source,i['answer'])
				if truth==True:
					there_is_a_source=1
			else:
				truth=-1
			helper[i['answer']]={'source':source,'truth':truth,'count':1,'trust_score':0,'users':i['user']}
		else:
			helper[i['answer']]['count']+=1
			helper[i['answer']]['users']=helper[i['answer']]['users']+';'+i['user']
			if (truth==-1 or truth == False) and i['source'] != '<-- Does not exist -->':
				truth=check_sources(i['source'],i['answer'])
				if truth==True:
					helper[i['answer']]['source']=i['source']
					helper[i['answer']]['truth']=truth
					there_is_a_source+=1

	if len(helper)==1:
		key=list(helper.keys())[0]
		if helper[key]['count']>5 and there_is_a_source==1:
			return 'positive',helper
	all_ones=True
	for i in helper:
		print
		if helper[i]=='<-- Does not exist -->':
			helper[i]['trust_score']=0.15
		if helper[i]['count']!=1 and all_ones:
			all_ones=False
		if there_is_a_source==0:
			helper[i]['trust_score']=0.05*helper[i]['count']
		elif there_is_a_source==1:
			if helper[i]['truth'] == True:
				helper[i]['trust_score']=0.134*helper[i]['count']
			else:
				helper[i]['trust_score']=0.01*helper[i]['count']
		else:
			if helper[i]['truth'] == True:
				helper[i]['trust_score']=0.1*helper[i]['count']
			else:
				helper[i]['trust_score']=0.01*helper[i]['count']

	if len(helper)>2 and all_ones:
		return 'zero',helper
	if len(helper)<3 and all_ones:
		return 'negative',helper
	return 'None',helper

def move_to_single_db(question,final,category):
	# print('--------')
	# print(question)
	# print(final)
	# print('--------')
	options=''
	trust_scores=''
	sources=''

	for i in final:
		if i=='<-- Does not exist -->':
			continue
		options=options+str(i)+';'
		trust_scores=trust_scores+str(final[i]['trust_score'])+';'
		sources=sources+str(final[i]['source'])+';'
	# print(options)
	# print(trust_score)
	# print(sources)
	options=options+'इनमे से कोई भी नहीं'
	trust_scores=trust_scores+'0'
	sources=sources+'<-- Does not exist -->'
	con=sqlite3.connect("seen_questions_sp.db")
	conn=con.cursor()
	conn.execute("INSERT INTO "+category+" (question, options, trust_score, sources) VALUES (?,?,?,?);",(question,options,trust_scores,sources))
	con.commit()
	con.close()


def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


def make_wikidata_entry(item,prop,value,source):
	try:
		query = """SELECT ?item
		WHERE
		{
		  ?item rdfs:label ?label.
		  FILTER(lcase(str(?label)) IN (
		    '"""+item+"""'
		  ))
		  SERVICE wikibase:label { bd:serviceParam wikibase:language "hi". }
		}
		LIMIT 1"""
		results = get_results(endpoint_url, query)
		item=results["results"]["bindings"][0]["item"]["value"].split('/')[-1]
		print(item)

		query = """select ?p {
		  ?p a wikibase:Property ;
		       rdfs:label ?label .
		  FILTER (?label = '"""+prop+"""'@hi)
		}
		LIMIT 1"""
		results = get_results(endpoint_url, query)
		prop=results["results"]["bindings"][0]['p']['value'].split('/')[-1]
		print(prop)
		
		prop='P95435'
		item='Q212171'
		reference_url='P93'#for actual wikidata it is P854

		site=pywikibot.Site("test", "wikidata")
		repo = site.data_repository()	
		item = pywikibot.ItemPage(repo, str(item))
		
		claim = pywikibot.Claim(repo, str(prop))
		claim.setTarget(str(value))
		item.addClaim(claim)

		qualifier = pywikibot.Claim(repo, reference_url)
		qualifier.setTarget(str(source))
		claim.addSource(qualifier)
	except:
		pass


def move_to_single(session,category):
	#Generalize it, made only for elements
	# return	
	con=sqlite3.connect("seen_questions_mp.db")
	conn=con.cursor()
	print("SELECT * FROM "+category+" WHERE session_question like '"+str(session)+" - 1'")
	a=conn.execute("SELECT * FROM "+category+" WHERE session_question like '"+str(session)+" - 1'")
	set1=a.fetchall()
	question1=set1[0][0]
	list1=[]
	for i in set1:
		ans = i[1]
		source = i[3]
		user = i[5]
		if ans is None or ans == '':
			ans='<-- Does not exist -->'
			source='<-- Does not exist -->'
		elif source is None or source == '':
			source='<-- Does not exist -->'
		temp = {'answer':ans,'source':source,'user':user}
		list1.append(temp)

	a=conn.execute("SELECT * FROM "+category+" WHERE session_question like '"+str(session)+" - 2'")
	set2=a.fetchall()
	question2=set2[0][0]
	list2=[]
	for i in set2:
		ans = i[1]
		source = i[3]
		if ans is None or ans == '':
			ans='<-- Does not exist -->'
			source='<-- Does not exist -->'
		elif source is None or source == '':
			source='<-- Does not exist -->'
		temp = {'answer':ans,'source':source,'user':user}
		list2.append(temp)

	a=conn.execute("SELECT * FROM "+category+" WHERE session_question like '"+str(session)+" - 3'")
	set3=a.fetchall()
	question3=set3[0][0]
	list3=[]
	for i in set3:
		ans = i[1]
		source = i[3]
		if ans is None or ans == '':
			ans='<-- Does not exist -->'
			source='<-- Does not exist -->'
		elif source is None or source == '':
			source='<-- Does not exist -->'

		temp = {'answer':ans,'source':source,'user':user}
		list3.append(temp)
	
	q1=question1
	q3=question3
	q2=question2
	cate,final1 = getScoreAndOptions(list1)
	if cate=='positive':
		question1=question1.split('तत्व')[1]
		item=question1.split('का')[0]
		question1=question1.split('का')[1]
		prop=question1.split('क्या है?')[0]
		value=list(final1.keys())[0]

		if final1[value]['truth'] ==True:
			source=final1[value]['source']
		else:
			source=''
		make_wikidata_entry(item,prop,value,source)
	elif cate=='zero':
		con=sqlite3.connect("questions.db")
		conn=con.cursor()
		a=conn.execute("select max(serial_no) from "+category+";")		
		a=a.fetchall()[0][0]+1
		conn.execute("INSERT INTO "+category+" (SERIAL_NO, QUESTION) VALUES (?,?);",(a,question1))
		con.commit()
		con.close()
	elif cate=='None':
		move_to_single_db(question1,final1,category)


	cate,final2 = getScoreAndOptions(list2)
	if cate=='positive':
		question2=question2.split('तत्व')[1]
		item=question2.split('का')[0]
		question2=question2.split('का')[1]
		prop=question2.split('क्या है?')[0]
		value=list(final2.keys())[0]

		if final2[value]['truth'] ==True:
			source=final2[value]['source']
		else:
			source=''
		make_wikidata_entry(item,prop,value,source)
	elif cate=='zero':
		con=sqlite3.connect("questions.db")
		conn=con.cursor()
		a=conn.execute("select max(serial_no) from "+category+";")		
		a=a.fetchall()[0][0]+1
		conn.execute("INSERT INTO "+category+" (SERIAL_NO, QUESTION) VALUES (?,?);",(a,question2))
		con.commit()
		con.close()
	elif cate=='None':
		move_to_single_db(question2,final2,category)

	cate,final3 = getScoreAndOptions(list3)
	if cate=='positive':
		question3=question3.split('तत्व')[1]
		item=question3.split('का')[0]
		question3=question3.split('का')[1]
		prop=question3.split('क्या है?')[0]
		value=list(final3.keys())[0]

		if final3[value]['truth'] ==True:
			source=final3[value]['source']
		else:
			source=''
		make_wikidata_entry(item,prop,value,source)
	elif cate=='zero':
		con=sqlite3.connect("questions.db")
		conn=con.cursor()
		a=conn.execute("select max(serial_no) from "+category+";")		
		a=a.fetchall()[0][0]+1
		conn.execute("INSERT INTO "+category+" (SERIAL_NO, QUESTION) VALUES (?,?);",(a,question3))
		con.commit()
		con.close()
	elif cate=='None':
		move_to_single_db(question3,final3,category)

	con=sqlite3.connect("seen_questions_mp.db")
	conn=con.cursor()
	a=conn.execute("DELETE from "+category+" where question='"+q1+"';")
	a=conn.execute("DELETE from "+category+" where question='"+q2+"';")
	a=conn.execute("DELETE from "+category+" where question='"+q3+"';")
	con.commit()

	for i in final1:
		trust_score=1000*float(final1[i]['trust_score'])
		users=final1[i]['users']
		users=users.split(';')
		for user in users:
			ct=sqlite3.connect("users.db")
			ctt=ct.cursor()
			a=ctt.execute("update users set score=score+"+str(trust_score)+" where username='"+str(user)+"';")
			ct.commit()


@app.route('/', methods = ['GET', 'POST'])
@app.route('/index', methods = ['GET', 'POST'])
@app.route('/login', methods = ['GET', 'POST'])
def index():
	form=LoginForm(request.form)
	error=None
	con=sqlite3.connect("users.db")
	conn=con.cursor()
	if request.method=='POST' and form.validate():
		user_name=form.user_name.data
		password=form.password.data
		con=sqlite3.connect("users.db")
		conn=con.cursor()
		res=conn.execute('''SELECT PASSWORD FROM USERS WHERE USERNAME=(?);''',(user_name,))
		k=res.fetchone()
		if k == None:
			error= 'गलत उपयोगकर्ता नाम!!'
		else:
			for row in k:
				c= row
			d=sha256_crypt.verify(password,c)	
			if d==False:
				error('उपयोगकर्ता का गलत नाम और पासवर्ड!!!')
				return render_template('login.html',form=form,error=error)
			else:
				conn.execute('''UPDATE USERS SET LOG=1 WHERE USERNAME=(?);''',(user_name,))
				con.commit()
				return redirect(url_for('logged',user_name=user_name))
	con.close()
	return render_template('home.html',form=form,error=error)

@app.route('/register',methods=['GET','POST'])
def register():
	form=RegisterForm(request.form)
	error=None
	if request.method=='POST' and form.validate():
		name=form.name.data
		user_name=form.user_name.data
		school_name=form.school_name.data
		password=form.password.data
		confirm=form.confirm.data
		password=sha256_crypt.encrypt(str(form.password.data))

		con=sqlite3.connect("users.db")
		conn=con.cursor()
		res=conn.execute('''SELECT * FROM USERS WHERE USERNAME=?;''',(user_name,))
		k=res.fetchone()

		if k != None:
			error = 'उपयोगकर्ता का नाम पहले से मौजूद है'
			# print('sdfdsf')	
			return redirect(url_for('succesFullRegister'))
		# print(request.files)	
		if 'file' not in request.files:
			# print('here')
			conn.execute("INSERT INTO USERS (NAME, USERNAME, PASSWORD, SCHOOL,IMAGE,LOG,score) VALUES (?,?,?,?,'default.svg',1,0);",(name,user_name,password,school_name))
			con.commit()
			return redirect(url_for('succesFullRegister'))
		
		file = request.files['file']
		if file.filename == '':
			conn.execute("INSERT INTO USERS (NAME, USERNAME, PASSWORD, SCHOOL,IMAGE,LOG,score) VALUES (?,?,?,?,'default.svg',1,0);",(name,user_name,password,school_name))
			con.commit()
			return redirect(url_for('logged',user_name=user_name))
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			conn.execute("INSERT INTO USERS (NAME, USERNAME, PASSWORD, SCHOOL,IMAGE,LOG,score) VALUES (?,?,?,?,?,1,0);",(name,user_name,password,school_name,filename))
			con.commit()
			return redirect(url_for('logged',user_name=user_name))
		
		con.commit()
		
	return render_template('register.html',form=form)

@app.route('/succesFullRegister')
def succesFullRegister():
	return render_template('EmailSend.html')

@app.route('/logged/<user_name>',methods=['GET','POST'])
def logged(user_name):

	con=sqlite3.connect("users.db")
	conn=con.cursor()
	conn.execute("SELECT * FROM USERS WHERE USERNAME=(?);",(user_name,))
	k=conn.fetchall()
	for row in k:
		c=row
	if c[6]==0:
		conn.execute('''UPDATE USERS SET LOG=0''')
		return redirect(url_for('index'))

	##Which categories are single player ready
	categories=[0,0,0,0,0,0,0,0,0,0,0]
	con=sqlite3.connect("seen_questions_sp.db")
	conn=con.cursor()
	# 1. Compounds
	conn.execute("SELECT * FROM compounds;")
	k=conn.fetchone()	
	if k!=None:
		categories[0]=1

	# 2. Elements
	conn.execute("SELECT * FROM elements;")
	k=conn.fetchone()	
	if k!=None:
		categories[1]=1

	# 3. Stars
	conn.execute("SELECT * FROM stars;")
	k=conn.fetchone()	
	if k!=None:
		categories[2]=1

	# 4. Theorems
	conn.execute("SELECT * FROM theorems;")
	k=conn.fetchone()	
	if k!=None:
		categories[3]=1

	# 5. Diseases	
	conn.execute("SELECT * FROM diseases;")
	k=conn.fetchone()	
	if k!=None:
		categories[4]=1

	# 6. Softwares
	conn.execute("SELECT * FROM softwares;")
	k=conn.fetchone()	
	if k!=None:
		categories[5]=1

	# 7. Biological Process
	conn.execute("SELECT * FROM biologicalprocess;")
	k=conn.fetchone()	
	if k!=None:
		categories[6]=1

	# 8. Rivers
	conn.execute("SELECT * FROM rivers;")
	k=conn.fetchone()	
	if k!=None:
		categories[7]=1

	# 9. Mountains
	conn.execute("SELECT * FROM mountains;")
	k=conn.fetchone()	
	if k!=None:
		categories[8]=1	

	# 10. Countires
	conn.execute("SELECT * FROM countries;")
	k=conn.fetchone()	
	if k!=None:
		categories[9]=1

	if request.method=='POST':
		file = request.files['file']
		if file.filename == '':
			return redirect(url_for('logged',user_name=user_name))
		if file and allowed_file(file.filename):
			cont=sqlite3.connect("users.db")
			connt=cont.cursor()
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			connt.execute("UPDATE USERS SET IMAGE = (?) WHERE USERNAME = (?);",(filename,user_name))
			cont.commit()
			cont.close()
			return redirect(url_for('logged',user_name=user_name))
	return render_template("homeLog.html",c=c,categories=categories,user_name=user_name)

@app.route('/Logout/<user_name>')
def logout(user_name):
	con=sqlite3.connect("users.db")
	conn=con.cursor()
	conn.execute("UPDATE USERS SET LOG=0 WHERE USERNAME=(?);",(user_name,))
	con.commit()
	return redirect(url_for('index'))

@app.route('/logged/<user_name>/howtoplay')
def howtoplay(user_name):
	return render_template("howtoplay.html",user_name=user_name)

multiplayer_questions={
	'compounds':{},
	'elements':{},
	'stars':{},
	'theorems':{},
	'diseases':{},
	'softwares':{},
	'biologicalprocess':{},
	'rivers':{},
	'mountains':{},
	'countries':{}
}


def multiplayer_question(user_name,category):
	con=sqlite3.connect("essential.db")
	conn=con.cursor()
	print(category)
	a=conn.execute("SELECT * FROM ESSENTIAL WHERE KEY='"+category+"_mutliplayer_session';")
	tem=a.fetchone()[1]
	print("----")
	print(tem.split(';'))
	print("----")
	temp=tem.split(';')
	temp[0]=int(temp[0])
	temp[1]=int(temp[1])
	# print(temp[1])
	if temp[1] > 9:
		# print("I was here")
		session=temp[0]
		move_to_single(session,category)
		value=str(session+1)+';0'
		contt=sqlite3.connect("essential.db")
		conntt=contt.cursor()
		conntt.execute("UPDATE ESSENTIAL SET VALUE=(?) WHERE KEY='"+category+"_mutliplayer_session';",(value,))
		contt.commit()
		contt.close()
		# print("SDFSDFS")
		return multiplayer_question(user_name,category)
	else:
		names=''
		for i in range(len(temp)-2):
			names=names+';'+temp[2+i]
		names=names+';'+user_name	
		session=temp[0]
		# print(temp)
		if user_name in temp:
			ret=[session,session,session,0]
			return ret

		value=str(session)+';'+str(temp[1]+1)+names
		conn.execute("UPDATE ESSENTIAL SET VALUE=(?) WHERE KEY='"+category+"_mutliplayer_session';",(value,))
		con.commit()
		if session not in multiplayer_questions[category]:
			# print('here here')
			con=sqlite3.connect("questions.db")
			conn=con.cursor()
			multiplayer_questions[category][session]=[]
			question=conn.execute("SELECT * FROM "+category+" ORDER BY RANDOM() LIMIT 3;").fetchall()
			multiplayer_questions[category][session].append(question[0][1])
			multiplayer_questions[category][session].append(question[1][1])
			multiplayer_questions[category][session].append(question[2][1])
			# conn.execute("DELETE from "+category+" where SERIAL_NO="+str(question[0][0]))
			# conn.execute("DELETE from "+category+" where SERIAL_NO="+str(question[1][0]))
			# conn.execute("DELETE from "+category+" where SERIAL_NO="+str(question[2][0]))
			# con.commit()
			# print(question)
		
		ret=multiplayer_questions[category][session]
		ret.append(1)
		return ret

def pre_process_data(textt):
    textt = str(textt)
    textt = textt.strip()
    textt = re.sub(r",", " ", textt)
    textt = re.sub(r"\.", " ", textt)
    textt = re.sub(r"!", " ! ", textt)
    textt = re.sub(r"\/", " ", textt)
    textt = re.sub(r"\^", " ^ ", textt)
    textt = re.sub(r"\+", " + ", textt)
    textt = re.sub(r"\-", " - ", textt)
    textt = re.sub(r"\=", " = ", textt)
    textt = re.sub(r"'", " ", textt)
    textt = re.sub(r":", " : ", textt)
    textt = re.sub(' +',' ',textt)
    textt = re.sub(';',' ',textt)
    return textt

record=''
@app.route('/logged/<user_name>/multiplayer/<category>/',methods=['GET','POST'])
def multiplayer(user_name,category):
	question=multiplayer_question(user_name,category)
	if question != -1:
		record=question
	# print(record)
	form=multiplayerForm(request.form)
	if request.method=='POST' and form.validate():
		answer1=form.answer1.data
		source1=form.source1.data
		answer2=form.answer2.data
		source2=form.source2.data
		answer3=form.answer3.data
		source3=form.source3.data
		# print('----------')
		answer1=pre_process_data(answer1)
		answer1=pre_process_data(answer2)
		answer1=pre_process_data(answer3)
		source1=pre_process_data(source1)
		source2=pre_process_data(source2)
		source3=pre_process_data(source3)

		con=sqlite3.connect("seen_questions_mp.db")
		conn=con.cursor()
		try:
			session=question[0]
			question=multiplayer_questions[category][session]
			v1 = str(session)+' - 1' 
			v2 = str(session)+' - 2' 
			v3 = str(session)+' - 3' 
			conn.execute("INSERT INTO "+category+" (question, options, trust_score, sources, session_question,user_name) VALUES (?,?,'',?,?,?);",(question[0],answer1,source1,v1,user_name))
			conn.execute("INSERT INTO "+category+" (question, options, trust_score, sources, session_question,user_name) VALUES (?,?,'',?,?,?);",(question[1],answer2,source2,v2,user_name))
			conn.execute("INSERT INTO "+category+" (question, options, trust_score, sources, session_question,user_name) VALUES (?,?,'',?,?,?);",(question[2],answer3,source3,v3,user_name))
			con.commit()
		except:
			pass
		# print(answer1)
		# print(source1)
		# print(answer2)
		# print(source2)
		# print(answer3)
		# print(source3)
		
		# print('----------')
		return redirect(url_for('logged',user_name=user_name))
	else:
		pass

	# if  == 0:
	# 	return('Already played this session, wait for it to get over.')
	return render_template("multiplayer.html",question=question,form=form,user_name=user_name,already_played=question[3])

def singleplayer_question(user_name,category):
	con=sqlite3.connect("seen_questions_sp.db")
	conn=con.cursor()
	conn.execute("SELECT * FROM "+category+" ORDER BY RANDOM() LIMIT 1;")
	k=conn.fetchone()
	question=k[0]
	options=k[1].split(';')
	return question,options
	
prev_question=''
@app.route('/logged/<user_name>/singleplayer/<category>/',methods=['GET','POST'])
def singleplayer(user_name,category):
	question,options=singleplayer_question(user_name,category)
	form=singleplayerForm(request.form)
	# print(question)
	# print(options)
	if '<-- Does not exist -->' in options:
		options.remove('<-- Does not exist -->')

	if request.method=='POST' and form.validate():
		answer=form.answer.data
		question=answer.split(';')[0].strip()
		answer=answer.split(';')[1].strip()
		con=sqlite3.connect("essential.db")
		conn=con.cursor()
		a=conn.execute("SELECT * FROM essential where value='"+question+"' and key='"+user_name+"';")
		a=a.fetchone()
		if a is None:
			conn.execute("INSERT INTO essential (key, value) VALUES (?,?);",(user_name,question))
			con.commit()
			cont=sqlite3.connect("seen_questions_sp.db")
			connt=cont.cursor()
			connt.execute("SELECT * FROM '"+category+"' where question='"+question+"';")
			k=connt.fetchone()
			temp=k[1].split(';')
			i=temp.index(answer)
			temp=k[2].split(';')
			sourcess=k[3].split(';')
			print(temp)
			if i == (len(temp)-1):
				for j in range(len(temp)-1):
					temp[j]=float(temp[j])-0.04;
					temp[j]=str(temp[j])
			else:
				for j in range(len(temp)-1):
					temp[j]=float(temp[j])-0.02;
					temp[j]=str(temp[j])
				temp[i]=float(temp[i])+0.15
				if temp[i] >= 0.8:
					question=question.split('तत्व')[1]
					item=question.split('का')[0]
					question=question.split('का')[1]
					prop=question.split('क्या है?')[0]
					value=answer
					if sourcess[i]=='<-- Does not exist -->':
						s=''
					else:
						s=sourcess[i]
					
					make_wikidata_entry(item,prop,value,s)
				else:
					temp[i]=str(temp[i])
					temp=';'.join(temp)
					connt.execute("update '"+category+"' set trust_score='"+temp+"' where question='"+question+"';")
					cont.commit()
		return redirect(url_for('logged',user_name=user_name))
	return render_template("singleplayer.html",question=question,options=options,user_name=user_name,form=form)

if __name__ == '__main__':
	cot=sqlite3.connect("users.db")
	cont=cot.cursor()
	cont.execute("UPDATE USERS SET LOG=0")
	cot.commit()
	app.secret_key='RadheRadhe'
	app.run(debug=True)
