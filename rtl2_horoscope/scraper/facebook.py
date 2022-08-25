from selenium import webdriver
from bs4 import BeautifulSoup
from typing import List

from rtl2_horoscope.scraper import Scraper
from rtl2_horoscope.utils import log

ALBUM_URL = "https://www.facebook.com/pg/rtl2/photos/?tab=album&album_id=248389291078&ref=page_internal"
WEBDRIVER_URL = 'http://selenium-horoscope:4444/wd/hub'

class FacebookScraper(Scraper):

    def __init__(self, album_url: str = ALBUM_URL, webdriver_url: str = WEBDRIVER_URL):
        super().__init__(social_media="facebook")
        self.album_url = album_url
        self.webdriver_url = webdriver_url

    def get_last_images(self, **kwargs) -> List[str]:

        log("Initialize Webdriver")
        driver = webdriver.Remote(
            self.webdriver_url,
            options=webdriver.ChromeOptions()
        )
        driver.set_window_size(1280, 1024)
        log(f"Get {self.album_url} ...")
        driver.get(self.album_url)
        log("Done")
        page_source = driver.page_source
        driver.close()

        soup = BeautifulSoup(page_source, features="html5lib")

        hrefs = []

        for a in soup.find_all("a"):
            for img in a.find_all("img"):
                hrefs.append(img['src'])

        return hrefs

