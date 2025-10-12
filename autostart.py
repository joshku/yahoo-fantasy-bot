#!/usr/bin/env python

# Python packages
import sys                              #Import sys for system calls
import os                               #Import os to get directory information
import json                             #Import json for reading and writing JSON data structures
import requests                         #Import requests for HTTP(S) protocols
import xmltodict                        #Import xmltodict to parse XML responses to JSON
import datetime                         #Import datetime to get the current date
import logging                          #Import logging to send output to a log file
import time                             #Import time to get epoch time
from collections import OrderedDict     #Import OrderedDict to set the key order in a dictionary

#Global Variables
REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth/v2/get_request_token"
REQUEST_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
REQUEST_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
BASE_YAHOO_API_URL = "https://fantasysports.yahooapis.com/fantasy/v2/"
NEXT_GAME_URL = "https://api-web.nhle.com/v1/club-schedule/%s/week/now"
DIRECTORY_PATH = os.path.dirname(os.path.realpath(__file__))
TOKEN_PATH = DIRECTORY_PATH + '/tokenData.conf'

consumerKey = os.environ['CONSUMER_KEY']
consumerSecret = os.environ['CONSUMER_SECRET']
gameKey = os.environ['GAME_KEY']
leagueId = os.environ['LEAGUE_ID']
teamId = os.environ['TEAM_ID']


NHL_TEAM_ID =  {
                    'New Jersey Devils' : 'NJD',
                    'New York Islanders' : 'NYI',
                    'New York Rangers' : 'NYR',
                    'Philadelphia Flyers' : 'PHI',
                    'Pittsburgh Penguins' : 'PIT',
                    'Boston Bruins' : 'BOS',
                    'Buffalo Sabres' : 'BUF',
                    'Montreal Canadiens' : 'MTL',
                    'Ottawa Senators' : 'OTT',
                    'Toronto Maple Leafs' : 'TOR',
                    'Carolina Hurricanes' : 'CAR',
                    'Florida Panthers' : 'FLA',
                    'Tampa Bay Lightning' : 'TBL',
                    'Washington Capitals' : 'WSH',
                    'Chicago Blackhawks' : 'CHI',
                    'Detroit Red Wings' : 'DET',
                    'Nashville Predators' : 'NSH',
                    'St. Louis Blues' : 'STL',
                    'Calgary Flames' : 'CGY',
                    'Colorado Avalanche' : 'COL',
                    'Edmonton Oilers' : 'EDM',
                    'Vancouver Canucks' : 'VAN',
                    'Anaheim Ducks' : 'ANA',
                    'Dallas Stars' : 'DAL',
                    'Los Angeles Kings' : 'LAK',
                    'San Jose Sharks' : 'SJS',
                    'Columbus Blue Jackets' : 'CBJ',
                    'Minnesota Wild' : 'MIN',
                    'Winnipeg Jets' : 'WPG',
                    'Utah Mammoth' : 'UTA',
                    'Vegas Golden Knights' : 'VGK',
                    'Seattle Kraken': 'SEA'
                }

def main():
    """
        This is the main function of the application. 
        It will start all players that are playing on a given day.
    """

    logging.info("Starting Auto-Start Bot...")
    hasToken = False

    if 'YAHOO_TOKEN' in os.environ:
        try:
            oauth = json.loads(os.environ['YAHOO_TOKEN'])
            tokenFile = open(TOKEN_PATH, 'w')
            json.dump(oauth, tokenFile)
            tokenFile.close()

        except Exception as e:
            raise e
        hasToken = True

        # Check to see if the token data file is present
    try:
        logging.debug("Token Path: %s" % TOKEN_PATH)
        open(TOKEN_PATH, 'r')
        hasToken = True
    except IOError as e:

        if "No such file or directory" in e.strerror:
            hasToken = False
        else:
            logging.error("IO ERROR: [%d] %s" %(e.errno, e.strerror))
            sys.exit(1)
    except Exception as e:
        logging.error("ERROR: [%d] %s" %(e.errno, e.strerror))
        sys.exit(1)

    if hasToken == False:
        logging.info("Token file not present. Beginning authorization process...")
        oauth = getFullAuthorization()

    leagueSettings = getLeagueSettings()
    roster = getRoster()
    team = []
    for player in roster['fantasy_content']['team']['roster']['players']['player']:
        playerData = getPlayerData(player['player_key'])
        playerData['current_position'] = player['selected_position']['position']
        playerData['key'] = player['player_key']
        team.append(playerData)
        logging.info("Fetched %s (%i pts) data" % (playerData['name'], playerData['points']))

    setLineup(team)

