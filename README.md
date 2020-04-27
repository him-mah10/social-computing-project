# Social Computing Project
Hello, this is a repository containing my work for Social Computing Project, take by Prof. Vasudeva Vara, at IIIT Hyderabad. The project aims to enhance Hindi and Telugu Wikidata using gamification.

I have attached PDFs explaining the approach and final aim of the project.

The project uses python3, flask, and pywikibot (for further details check the requirements.txt file). 

## Setting up the game:
1. First, we need a Wikidata id and password which will henceforth be referred to as bot. This account will be used to make Wikidata entries.
2. Next, download pywikibot from this link https://tools.wmflabs.org/pywikibot/core_stable.zip. 
3. Then extract the zip file and run this command: python3 pwb.py generate_user_files. 
4. You will see a list of options to choose from. The first list asks you to choose which project are you working on. Since we are working on Wikidata, choose Wikidata. The second list asks you to choose what language/variant of Wikidata you are working on. If your bot is authorized then choose Wikidata otherwise choose Test.
5. It will then ask for your bot's username and password. Enter them. You will see a user config file generated.
6. Please make sure that your game files are in the same folder as the config file i.e. the entire game should be in the core_stable folder.

## Steps to run the game:
All of the above steps need to be done only once i.e. they are steps for setting up the game. Follow the following step every time you want to run the game:
1. python3 pwb.py login
2. python3 app.py
3. Next, visit the localhost in your browser i.e. http://127.0.0.1:5000/ to play the game.

I have pushed a pdf presentation describing the flow of the game.

I faced some difficulties setting up pywikibot, using it to add statements and references. So I wrote the following article, please check: https://medium.com/@himanshumaheshwari_41605/bots-to-update-wikidata-181ef932e2dc
