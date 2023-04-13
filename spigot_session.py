import os
from xvfbwrapper import Xvfb
# Virtual desktop for running headless and still passing Cloudflare

if not os.environ.get('DISPLAY'):
    # start virtual desktop for selenium
    vdisplay = Xvfb(width=800, height=1280)
    vdisplay.start()

import undetected_chromedriver as uc
from selenium import webdriver
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pickle
from bs4 import BeautifulSoup
import time

class SpigotSession:
    RATE_LIMIT = 2.5

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.last_req = None

    def make_new_cf_session(self) -> None:
        if not self.session:
            self.session = requests.Session()

        options = webdriver.ChromeOptions()
        options.add_argument(f'--no-sandbox')
        driver = uc.Chrome(options=options, browser_executable_path="/usr/bin/google-chrome")

        # calling a non-exisiting url for adding cookies before accessing the website
        driver.get("https://www.spigotmc.org/e")
        for cookie in self.session.cookies:
            driver.add_cookie({"name": cookie.name, "value": cookie.value, "domain": cookie.domain})


        driver.get('https://www.spigotmc.org/')

        try:
            WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//iframe[@title="Widget containing a Cloudflare security challenge"]')))
        except:
            print("no cf challenge iframe found")
        finally:
            pass

        challenge_button_path = '//*[@id="challenge-stage"]/div/label/input'
        challenge_button_path2 = '//*[@id="cf-stage"]/div[6]/label/input'
        spigot_userbar_path = '//*[@id="userBar"]'

        #print(driver.page_source.encode("utf-8"))
        try:
            # waiting for loading the home site
            print("Waiting for challenge buttons to appear...")
            element = WebDriverWait(driver, 200).until(EC.any_of(
                        EC.presence_of_element_located((By.XPATH, challenge_button_path)),
                        EC.presence_of_element_located((By.XPATH, challenge_button_path2)),
                        EC.presence_of_element_located((By.XPATH, spigot_userbar_path))
                )
            )
        except:
            #print(driver.page_source.encode("utf-8"))
            print("Challenge button not found.")
        finally:
            time.sleep(2)

            if element.get_attribute("id") != "userBar":
                element.click()
                print("Clicked cloudflare challenge button")
            driver.switch_to.default_content()

        try:
            # waiting for loading the home site
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, spigot_userbar_path)))
        except:
            #print(driver.page_source.encode("utf-8"))
            print(driver.title)
        finally:
            # Transfer selenium user agent and cookies to request.Session object
            selenium_user_agent = driver.execute_script("return navigator.userAgent;")
            self.session.headers.update({"user-agent": selenium_user_agent})

            for cookie in driver.get_cookies():
                self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            if not os.environ.get('DISPLAY'):
                vdisplay.stop()
            driver.quit()
        
    def login(self) -> None:
        """Creates a new session on spigotmc.org"""
        data = {
            "login": self.username,
            "register": 0,
            "password": self.password,
            "remember": 1,
            "cookie_check": 1,
            "_xfToken": "",
            "redirect": "."}

        res = self.session.post("https://www.spigotmc.org/login/login", data=data)
        print(res.text)
        code = input("Please enter 2FA code:")
        
        if code:
            data = {
                "code": code,
                "trust": 1,
                "provider": "email",
                "_xfConfirm": 1,
                "_xfToken": "",
                "remember": 1,
                "redirect": "https://www.spigotmc.org/",
                "save": "Confirm",
                "_xfRequestUri": "/login/two-step?redirect:https%3A%2F%2Fwww.spigotmc.org%2F&remember=1",
                "_xfNoRedirect": 1,
                "_xfResponseType": "json"
            }
            res = self.session.post("https://www.spigotmc.org/login/two-step", data=data)
        
            print(res.status_code)

    def save(self) -> None:
        """Saves the current session to pickle file."""
        data = {"user-agent": self.session.headers["user-agent"], "cookies": self.session.cookies}
        pickle.dump(data, open("session.p", "wb"))
                    
    def restore(self) -> None:
        """Restores session from pickle file."""
        try:
            data = pickle.load(open("session.p", "rb"))
        except:
            self.session = requests.Session()
            return
            
        self.session = requests.Session()
        self.session.headers.update({"user-agent": data["user-agent"]})
        self.session.cookies = data["cookies"]

    def getRequestSession(self) -> requests.Session:
        return self.session

    def getSoup(self, url: str) -> BeautifulSoup:
        """Crates a new soup and renews the session when a cloudflare-challenge comes up"""
        # rate limit
        while self.last_req and time.time_ns() - self.last_req < self.RATE_LIMIT * 1000 * 1000 * 1000:
            pass

        try:

            response = self.session.get(url, timeout=5)
        except ConnectionResetError:
            print(f"error getting {url}")
            self.getSoup(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        if not response.ok:
            if True or soup.find(id="cf-content"):
                # cf challenge, new session
                print("Creating new CF-Session...")
                self.make_new_cf_session()
                return self.getSoup(url)
            else:
                return None

        self.last_req = time.time_ns()
        
        return soup
