#!/usr/bin/env python

from bs4 import BeautifulSoup
import requests
import os
import json
import sys

ROTOWORLD_URL = "http://www.rotoworld.com/playernews/nhl/hockey-player-news"
DIRECTORY_PATH = os.path.dirname(os.path.realpath(__file__))
ROTOWORLD_PATH = DIRECTORY_PATH + '/rotoworld.txt'

def main():
    """
        Scrapes rotoworld.com and gets all goalie related news
    """"

    response = requests.get(ROTOWORLD_URL)
    soup = BeautifulSoup(response.content, 'html.parser')

    newsList = []
    currentBlurb = {}
    for div in soup.find_all('div', ['player', 'report', 'date']):
        if len(div.contents) == 1:
            currentBlurb['date'] = div.string
            if currentBlurb['position'] == "G":
                newsList.append(currentBlurb)
                currentBlurb = {}
        elif len(div.contents) == 3:
            currentBlurb['news'] = div.contents[1].string
        elif len(div.contents) == 4:
            blurb = {}
            blurb['name'] = div.contents[0].string
            position = "None"
            if "C" in div.contents[1].string:
                position = "C"
            elif "W" in div.contents[1].string:
                position = "W"
            elif "D" in div.contents[1].string:
                position = "D"
            elif "G" in div.contents[1].string:
                position = "G"
            
            blurb['position'] = position
            currentBlurb = blurb
            

    # for news in newsList:
    #     print news

    rotoworld = getFileContents()
    insertNews(rotoworld, newsList)

def getFileContents():
    """
        Opens a file and reads all existing saved rotoworld articles
    """
    
    rotoworldList = []
    try:
        rotoworldFile = open(ROTOWORLD_PATH, 'r')
        fileList = list(rotoworldFile)
        for line in fileList:
            newDict = json.loads(line)
            rotoworldList.append(newDict)
        rotoworldFile.close()
        return rotoworldList
    except IOError, e:
        if "No such file or directory" in e.strerror:
            return None
    except Exception, e:
        print("ERROR: [%d] %s" %(e.errno, e.strerror))
        sys.exit(1)
    


def insertNews(existingNews, newNews):
    """
        Merges all new articles with existing articles and saves to file
    """

    if len(existingNews) != 0:
        for article in newNews:
                for blurb in existingNews:
                    if article['date'] != blurb['date'] and article['name'] != blurb['name']:
                        existingNews.append(article)
    else:
        existingNews = newNews

    # print existingNews
    rotoworldFile = open(ROTOWORLD_PATH, 'w')

    for entry in existingNews:
        json.dump(entry, rotoworldFile)
    
main()