#!/usr/bin/env python

# Python packages
import sys              #Import sys for system calls
import json             #Import json for reading and writing JSON data structures
import requests         #Import requests for HTTP(S) protocols
import xmltodict        #Import xmltodict to parse XML responses to JSON
import datetime         #Import datetime to get the current date


# Custom packages
import credentials         #Import credentials file to be used for calls to Yahoo services

#Global Variables

debug = False

REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth/v2/get_request_token"
REQUEST_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
BASE_YAHOO_API_URL = "https://fantasysports.yahooapis.com/fantasy/v2/"
NEXT_GAME_URL = "https://statsapi.web.nhl.com/api/v1/teams/%s?expand=team.schedule.next"

NHL_TEAM_ID =  {
                    'New Jersey Devils' : '1',
                    'New York Islanders' : '2',
                    'New York Rangers' : '3',
                    'Philadelphia Flyers' : '4',
                    'Pittsburgh Penguins' : '5',
                    'Boston Bruins' : '6',
                    'Buffalo Sabres' : '7',
                    'Montreal Canadiens' : '8',
                    'Ottawa Senators' : '9',
                    'Toronto Maple Leafs' : '10',
                    'Carolina Hurricanes' : '12',
                    'Florida Panthers' : '13',
                    'Tampa Bay Lightning' : '14',
                    'Washington Capitals' : '15',
                    'Chicago Blackhawks' : '16',
                    'Detroit Red Wings' : '17',
                    'Nashville Predators' : '18',
                    'St. Louis Blues' : '19',
                    'Calgary Flames' : '20',
                    'Colorado Avalanche' : '21',
                    'Edmonton Oilers' : '22',
                    'Vancouver Canucks' : '23',
                    'Anaheim Ducks' : '24',
                    'Dallas Stars' : '25',
                    'Los Angeles Kings' : '26',
                    'San Jose Sharks' : '28',
                    'Columbus Blue Jackets' : '29',
                    'Minnesota Wild' : '30',
                    'Winnipeg Jets' : '52',
                    'Arizona Coyotes' : '53',
                    'Vegas Golden Knights' : '54'
                }

def main():
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

    leagueSettings = getLeagueSettings()
    roster = getRoster()
    team = []
    for player in roster['fantasy_content']['team']['roster']['players']['player']:
        # print ("Name: %s\t\tKey: %s" % (player['name']['full'], player['player_key']))
        playerData = getPlayerData(player['player_key'])
        playerData['current_position'] = player['selected_position']['position']
        playerData['key'] = player['player_key']
        team.append(playerData)
        # print playerData
    
    setLineup(team)

def getLeagueSettings():
    """
        Get the league settings from Yahoo and parses the response
    """

    rosterUrl = BASE_YAHOO_API_URL + "league/" + credentials.gameKey + ".l." + credentials.leagueId + "/settings"
    return queryYahooApi(rosterUrl, "league")

def getRoster():
    """
        Get the roster from Yahoo and parses the response
    """

    rosterUrl = BASE_YAHOO_API_URL + "team/" + credentials.gameKey + ".l." + credentials.leagueId + ".t." + credentials.teamId + "/roster"
    return queryYahooApi(rosterUrl, "roster")

def getPlayerData(playerKey):
    """
        Get player data from Yahoo and parses the response
    """

    rosterUrl = BASE_YAHOO_API_URL + "league/" + credentials.gameKey + ".l." + credentials.leagueId + "/players;player_keys=" + playerKey + "/stats"
    playerData = queryYahooApi(rosterUrl, "player")
    player = {}
    player['name'] = playerData['fantasy_content']['league']['players']['player']['name']['full']
    player['team'] = playerData['fantasy_content']['league']['players']['player']['editorial_team_full_name']
    player['available_positions'] = playerData['fantasy_content']['league']['players']['player']['eligible_positions']['position']
    player['points'] = playerData['fantasy_content']['league']['players']['player']['player_points']['total']

    url = NEXT_GAME_URL % NHL_TEAM_ID[player['team']]
    response = requests.get(url)
    nextGame = json.loads(response.content)
    player['next_game'] = nextGame['teams'][0]['nextGameSchedule']['dates'][0]['date']
    
    return player

