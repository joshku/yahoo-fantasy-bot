#!/usr/bin/env python

# Python packages
import sys              #Import sys for system calls
import json             #Import json for reading and writing JSON data structures
import requests         #Import requests for HTTP(S) protocols


# Custom packages
import credentials         #Import credentials file to be used for calls to Yahoo services

#Global Variables

debug = False

REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth/v2/get_request_token"
REQUEST_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
BASE_YAHOO_API_URL = "https://fantasysports.yahooapis.com/fantasy/v2/"


def startPlayers():
    """
        This is the main function of the application. 
        It will start all players that are playing on a given day.
    """

    hasToken = False

    #if file exists mark hasToken as True

    try:
        open('tokenData.conf', 'r')
        hasToken = True
    except IOError, e:

        if "No such file or directory" in e.strerror:
            hasToken = False
        else:
            print ("IO ERROR: [%d] %s" %(e.errno, e.strerror))
            sys.exit(1)
    except Exception, e:
        print ("ERROR: [%d] %s" %(e.errno, e.strerror))
        sys.exit(1)

    if hasToken == False:
        oauth = getFullAuthorization()
    else:
        oauth = readOAuthToken()

    roster = getRoster(oauth)


def getRoster(oauth):
    """
        Get the roster from Yahoo and parses the response
    """

    rosterUrl = BASE_YAHOO_API_URL + "team/" + credentials.gameKey + ".l." + credentials.leagueId + ".t." + credentials.teamId + "/roster"
    header = "Bearer " + oauth['token']
    response = requests.get(rosterUrl, headers={'Authorization' : header})
    
    if response.status_code == 200:
        print ("Successfully got roster")
        print (response.content)
    elif response.status_code == 401 and "token_expired" in response.content:
        print ("Token Expired....renewing")
        oauth = refreshAccessToken(oauth['refreshToken'])
        getRoster(oauth)
    else:
        print ("ERROR! Could not get player roster")
        print ("-------DEBUG------\n%s\%s" % (response.status_code, response.content))
        sys.exit(1)
    
    return None

def getFullAuthorization():
    """
        Gets full authorization for the application to access Yahoo APIs and get User Data.

        Writes all relevant data to tokenData.conf
    """
    # Step 1: Get authorization from User to access their data

    authUrl = "%s?client_id=%s&redirect_uri=oob&response_type=code" % (REQUEST_AUTH_URL, credentials.consumerKey)

    if debug == True:
        print (authUrl)

    print ("You need to authorize this application to access your data.\nPlease go to %s" % (authUrl))

    authorized = 'n'

    while authorized.lower() != 'y':
        authorized = raw_input('Have you authorized me? (y/n)')
        if authorized.lower() != 'y':
            print ("You need to authorize me to continue...")

    authCode = raw_input("What is the code? ")

    # Step 2: Get Access Token to send requests to Yahoo APIs

    response = getAccessToken(authCode)

    oauth = parseResponse(response)
    
    return oauth

def readOAuthToken():
    """
        Reads the token data from file and returns a dictionary object
    """

    print ("Reading token details from file...")

    try:
        tokenFile = open('tokenData.conf', 'r')
        oauth = json.load(tokenFile)
        tokenFile.close()
    except Exception, e:
        raise e

    print ("Reading complete!")
    return oauth

def parseResponse (response):
    """
        Receives the token payload and breaks it up into a dictionary and saves it to tokenData.conf

        Returns a dictionary to be used for API calls
    """

    parsedResponse = json.loads(response)
    accessToken = parsedResponse['access_token']
    refreshToken = parsedResponse['refresh_token']
    guid = parsedResponse['xoauth_yahoo_guid']

    oauth = {}

    oauth['token'] = accessToken
    oauth['refreshToken'] = refreshToken
    oauth['guid'] = guid

    try:
        tokenFile = open('tokenData.conf', 'w')
        json.dump(oauth, tokenFile)
        tokenFile.close()

        return oauth

    except Exception, e:
        raise e

def getAccessToken(verifier):
    """
        Gets the access token used to allow access to user data within Yahoo APIs

        Returns access token payload
    """

    print ("Getting access token...")

    response = requests.post(REQUEST_TOKEN_URL, data = {'client_id' : credentials.consumerKey, 'client_secret' : credentials.consumerSecret, 'redirect_uri' : 'oob', 'code' : verifier, 'grant_type' : 'authorization_code'})

    if response.status_code == 200:
        print ("Success!")
        if debug == True:
            print response.content
        return response.content
    else:
        print ("Error! Access Token Request returned a non 200 code")
        print ("-------DEBUG-------\n%s%s" % (response.status_code, response.content))
        sys.exit(1)

def refreshAccessToken(refreshToken):
    """
        Refreshes the access token as it expires every hour

        Returns access token payload
    """

    print ("Refreshing access token...")

    response = requests.post(REQUEST_TOKEN_URL, data = {'client_id' : credentials.consumerKey, 'client_secret' : credentials.consumerSecret, 'redirect_uri' : 'oob', 'refresh_token' : refreshToken, 'grant_type' : 'refresh_token'})

    if response.status_code == 200:
        print ("Success!")
        oauth = parseResponse(response.content)
        return oauth
    else:
        print ("Error! Access Token Request returned a non 200 code")
        print ("-------DEBUG-------\n%s%s" % (response.status_code, response.content))
        sys.exit(1)


startPlayers()
