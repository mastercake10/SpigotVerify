# SpigotMC.org verify bot for Discord

A simple verify bot for linking your customer purchases to your support discord and assigning them roles.

It uses selenium for creating a spigot user session to bypass their cloudflare restrictions. After creating the session it will use normal requests.

## How does it work

Your customers simply type `/verify` on the discord server. 

It responds with an interaction message instructing the user to follow a link to a profile post on your spigot profile. 

The user (that (presumably) bought your plugin) likes the comment, the bot checks if they actually bought the plugin(s).

If they indeed bought the plugin, they will receive all the plugin roles on your discord + a premium or premium+ role when they bought 1 or 2+ plugins.


## Setting up the bot

tldr: Just take a look at the `settings.yml` file, you should be able to figure out what to configure.

Long version:

1. Create a new discord bot in the discord developer portal, copy the token over to the `settings.yml` file.
2. Creating roles: For each premium plugin id (you find it in your resource url) create a role and add it to the settings file. For the premium roles, just create "Premium" and "Premium+" or whatever you like
3. Create two channels, one for the purchase log (all purchase notifications will go there) and one for when a user links the account to spigot. Copy the channel id (enable discord dev mode) over to the settings file.
4. Put your spigot login details in the config.
5. Add a comment to your spigot profile which is used for linking the accounts and obtain the ID, add it to the setting file.

## Running the bot

You need to have a chrome based browser and python installed, `brave` is configured by default (see `spigot_session.py` and change `browser_executable_path` accordingly).


```bash
python3 -m pip install -r requirements.txt
python3 discord_bot.py
```