#!/usr/bin/env python3

import interactions
from interactions import listen, Intents
from interactions import ComponentContext, SlashContext

from spigot_scraper import SpigotScraper
from spigot_session import SpigotSession
import json
import asyncio
import yaml

settings = yaml.safe_load(open("settings.yml", "r"))

bot = interactions.Client(intents=Intents.DEFAULT, sync_interactions=True, asyncio_debug=True)

class SpigotHandler:
    def __init__(self) -> None:
        self.spigotSession = SpigotSession(settings["login"]["user"], settings["login"]["password"], settings["login"]["2fa_provider"])
        self.spigotSession.restore()

        soup = self.spigotSession.getSoup("https://www.spigotmc.org/")

        if not soup or not soup.find(id="userBar"):
            print("user not logged in, logging in...")
            self.spigotSession.login()
            print("logged in.")

        self.spigotSession.save()

        # update with new details
        soup = self.spigotSession.getSoup("https://www.spigotmc.org/")

        username = soup.find_all("a", class_="username")[0]
        user_id = username["href"].split("/")[1]
        print(f"Logged in as: {username.text}/{user_id}")

        self.scraper = SpigotScraper(self.spigotSession, user_id)
        try:
            f = open('resources.json')
            self.resources = json.load(f)

            if isinstance(list(self.resources.keys())[0], str):
                # convert old str keys to ints
                converted = {}       
                for key, value in self.resources.items():
                    if isinstance(key, str):
                        converted[int(key)] = value
                self.resources = converted

                

        except FileNotFoundError:
            self.resources = {}

        # get all premium resource of current user
        self.resource_ids = self.scraper.get_resources()
        # update entire buyer list of (new) resources
        for id in filter(lambda x: x not in self.resources, self.resource_ids):
            title, max_page = self.scraper.get_resource_page_info(id)
            print(f"Getting all buyers for resource id: {id}, title: {title}")
            buyers = []
            for i in range(1, max_page+1):
                buyers.extend(self.scraper.get_buyers(id, page_num=i))
                print(f"Page [{i} / {max_page}], Buyers: {len(buyers)}")

            self.resources[int(id)] = buyers

        f = open('resources.json', 'w')
        json.dump(self.resources, f, default=lambda x: x.__dict__)
        f.close()

        self.linked_users = {}
        try:
            f = open('linked_users.json')
            self.linked_users = json.load(f)
        except FileNotFoundError:
            self.linked_users = {}

    async def update_buyers(self) -> None:
        """Updating buyers of resources, only checking first page"""
        for id in self.resource_ids:
            # only check first page for new buyers
            buyers = self.scraper.get_buyers(id, page_num=0)
            for buyer in buyers:
                add = True
                for buyer2 in self.resources[id]:
                    if type(buyer2) == dict:
                        if buyer2["user_id"] == buyer.user_id:
                            add = False
                    else:
                        if buyer2.user_id == buyer.user_id:
                            add = False
                if add:
                    self.resources[id].append(buyer)
                    name = settings["roles"]["resources"][id]
                    print(f"User {buyer.user_id} just bought {name}!")
                    await info_buy(f"User {buyer.user_id} just bought {name}!")
                    await asyncio.sleep(1)
                    f = open('resources.json', 'w')
                    json.dump(self.resources, f, default=lambda x: x.__dict__)
                    f.close()

    def get_plugins_bought(self, spigot_user: str) -> set[str]:
        plugins_bought = set()
        for res_id in self.resources:
            for buyEntry in self.resources[res_id]:
                if type(buyEntry) is dict and buyEntry["user_id"] == spigot_user or hasattr(buyEntry, 'user_id') and buyEntry.user_id == spigot_user:
                    plugins_bought.add(res_id)

        return plugins_bought
    
    def get_last_user_liking(self) -> str:
        new_likes = self.scraper.get_profile_post_likes()
        last_user = None
        likes = []
        for user in new_likes:
            if user not in likes:
                likes.append(user)
                last_user = user

        return last_user
    
    async def link(self, discord_id: int, spigot_id: str, ctx: ComponentContext) -> None:
        if spigot_id not in self.linked_users:
            self.linked_users[spigot_id] = discord_id
            await ctx.send(f"Sucessfully linked your account with https://www.spigotmc.org/members/{spigot_id}!", ephemeral=True)
            await info_verify(f"User <@{discord_id}> linked account to https://www.spigotmc.org/members/{spigot_id}")
            await updata_roles(discord_id, spigot_id)
            f = open('linked_users.json', 'w')
            json.dump(self.linked_users, f)
            f.close()
        else:
            await ctx.send("Failed to link: Please like the profile post first", ephemeral=True)


