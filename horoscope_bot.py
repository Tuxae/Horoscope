# coding: utf8
import discord
import requests
import asyncio
import aiohttp
import bs4
from bs4 import BeautifulSoup

from my_constants import TOKEN, channel_horoscope
from scraper import is_horoscope, get_last_image

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.get_facebook_img())
        self.old_tweets_url = []

    async def on_ready(self):
        print('Bot ready :-)')
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def get_facebook_img(self):
        await self.wait_until_ready()
        while not self.is_closed():
            img_href = get_last_image()
            img = requests.get(img_href)
            if img.status_code == 200:
                img = img.content
                if is_horoscope(img):
                    # TO DO
            await asyncio.sleep(120) #tasks run every 120 seconds

client = MyClient()
client.run(TOKEN)