def queryYahooApi(url, dataType):
    """
        Queries the yahoo fantasy sports api
    """

    oauth = readOAuthToken()
    header = "Bearer " + oauth['token']
    response = requests.get(url, headers={'Authorization' : header})
    
    if response.status_code == 200:
        # print ("Successfully got %s data" % dataType)
        # print (response.content)
        payload = xmltodict.parse(response.content)
        # print ("Successfully parsed %s data" % dataType)
        return payload
    elif response.status_code == 401 and "token_expired" in response.content:
        print ("Token Expired....renewing")
        oauth = refreshAccessToken(oauth['refreshToken'])
        return queryYahooApi(url, dataType)
    else:
        print ("ERROR! Could not get %s information" % dataType)
        print ("-------DEBUG------\n%s\%s" % (response.status_code, response.content))
        sys.exit(1)

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

    # print ("Reading token details from file...")

    try:
        tokenFile = open('tokenData.conf', 'r')
        oauth = json.load(tokenFile)
        tokenFile.close()
    except Exception, e:
        raise e

    # print ("Reading complete!")
    return oauth

def parseResponse (response):
    """
        Receives the token payload and breaks it up into a dictionary and saves it to tokenData.conf

        Returns a dictionary to be used for API calls
    """

    parsedResponse = json.loads(response)
    accessToken = parsedResponse['access_token']
    refreshToken = parsedResponse['refresh_token']

    oauth = {}

    oauth['token'] = accessToken
    oauth['refreshToken'] = refreshToken

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

def setLineup(roster):
    """
        Sets the lineup given a dictionary of players.
        If there is a tie, tie-breaker is by total season points
    """

    switchedPlayers = True
    while (switchedPlayers):
        switchedPlayers = False
        for benchPlayer in roster:
            if benchPlayer['current_position'] == "BN":
                print ("Looking at bench player %s" % benchPlayer['name'])
                positions = set(benchPlayer['available_positions'])
                print positions
                for player in roster:
                    if player['current_position'] in positions:
                        print ("Looking at %s" % player['name'])
                        if player['next_game'] > benchPlayer['next_game']:
                            print ("BN player has an earlier game")
                            print ("Swapping %s for %s" % (player['name'], benchPlayer['name']))
                            # swapPlayers(player, benchPlayer)
                            position = benchPlayer['current_position']
                            benchPlayer['current_position'] = player['current_position']
                            player['current_position'] = position
                            switchedPlayers = True
                            break
                        elif ((player['next_game'] == benchPlayer['next_game']) and (player['points'] > benchPlayer['points'])):
                            print ("BN player has more points")
                            print ("Swapping %s for %s" % (player['name'], benchPlayer['name']))
                            # swapPlayers(player, benchPlayer)
                            position = benchPlayer['current_position']
                            benchPlayer['current_position'] = player['current_position']
                            player['current_position'] = position
                            switchedPlayers = True
                            break
                    
    
    # for line in roster:
        # print line

    # print "\n\n\
    
def swapPlayers(currentPlayer, benchPlayer):
    """
        Sends PUT request to Yahoo to swap two players
    """
    print ("Starting %s over %s" % (benchPlayer['name'], currentPlayer['name']))
    dictPayload = {}
    dictPayload['fantasy_content'] = {}
    dictPayload['fantasy_content']['roster'] = {}
    dictPayload['fantasy_content']['roster']['coverage_type'] = "date"
    dictPayload['fantasy_content']['roster']['date'] = str(datetime.date.today())
    dictPayload['fantasy_content']['roster']['players'] = {}
    dictPayload['fantasy_content']['roster']['players']['player'] = []
    player1 = {}
    player1['position'] = benchPlayer['current_position']
    player1['player_key'] = currentPlayer['key']
    dictPayload['fantasy_content']['roster']['players']['player'].append(player1)

    player2 = {}
    player2['position'] = currentPlayer['current_position']
    player2['player_key'] = benchPlayer['key']
    dictPayload['fantasy_content']['roster']['players']['player'].append(player2)

    payload = xmltodict.unparse(dictPayload, pretty=True)
    print payload

    rosterUrl = BASE_YAHOO_API_URL + "team/" + credentials.gameKey + ".l." + credentials.leagueId + ".t." + credentials.teamId + "/roster"
    oauth = readOAuthToken()
    header = "Bearer " + oauth['token']
    response = requests.put(rosterUrl, headers={'Authorization' : header, 'Content-Type': 'application/xml'}, data=payload)
    print response.status_code
    print response.content
    # if response.status_code == 200:
    #     # print ("Successfully got %s data" % dataType)
    #     # print (response.content)
    #     payload = xmltodict.parse(response.content)
    #     # print ("Successfully parsed %s data" % dataType)
    #     return payload
    # elif response.status_code == 401 and "token_expired" in response.content:
    #     print ("Token Expired....renewing")
    #     oauth = refreshAccessToken(oauth['refreshToken'])
    #     return queryYahooApi(url, dataType)
    # else:
    #     print ("ERROR! Could not get %s information" % dataType)
    #     print ("-------DEBUG------\n%s\%s" % (response.status_code, response.content))
    #     sys.exit(1)


main()
