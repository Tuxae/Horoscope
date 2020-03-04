# coding: utf8
import discord
from discord.ext import commands
import asyncio
import aiohttp
import datetime

from my_constants import TOKEN, channel_horoscope
from scraper import is_horoscope, get_last_image, download_image

bot = commands.Bot(command_prefix='$')

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        # self.bg_task = self.loop.create_task(self.get_facebook_img())

    async def on_ready(self):
        print('Bot ready :-)')
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def get_facebook_img(self):
        await self.wait_until_ready()
        while not self.is_closed():
            img_href = await get_last_image()
            filename = await download_image(img_href)
            if is_horoscope(filename):
                await self.get_channel(channel_horoscope).send(file=discord.File(filename))
                await asyncio.sleep(10) 
            await asyncio.sleep(300) #tasks run every 300 seconds

client = MyClient()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == '$test':
        print("On m'appelle !")
        img_href = await get_last_image()
        filename = await download_image(img_href, filename="test.jpg")
        await client.get_channel(channel_horoscope).send(file=discord.File(filename))

client.run(TOKEN)
