from bs4 import BeautifulSoup
import re

from spigot_session import SpigotSession

from typing import Optional

class User:
    def __init__(self, name: str, user_id: str, discord_id: int) -> None:
        self.name = name
        self.user_id = user_id
        self.discord_id = discord_id
    
class BuyEntry:
    def __init__(self, user_id: str, resource_id: str, date: str, price: str) -> None:
        self.user_id = user_id
        self.resource_id = resource_id
        self.date = date
        self.price = price


class SpigotScraper:
    URL_RESOURCES = "https://www.spigotmc.org/resources/authors/{author_id}/"
    URL_BUYERS = "https://www.spigotmc.org/resources/{resource_id}/buyers?page={page_num}"
    URL_CONVERSATIONS = "https://www.spigotmc.org/conversations/"
    URL_PROFILE_POST_LIKES = "https://www.spigotmc.org/profile-posts/{post_id}/likes"

    def __init__(self, session: SpigotSession, author_id: str) -> None:
        self.session = session
        self.author_id = author_id

    def get_resources(self, filter_only_premium=True) -> Optional[list[int]]:
        response = self.session.getRequestSession().get(self.URL_RESOURCES.format(author_id=self.author_id))

        if not response.ok:
            return None

        resources = []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find("ol", { "class" : "resourceList" }).findAll('div', class_="main")
        for item in items:
            resource_id = item.div.h3.a["href"].split(".")[-1][:-1]
            is_premium = item.div.span["class"][0] == "cost"

            if is_premium and filter_only_premium:
                resources.append(int(resource_id))

        return resources

    def get_buyers(self, resource_id: str, page_num=0) -> list:
        soup = self.session.getSoup(self.URL_BUYERS.format(resource_id=resource_id, page_num=page_num))
        items = soup.findAll("li", {"class": "memberListItem"})
        buy_entries = []
        for item in items:
            user = item.findAll("div", class_="member")[0].h3.a
            user_id = user["href"].split("/")[1]
            user_name = user.text

            extra = item.findAll("div", class_="extra")[0]
    
            date = ""
            if extra.abbr:
                date = extra.abbr["data-time"]

            price = extra.div.text if extra.findAll("div", class_="muted") else ""

            buyEntry = BuyEntry(user_id, user_name, date, price)
            buy_entries.append(buyEntry)

        return buy_entries


    def get_resource_page_info(self, resource_id: str) -> tuple[str, int]:
        soup = self.session.getSoup(self.URL_BUYERS.format(resource_id=resource_id, page_num=0))

        a_ = soup.findAll("a", href=re.compile("buyers\?page=\d*"))
        max_page = 0
        for a in a_:
            num = a["href"].split("buyers?page=")[1]
            if not num.isnumeric():
                continue
            if int(num) > max_page:
                max_page = int(num)

        return soup.find("title").get_text().split(" | ")[0], max_page

    def get_messages(self) -> list[dict]:
        soup = self.session.getSoup(self.URL_CONVERSATIONS)

        entries = soup.findAll("div", class_="titleText")
        messages = []

        for entry in entries:
            title = entry.h3.a.text
            sender = entry.div.div.a["href"].split("/")[1]
            messages.append({"title": title, "sender": sender})

        return messages

    def get_profile_post_likes(self, post_id) -> list[str]:
        soup = self.session.getSoup(self.URL_PROFILE_POST_LIKES.format(post_id=post_id))

        users = []
        entries = soup.findAll("li", {"class": "memberListItem"})
        for entry in entries:
            users.append(entry.a["href"].split("/")[1])

        return users

