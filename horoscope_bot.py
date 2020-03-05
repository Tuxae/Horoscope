# coding: utf8
import discord
from discord.ext import commands
import asyncio
import aiohttp
import datetime as dt

from my_constants import TOKEN, channel_horoscope
from scraper import is_horoscope, get_last_image, download_image
from parse import parse_horoscope


help = """
```Help
/horoscope test_download  -- Récupère la dernière photo de RTL2 (horoscope ou pas)
/horoscope time_to_wait   -- Il faut attendre encore longtemps ?
```
"""
def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return days, hours, minutes, seconds


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        # self.bg_task = self.loop.create_task(get_facebook_img())

    async def on_ready(self):
        print('Bot ready :-)')
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def job(self):
        await self.wait_until_ready()
        while not self.is_closed():
            # Monday : 0
            # Sunday : 6
            if dt.datetime.today().weekday() <= 4 and 9 <= dt.datetime.today().hour <= 14:
                while not await self.try_get_horoscope():
                    #tasks run every 300 seconds
                    await asyncio.sleep(300) 
            time_to_wait = self.get_time_to_wait()
            await asyncio.sleep(time_to_wait.total_seconds()) 

    async def on_message(self, message):
        if message.author == client.user:
            return
        if message.content == '/horoscope help':
            await self.get_channel(channel_horoscope).send(help)
        if message.content == '/horoscope test_download':
            await self.try_get_horoscope()
        if message.content == '/horoscope time_to_wait':
            time_to_wait = self.get_time_to_wait()
            days, hours, minutes, seconds = convert_timedelta(time_to_wait)
            await self.get_channel(channel_horoscope).send("Il faut attendre encore " +
                    str(days) + " jours, " +
                    str(hours) + " heures, " +
                    str(minutes) + " minutes et "+
                    str(seconds) + " secondes avant d'avoir un nouveau horoscope.")

    async def try_get_horoscope(self):
        print("Récupération du dernier lien.")
        img_href = await get_last_image()
        print("Téléchargement de l'image...")
        filename = await download_image(img_href)
        print("Test de l'image : est-ce l'horoscope ?")
        if is_horoscope(filename):
            print("C'est l'horoscope !")
            print("OCR : en cours.")
            horoscope_text = parse_horoscope(filename)
            print("OCR : terminé.")
            await self.get_channel(channel_horoscope).send(file=discord.File(filename))
            await self.get_channel(channel_horoscope).send("```"+ str(horoscope_text) + "```")
            return True
        print("Ce n'est pas l'horoscope")
        await self.get_channel(channel_horoscope).send("La dernière image n'est pas l'horoscope :-(")
        return False

    def get_time_to_wait(self):
        time_to_wait = 0
        today = dt.datetime.today()
        day_to_wait = 1
        if dt.datetime.today().weekday() == 4:
            # it's Friday -> wait two days
            day_to_wait = 3
        # sleep until tomorrow
        next_monday = today.replace(day=today.day+day_to_wait, 
                hour=9,minute=0,second=0,microsecond=0)
        return next_monday-today

client = MyClient()
client.run(TOKEN)