@listen()
async def on_startup() -> None:
    global spigotHandler
    spigotHandler = SpigotHandler()

@listen()
async def on_ready() -> None:
    global guild
    guild = bot.get_guild(settings["guild_id"])
    print(f"Active in guild: {guild.name}")

    buy_task.start()
    await buy_task()

async def updata_roles(discord_id, spigot_id) -> None:
    res_ids = spigotHandler.get_plugins_bought(spigot_id)
    await handle_roles(discord_id, res_ids)


from interactions import Task, TimeTrigger

@Task.create(TimeTrigger(hour=0, minute=5))
async def buy_task() -> None:
    print("Checking for new buyers...")
    await spigotHandler.update_buyers()


complete_button = interactions.Button(
    custom_id="complete_button",
    style=interactions.ButtonStyle.DANGER,
    label="Done",
)

@interactions.slash_command(
    name="verify",
    description="Connects your SpigotMC-Account with Discord. Also gives you access to premium channels.",
)
async def verify_command(ctx: SlashContext) -> None:
    await ctx.send("Please go to my profile and like the Verifcation post to link your discord account with SpigotMC! Click \"Done\" when you're done liking. https://www.spigotmc.org/members/mastercake.29634/#profile-post-196759", 
        ephemeral=True,
        components=complete_button)

@interactions.component_callback(complete_button.custom_id)
async def button_response(ctx: ComponentContext) -> None:
    last_user = spigotHandler.get_last_user_liking()

    if last_user:
        await spigotHandler.link(int(ctx.author.user.id), last_user, ctx)
    else:
        await ctx.send("Failed to link: Please like the profile post first", ephemeral=True)

async def handle_roles(user_id, resource_ids) -> None:
    resource_roles = settings["roles"]["resources"]

    for resource in resource_ids:
        role_name = resource_roles[resource]
        for role in guild.roles:
            if role.name == role_name:
                break

        member = guild.get_member(int(user_id))
    
        await member.add_role(role, "Verify Bot")
        print(f"Added role {role.name} to {member.display_name}")
    
    premium_roles = [next(filter(lambda r: r.name == name, guild.roles)) for name in settings["roles"]["premium"]]
    if len(resource_ids) > 0:
        await member.add_role(premium_roles[0], "Verify Bot")
        print(f"Added role {premium_roles[0].name} to {member.display_name}")
    if len(resource_ids) > 1:
        await member.add_role(premium_roles[1], "Verify Bot")
        print(f"Added role {premium_roles[1].name} to {member.display_name}")


from interactions.models.discord.snowflake import to_snowflake

async def private_message(user_id: int, msg: str) -> None:
    data = await bot.http.create_dm(user_id)
    channel_id = to_snowflake(data["id"])
    payload = interactions.models.discord.process_message_payload(msg)
    await bot.http.create_message(channel_id=channel_id, payload=payload)

async def info_verify(msg: str) -> None:
    await guild.get_channel(settings["channels"]["verify_log"]).send(msg)

async def info_buy(msg: str) -> None:
    await guild.get_channel(settings["channels"]["buy_log"]).send(msg)

bot.start(settings["discord_api_token"])