def getLeagueSettings():
    """
        Get the league settings from Yahoo and parses the response
    """

    rosterUrl = BASE_YAHOO_API_URL + "league/" + gameKey + ".l." + leagueId + "/settings"
    return queryYahooApi(rosterUrl, "league")

def getRoster():
    """
        Get the roster from Yahoo and parses the response
    """

    rosterUrl = BASE_YAHOO_API_URL + "team/" + gameKey + ".l." + leagueId + ".t." + teamId + "/roster"
    return queryYahooApi(rosterUrl, "roster")

def getPlayerData(playerKey):
    """
        Get player data from Yahoo and parses the response
    """

    rosterUrl = BASE_YAHOO_API_URL + "league/" + gameKey + ".l." + leagueId + "/players;player_keys=" + playerKey + "/stats;type=biweekly"
    playerData = queryYahooApi(rosterUrl, "player")
    player = {}
    player['name'] = playerData['fantasy_content']['league']['players']['player']['name']['full']
    player['team'] = playerData['fantasy_content']['league']['players']['player']['editorial_team_full_name']
    player['available_positions'] = playerData['fantasy_content']['league']['players']['player']['eligible_positions']['position']
    if 'player_notes_last_timestamp' in playerData['fantasy_content']['league']['players']['player']:
        player['new_notes_timestamp'] = int(playerData['fantasy_content']['league']['players']['player']['player_notes_last_timestamp'])
    else:
        player['new_notes_timestamp'] = '-1'

    points = 0
    print(playerData['fantasy_content']['league']['players']['player']['player_stats']['stats']['stat'])
    for stat in playerData['fantasy_content']['league']['players']['player']['player_stats']['stats']['stat']:
        if stat['value'] == '-':
            points += 0
        elif stat['stat_id'] == '22':       # Goals Against counts against overall score
            points -= int(stat['value'])
        else:
            points += int(stat['value'])

    player['points'] = points

    url = NEXT_GAME_URL % NHL_TEAM_ID[player['team']]
    response = requests.get(url)
    nextGame = json.loads(response.content)
    player['next_game'] = nextGame['games'][0]['gameDate']
    
    return player

def queryYahooApi(url, dataType):
    """
        Queries the yahoo fantasy sports api
    """

    oauth = readOAuthToken()
    header = "Bearer " + oauth['token']
    logging.debug("URL: %s" % url)
    response = requests.get(url, headers={'Authorization' : header})
    
    if response.status_code == 200:
        logging.debug("Successfully got %s data" % dataType)
        logging.debug(response.content)
        payload = xmltodict.parse(response.content)
        logging.debug("Successfully parsed %s data" % dataType)
        return payload
    elif response.status_code == 401 and b"token_expired" in response.content:
        logging.info("Token Expired....renewing")
        oauth = refreshAccessToken(oauth['refreshToken'])
        return queryYahooApi(url, dataType)
    else:
        logging.error("Could not get %s information" % dataType)
        logging.error("---------DEBUG--------")
        logging.error("HTTP Code: %s" % response.status_code)
        logging.error("HTTP Response: \n%s" % response.content)
        logging.error("-------END DEBUG------")
        sys.exit(1)

def getFullAuthorization():
    """
        Gets full authorization for the application to access Yahoo APIs and get User Data.

        Writes all relevant data to tokenData.conf
    """

    # Step 1: Get authorization from User to access their data
    authUrl = "%s?client_id=%s&redirect_uri=oob&response_type=code" % (REQUEST_AUTH_URL, consumerKey)
    logging.debug(authUrl)
    print ("You need to authorize this application to access your data.\nPlease go to %s" % (authUrl))
    authorized = 'n'

    while authorized.lower() != 'y':
        authorized = input('Have you authorized me? (y/n)')
        if authorized.lower() != 'y':
            print ("You need to authorize me to continue...")

    authCode = input("What is the code? ")

    # Step 2: Get Access Token to send requests to Yahoo APIs
    response = getAccessToken(authCode)
    oauth = parseResponse(response)
    return oauth

