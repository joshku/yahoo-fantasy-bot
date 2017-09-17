# Yahoo Fantasy Bot for NHL
This bot is for the lazy people in the world who just don't feel like logging in every day to set their lineups. This bot will login for you and start all possible players for you.

## Authentication
You will need to get a consumer key and secret from Yahoo. Check out `credentials.template.py` on how to fill in the credentials file and then name it `credentials.py`. You will need to figure out the game key, league ID and team ID yourself. To make it simple, the NHL 2017 Game Key is `376`. Your league ID and team ID can be retrieved when you login to your team online. If you look at the url you will see something like `https://hockey.fantasysports.yahoo.com/hockey/1234/0`. The `1234` is the league ID and the `0` is the team ID. 

I used the Yahoo oauth2 [documentation](https://developer.yahoo.com/oauth2/guide/flows_authcode) to figure get the authentication flow.