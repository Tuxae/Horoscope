# coding: utf8
import discord
from discord.ext import commands
import asyncio
import aiohttp
import datetime as dt
import hashlib
import os

from my_constants import TOKEN, IMG_FOLDER, channel_horoscope
from scraper import is_horoscope, get_last_image, download_image
from parse import parse_horoscope, reformat_horoscope
from utils import convert_timedelta, md5


manual  = """
```Help
<@!{id}> test  -- Récupère la dernière photo de RTL2 (horoscope ou pas)
<@!{id}> last  -- Donne le dernier horoscope de RTL2 
<@!{id}> time_to_wait   -- Il faut attendre encore longtemps ?
```
"""

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.job())

    async def on_ready(self):
        if not os.path.isdir(IMG_FOLDER):
            print(f"Création du dossier {IMG_FOLDER}")
            os.mkdir(IMG_FOLDER)
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
            today = dt.datetime.today()
            if today.weekday() <= 4 and 7 <= today.hour <= 11:
                while not await self.try_get_horoscope():
                    #tasks run every 300 seconds
                    await asyncio.sleep(300) 
            time_to_wait = self.get_time_to_wait()
            print(f"A demain, reprise de l'activité dans {time_to_wait.total_seconds()} secondes.")
            await asyncio.sleep(time_to_wait.total_seconds()) 

    async def on_message(self, message):
        print(message.content)
        if message.author == client.user:
            return
        if message.content == '<@!{}> help'.format(self.user.id):
            await self.get_channel(channel_horoscope).send(manual.format(id=self.user.id))
        if message.content == '<@!{}> test'.format(self.user.id):
            await self.try_get_horoscope(force=True)
        if message.content == '<@!{}> last'.format(self.user.id):
            files = sorted(os.listdir("images/"), reverse=True)
            if len(files) == 0:
                await self.get_channel(channel_horoscope).send("Aucun horoscope en stock :-(")
                return
            print("OCR : en cours.")
            last_horoscope = "images/" + files[0]
            horoscope_dict = parse_horoscope(last_horoscope)
            horoscope_str = reformat_horoscope(horoscope_dict)
            print("OCR : terminé.")
            await self.get_channel(channel_horoscope).send(file=discord.File(last_horoscope))
            await self.get_channel(channel_horoscope).send(horoscope_str)
        if message.content == '<@!{}> time_to_wait':
            time_to_wait = self.get_time_to_wait()
            days, hours, minutes, seconds = convert_timedelta(time_to_wait)
            await self.get_channel(channel_horoscope).send("Il faut attendre encore " +
                    str(days) + " jours, " +
                    str(hours) + " heures, " +
                    str(minutes) + " minutes et "+
                    str(seconds) + " secondes avant d'avoir un nouveau horoscope.")

    async def try_get_horoscope(self, force=False):
        print("Récupération du dernier lien.")
        img_href = await get_last_image()
        print("Téléchargement de l'image...")
        if force:
            filename = await download_image(img_href, filename="images/0000-00-00_test.jpg")
        else:
            filename = await download_image(img_href)
        files = sorted(os.listdir("images/"), reverse=True)
        f1, f2 = "images/" + files[0], "images/" + files[1]
        # If force, send file without check
        if force:
            f1, f2 = "images/0000-00-00_test.jpg", "images/" + files[0]
            await self.get_channel(channel_horoscope).send(file=discord.File(f1))
            return True
        print("Test de l'image : est-ce l'horoscope ?")
        if is_horoscope(f1) and md5(f1) != md5(f2):
            print("C'est l'horoscope !")
            print("OCR : en cours.")
            horoscope_dict = parse_horoscope(f1)
            horoscope_str = reformat_horoscope(horoscope_dict)
            print("OCR : terminé.")
            await self.get_channel(channel_horoscope).send(file=discord.File(f1))
            await self.get_channel(channel_horoscope).send(horoscope_str)
            return True
        print("Ce n'est pas l'horoscope")
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
                hour=7,minute=0,second=0,microsecond=0)
        return next_monday-today

client = MyClient()
client.run(TOKEN)