def readOAuthToken():
    """
        Reads the token data from file and returns a dictionary object
    """

    logging.debug("Reading token details from file...")

    try:
        tokenFile = open(TOKEN_PATH, 'r')
        oauth = json.load(tokenFile)
        tokenFile.close()
    except Exception as e:
        raise e

    logging.debug("Reading complete!")
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
        tokenFile = open(TOKEN_PATH, 'w')
        json.dump(oauth, tokenFile)
        tokenFile.close()

        return oauth

    except Exception as e:
        raise e

def getAccessToken(verifier):
    """
        Gets the access token used to allow access to user data within Yahoo APIs

        Returns access token payload
    """

    logging.info("Getting access token...")

    response = requests.post(REQUEST_TOKEN_URL, data = {'client_id' : consumerKey, 'client_secret' : consumerSecret, 'redirect_uri' : 'oob', 'code' : verifier, 'grant_type' : 'authorization_code'})

    if response.status_code == 200:
        logging.info("Success!")
        logging.debug(response.content)
        return response.content
    else:
        logging.error("Access Token Request returned a non 200 code")
        logging.error("---------DEBUG--------")
        logging.error("HTTP Code: %s" % response.status_code)
        logging.error("HTTP Response: \n%s" % response.content)
        logging.error("-------END DEBUG------")
        sys.exit(1)

def refreshAccessToken(refreshToken):
    """
        Refreshes the access token as it expires every hour

        Returns access token payload
    """

    logging.info("Refreshing access token...")

    response = requests.post(REQUEST_TOKEN_URL, data = {'client_id' : consumerKey, 'client_secret' : consumerSecret, 'redirect_uri' : 'oob', 'refresh_token' : refreshToken, 'grant_type' : 'refresh_token'})

    if response.status_code == 200:
        logging.info("Success!")
        logging.debug(response.content)
        oauth = parseResponse(response.content)
        return oauth
    else:
        logging.error("Access Token Request returned a non 200 code")
        logging.error("---------DEBUG--------")
        logging.error("HTTP Code: %s" % response.status_code)
        logging.error("HTTP Response: \n%s" % response.content)
        logging.error("-------END DEBUG------")
        sys.exit(1)

def setLineup(roster):
    """
        Sets the lineup given a dictionary of players.
        If there is a tie, tie-breaker is total biweekly points
        To start a goalie, checks to see if there is a new note since 3 AM PT of the current day
        Typically there is a note for the goalie stating they will start on the day they are playing
    """

    swapStatus = False
    today = str(datetime.date.today())
    for benchPlayer in roster:
        is_last_note_timestamp_today = int(benchPlayer['new_notes_timestamp']) > int(datetime.date.today().strftime('%s')) + 10800
        if (benchPlayer['current_position'] == "BN" and benchPlayer['next_game'] == today and benchPlayer['available_positions'] != 'G' and 'IR' not in benchPlayer['available_positions'] and 'IR+' not in benchPlayer['available_positions']) or (benchPlayer['available_positions'] == 'G' and benchPlayer['current_position'] == "BN" and benchPlayer['next_game'] == today and is_last_note_timestamp_today):
            logging.info("Looking at bench player %s" % benchPlayer['name'])
            positions = set(benchPlayer['available_positions'])
            logging.debug(positions) 
            player = findNonPlayingPlayer(positions, roster)

            if player is not None:
                logging.debug("Benching %s for %s" % (player['name'], benchPlayer['name']))
                swapStatus = swapPlayers(player, benchPlayer)

            else:
                player = findNextEligiblePlayer(positions, roster)
                # logging.info("Bench Points: %s Player Points: %s" % (benchPlayer['points'], player['points']))
                if float(benchPlayer['points']) > float(player['points']):
                    logging.debug("Benching %s for %s" % (player['name'], benchPlayer['name']))
                    swapStatus = swapPlayers(player, benchPlayer)
                else:
                    logging.info("Not starting %s because he has lower points" % player['name'])
            
            if swapStatus == True:
                position = player['current_position']
                player['current_position'] = benchPlayer['current_position']
                benchPlayer['current_position'] = position

    for line in roster:
        logging.debug(line)


