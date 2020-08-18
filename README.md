#Version 1.0 of the scraper for https://dlib.eastview.com/

URL scraper is working with, login (email) and password are to be mentioned in the file: settings.yaml

Search query that you'd like to find is neccesary to mention in a content, for example
content: Білорусь 2020

All the obtained data will be stored to xlsx file.

All the articles are download automatically.

# First install chromium browser on ubuntu
sudo apt-get install chromium-chromedriver
#Install python libraries
pip install -r requirements.txt
#Run the program
python loader.py
