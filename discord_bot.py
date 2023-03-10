#!/usr/bin/env python3

import interactions
from interactions.api.models.guild import Guild
from interactions.api.cache import Item
from interactions.api.models.member import Member
from interactions.api.models.channel import Channel

from spigot_scraper import SpigotScraper
from spigot_session import SpigotSession
import json
import asyncio
import yaml

settings = yaml.safe_load(open("settings.yml", "r"))

bot = interactions.Client(token=settings["discord_api_token"])

roles = settings["roles"]

premium_roles = settings["premium_roles"]

s = SpigotSession(settings["login"]["user"], settings["login"]["password"])
s.restore()

soup = s.getSoup("https://www.spigotmc.org/")

if not soup or not soup.find(id="userBar"):
    print("user not logged in, logging in...")
    s.login()
    print("logged in.")

s.save()

username = soup.find_all("a", class_="username")[0]
user_id = username["href"].split("/")[1]
print(f"Logged in as: {username.text}/{user_id}")

scraper = SpigotScraper(s, user_id)
try:
    f = open('resources.json')
    resources = json.load(f)
except FileNotFoundError:
    resources = {}

resource_ids = scraper.get_resources()

linked_users = {}
try:
    f = open('linked_users.json')
    linked_users = json.load(f)
except FileNotFoundError:
    linked_users = {}

async def update_buyers():
    for id in resource_ids:
        buyers = scraper.get_buyers(id, page_num=0)
        for buyer in buyers:
            add = True
            for buyer2 in resources[id]:
                if type(buyer2) == dict:
                    if buyer2["user_id"] == buyer.user_id:
                        add = False
                else:
                    if buyer2.user_id == buyer.user_id:
                        add = False
            if add:
                resources[id].append(buyer)
                name = roles[id]
                print("tesdt")
                await info_buy(f"User {buyer.user_id} just bought {name}!")
                await asyncio.sleep(1)
                f = open('resources.json', 'w')
                json.dump(resources, f, default=lambda x: x.__dict__)
                f.close()

for id in resource_ids:
    if id not in resources:
        print(f"getting buyers for {id}")
        max_page = scraper.get_buyer_page_count(id)
        buyers = []
        for i in range(1, max_page+1):
            buyers.extend(scraper.get_buyers(id, page_num=i))

        resources[id] = buyers

    f = open('resources.json', 'w')
    json.dump(resources, f, default=lambda x: x.__dict__)
    f.close()

def get_plugins_bought(spigot_user):
    plugins_bought = set()
    for res_id in resources:
        for buyEntry in resources[res_id]:
            if type(buyEntry) is dict and buyEntry["user_id"] == spigot_user or hasattr(buyEntry, 'user_id') and buyEntry.user_id == spigot_user:
                plugins_bought.add(res_id)

    return plugins_bought

async def updata_roles(discord_id, spigot_id):
    res_ids = get_plugins_bought(spigot_id)
    await handle_roles(discord_id, res_ids)

async def link(discord_id, spigot_id):
    if spigot_id not in linked_users:
        linked_users[spigot_id] = discord_id
        #await private_message(discord_id, f"Sucessfully linked your account with https://www.spigotmc.org/members/{spigot_id}!")
        await info(f"User <@{discord_id}> linked account to https://www.spigotmc.org/members/{spigot_id}")
        await updata_roles(discord_id, spigot_id)
        f = open('linked_users.json', 'w')
        json.dump(linked_users, f)
        f.close()


async def handle_messages():
    for msg in scraper.get_messages():
        if "Verification" in msg["title"]:
            if len(msg["title"].split(" ")) > 2:
                id = msg["title"].split(" ")[2]
                if id.isnumeric():
                    id = int(id)
                    await link(id, msg["sender"])

async def message_task():
    while not bot.loop.is_closed():
        print("Checking for new messages...")
        await handle_messages()
        await asyncio.sleep(60)

async def buy_task():
    while not bot.loop.is_closed():
        print("Checking for new buyers...")
        await update_buyers()
        await asyncio.sleep(60 * 5)

likes = []
def get_last_user_liking():
    new_likes = scraper.get_profile_post_likes()
    last_user = None
    for user in new_likes:
        if user not in likes:
            likes.append(user)
            last_user = user

    return last_user
             

get_last_user_liking()

complete_button = interactions.Button(
    style=interactions.ButtonStyle.DANGER,
    label="Done",
    custom_id="primary",
    scope=347179
)

@bot.event
async def on_ready():
    print("bot is now online.")

@bot.command(
    name="verify",
    description="Connects your SpigotMC-Account with Discord. Also gives you access to premium channels.",
)
async def verify_command(ctx: interactions.CommandContext):
    code = ctx.author.user.id
    bot.http.cache.members.add(Item(id=str(code), value=ctx.author))
    await ctx.send("Please go to my profile and like the Verifcation post to link your discord account with SpigotMC! Click \"Done\" when you're done liking. https://www.spigotmc.org/members/mastercake.29634/#profile-post-196759", 
        ephemeral=True,
        components=complete_button)
    #await ctx.send(f"Please send any message to me on spigot to verify using this link: \nhttps://www.spigotmc.org/conversations/add?to=MasterCake&title=Verification%2C+Code%3A+{code}+%28DONT+CHANGE+SUBJECT%2C+Write+%27verify%27+below+as+message%29", ephemeral=True)
    
@bot.component(complete_button)
async def button_response(ctx: interactions.ComponentContext):
    print("someone clicked the button! :O")
    last_user = get_last_user_liking()
    #last_user = "zedar_yt.1112302"

    if last_user:
        await link(int(ctx.author.user.id), last_user)
        await ctx.send(f"Sucessfully linked your account to {last_user}", ephemeral=True)
    else:
        await ctx.send("Failed to link: Please like the profile post first", ephemeral=True)

async def handle_roles(user_id, resource_ids):
    guild = await bot.http.get_guild(330725294749122561)
    guild = Guild(**guild)
    
    for resource in resource_ids:
        role_name = roles[resource]
        for role in guild.roles:
            if role["name"] == role_name:
                break

        member = await bot.http.get_member(330725294749122561, int(user_id))
        member = Member(**member)

        await bot.http.add_member_role(guild.id, member.user.id, role["id"], "Verify Bot")
    
    if len(resource_ids) > 0:
        await bot.http.add_member_role(guild.id, member.user.id, premium_roles[0], "Verify Bot")
    if len(resource_ids) > 1:
        await bot.http.add_member_role(guild.id, member.user.id, premium_roles[1], "Verify Bot")
    print("added role")

   #res = await bot.http.add_member_role(guild_id=330725294749122561, user_id=int(user_id), role_id=468453568391806977, reason="Verify bot")

async def info(msg):
    await bot.http.send_message(927339823553978468, msg)

async def private_message(user_id, msg):
    channel = await bot.http.create_dm(int(user_id))
    channel = Channel(**channel)

    await bot.http.send_message(channel.id, msg)

async def info_buy(msg):
    await bot.http.send_message(927349992836960348, msg)


bot.loop.create_task(buy_task())
bot.start()