def findNonPlayingPlayer(positions, roster):
    """
        Looks for the first player not playing on the current date and returns it
    """

    logging.debug("Today's date: %s" % str(datetime.date.today()))
    today = str(datetime.date.today())
    for player in roster:
        timestamp_diff = (int(time.time()) - int(player['new_notes_timestamp'])) / 3600
        if player['current_position'] == 'G' and player['next_game'] == today and timestamp_diff > 6:
            return player
        if player['current_position'] in positions and player['next_game'] > today:
            logging.debug("Found player %s who plays on %s" % (player['name'], player['next_game']))
            return player

        # Bench an injured player
        if player['current_position'] in positions and 'IR' in player['available_positions'] or 'IR+' in player['available_positions']:
            logging.debug("Found injured player %s" % player['name'])
            return player
    
    logging.info("All players playing today")
    return None

def findNextEligiblePlayer(positions, roster):
    """
        Looks for the next eligible player with the lowest points biweekly and returns it
    """

    today = str(datetime.date.today())
    selectedPlayer = None
    for player in roster:
        if selectedPlayer is None and player['current_position'] in positions:
            selectedPlayer = player
            logging.debug("Thinking of starting %s" % selectedPlayer)
            pass

        if player['current_position'] in positions and float(player['points']) < float(selectedPlayer['points']) and player['current_position'] != "BN":
            logging.debug("Thinking of starting %s" % player)
            selectedPlayer = player        
    
    logging.info("Found %s to be the next eligible player" % selectedPlayer['name'])
    return selectedPlayer

def swapPlayers(currentPlayer, benchPlayer):
    """
        Sends PUT request to Yahoo to swap two players
    """

    logging.info("Starting %s over %s" % (benchPlayer['name'], currentPlayer['name']))
    dictPayload = {}
    dictPayload['fantasy_content'] = {}
    dictPayload['fantasy_content']['roster'] = {}
    dictPayload['fantasy_content']['roster']['coverage_type'] = "date"
    dictPayload['fantasy_content']['roster']['date'] = str(datetime.date.today())
    dictPayload['fantasy_content']['roster']['players'] = {}
    dictPayload['fantasy_content']['roster']['players']['player'] = []
    player1 = {}
    player1['player_key'] = benchPlayer['key']
    player1['position'] = currentPlayer['current_position']
    # Using an ordered dictionary because a regular dictionary does not respect order
    orderedP1 = OrderedDict(sorted(player1.items()))
    dictPayload['fantasy_content']['roster']['players']['player'].append(orderedP1)

    player2 = {}
    player2['player_key'] = currentPlayer['key']
    player2['position'] = benchPlayer['current_position']
    orderedP2 = OrderedDict(sorted(player2.items()))
    dictPayload['fantasy_content']['roster']['players']['player'].append(orderedP2)
    payload = xmltodict.unparse(dictPayload, pretty=True)
    logging.debug(payload)

    rosterUrl = BASE_YAHOO_API_URL + "team/" + gameKey + ".l." + leagueId + ".t." + teamId + "/roster"
    oauth = readOAuthToken()
    header = "Bearer " + oauth['token']
    response = requests.put(rosterUrl, headers={'Authorization' : header, 'Content-Type': 'application/xml'}, data=payload)

    if response.status_code == 200:
        logging.info("Successfully started %s and benched %s" % (benchPlayer['name'], currentPlayer['name']))
        return True
    elif response.status_code == 401 and "token_expired" in response.content:
        logging.info("Token Expired....renewing")
        oauth = refreshAccessToken(oauth['refreshToken'])
        return queryYahooApi(url, dataType)
    else:
        logging.error("Could not start players")
        logging.error("---------DEBUG--------")
        logging.error("HTTP Code: %s" % response.status_code)
        logging.error("HTTP Response: \n%s" % response.content)
        logging.error("-------END DEBUG------")
        return False

    return True

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

main()
logging.info("Done!")
