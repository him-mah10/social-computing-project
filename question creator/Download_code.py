import sys
from SPARQLWrapper import SPARQLWrapper, JSON
import random

endpoint_url = "https://query.wikidata.org/sparql"

query = """SELECT ?item ?itemLabel 
WHERE 
{
  ?item wdt:P31 wd:Q11173.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],hi". }
}"""

def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


results = get_results(endpoint_url, query)
print("HERE0")
all_elements=[]
names=[]
for result in results["results"]["bindings"]:
    all_elements.append(result['item']['value'].split('/')[-1])
    names.append(result['itemLabel']['value'])

properties_list=[]
count=0
print("HERE")
for i in range(len(all_elements)):
	query = """SELECT ?wdLabel {
	  VALUES (?element) {(wd:"""+str(all_elements[i])+""")}

	  ?element ?p ?statement .
	  

	  ?wd wikibase:claim ?p.
	  

	  SERVICE wikibase:label { bd:serviceParam wikibase:language "hi" }
	} ORDER BY ?wd ?statement ?ps_"""

	def get_results(endpoint_url, query):
	    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
	    # TODO adjust user agent; see https://w.wiki/CX6
	    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
	    sparql.setQuery(query)
	    sparql.setReturnFormat(JSON)
	    return sparql.query().convert()


	file=open(names[i],'w')
	for i in properties_list:
		for j in i:
			print(j)
	results = get_results(endpoint_url, query)
	for result in results["results"]["bindings"]:
		if result['wdLabel']['value'][0] != 'P':
			file.write(str(result['wdLabel']['value'])+'\n')



# first=random.randint(1,5)
# second=first
# while second==first:
# 	second=random.randint(1,5)
# print(first)
# print(second)
# print(list(properties_list[first]-properties_list[second]))
