# coding: utf8
import discord
from discord.ext import commands
import asyncio
import aiohttp
import datetime as dt
import hashlib
import os

from my_constants import TOKEN, IMG_FOLDER, channel_horoscope
from scraper import get_last_image, download_image
from parse import parse_horoscope, reformat_horoscope
from utils import convert_timedelta, md5


import pickle
from PIL import Image
from collections import Counter
import numpy as np

manual  = """
```Help
<@!{id}> test  -- Récupère la dernière photo de RTL2 (horoscope ou pas)
<@!{id}> last  -- Donne le dernier horoscope de RTL2
<@!{id}> download  <URL> -- Télécharge l'image via l'URL donnée en argument et vérifie s'il s'agit de l'horoscope de RTL2
```
"""

# top,left,bottow,right
true_width, true_height = 1181, 1716
# True Horoscope has the following
# color proportions
#Counter({0: 134576, 1: 132231, 2: 28443})
# Tested on a header of size 1181*250
crop_height = 250
true_prop   = np.array([134576, 132231, 28443])/(true_width * crop_height)
rtl2_header = np.array([0, 0, 1181, 250])

kmeans = pickle.load(open("horoscope_kmeans.pickle", "rb"))

def is_horoscope(filename, verbose=False):
    """Check if it is a horoscope or not
    Step 1 : check the picture size
    Step 2 : use pretrained KMeans to compare color proporitons

    Args:
        filename (str) : path to horoscope

    Return:
        Bool : return True if it is an horoscope, False otherwise
    """
    assert os.path.isfile(filename), "Invalid file name"

    # Step 1
    photo = Image.open(filename)
    width, height = photo.size

    print(f"Image size : {width}x{height}")
    if abs(width/true_width - height/true_height) > 0.05 :
        return False
    print(f"Ratio de l'image correct.")

    # Step 2
    k = width/true_width
    pixels = np.array(photo.crop(tuple(k*rtl2_header)).getdata())
    occurences = Counter(kmeans.predict(pixels))
    proportions = np.array([occ for occ in occurences.values()])/(k*true_width * k*crop_height)
    if verbose:
        print(proportions, "Image proportions")
        print(true_prop, "True proportions")
        print(np.sum(np.abs(true_prop - proportions)), "Distance")
    return np.sum(np.abs(true_prop - proportions)) < 0.03



class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.job())

    async def on_ready(self):
        """Initial check"""
        if not os.path.isdir(IMG_FOLDER):
            print(f"Création du dossier {IMG_FOLDER}")
            os.mkdir(IMG_FOLDER)

        print("[" + dt.datetime.now().ctime() + "] - Bot ready :-)")
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def job(self, fetch_interval=300, days=[0,1,2,3,4], hours=[9,10,11]):
        """ Job to run evey `fetch_interval` seconds,
        each day in days, between hours
        Args:
            fetch_interval (int) : run job every `fetch_interval` seconds
            days (list of int): day to fetch horoscope
            hours (list of hour) : (whole) hour to fetch horoscope

        Example : job(300, [0,1,3,4], [7,8,10,12,13]):
        Run the job on Monday, Tuesday, Thursday and Friday, between 7 and 8 hours
        and between 10 and 13 hours.
        """
        await self.wait_until_ready()

        assert max(days) <= 6, "Need number between 0 and 6"
        assert min(days) >= 0, "Need number between 0 and 6"

        assert max(hours) <= 23, "Need number between 0 and 23"
        assert min(hours) >= 0, "Need number between 0 and 23"

        while not self.is_closed():
            today = dt.datetime.today()
            while today.weekday() in days and today.hour in hours and not await self.fetch_new_horoscope():
                # while (it's time to fetch horoscope) AND (the horoscope has not been published yet)
                # wait fetch_interval to not spam Facebook
                await asyncio.sleep(fetch_interval)
            time_to_wait = self.get_time_to_wait(hours).total_seconds()
            print("[" + dt.datetime.now().ctime() + "] - " + f"Reprise de l'activité dans {time_to_wait} secondes.")
            await asyncio.sleep(time_to_wait)

    def command(self, cmd):
        """Wrapper for bot prefix"""
        return f"<@!{self.user.id}> " + str(cmd)

    async def on_message(self, message):
        """Handle messages
        See help for features.
        """
        if message.author == client.user:
            return

        if message.content == self.command("help"):
            await self.get_channel(channel_horoscope).send(manual.format(id=self.user.id))

        if message.content == self.command("test"):
            await self.fetch_new_horoscope(force=True)

        if message.content.startswith(self.command("download")):
            img_href = message.content.split(" ")[-1]
            if img_href.startswith("http") and await self.fetch_new_horoscope(img_href=img_href):
                time_to_wait = self.get_time_to_wait([9,10,11]).total_seconds()
                print("[" + dt.datetime.now().ctime() + "] - " + f"Reprise de l'activité dans {time_to_wait} secondes.")
                await asyncio.sleep(time_to_wait)

        if message.content == self.command("last"):
            files = sorted(os.listdir(IMG_FOLDER), reverse=True)
            if len(files) == 0:
                await self.get_channel(channel_horoscope).send("Aucun horoscope en stock :-(")
                return
            horoscope_img = IMG_FOLDER + "/" + files[0]
            await self.parse_and_send_horoscope(horoscope_img)

    async def parse_and_send_horoscope(self, filename):
        """Parse the image and send the image and the text
        found through OCR
        """
        print("OCR : en cours.")
        horoscope_dict = parse_horoscope(filename)
        horoscope_str = reformat_horoscope(horoscope_dict)
        print("OCR : terminé.")
        await self.get_channel(channel_horoscope).send(file=discord.File(filename))
        await self.get_channel(channel_horoscope).send(horoscope_str)

    async def fetch_new_horoscope(self, img_href=None, force=False):
        """Get last image from RTL2 Facebook page,
        check if it's a new horoscope (using md5)
        and send the file on Discord
        Args:
            img_href (str) : if not None, download the image
                           from <img_href> url
            force (bool) : if True, download the last image
                           and send it as it is
        """

        print("[" + dt.datetime.now().ctime() + "] - Fetch Horoscope")
        if not img_href:
            print("Récupération du dernier lien.")
            img_href = await get_last_image()
            print("Téléchargement de l'image...")

        if force:
            filename = await download_image(img_href, filename=IMG_FOLDER + "/" + "9999-99-99_test.jpg")
            await self.get_channel(channel_horoscope).send(file=discord.File(filename))
            return True

        filename = await download_image(img_href)
        files = sorted(os.listdir(IMG_FOLDER + "/"), reverse=True)

        f1 = IMG_FOLDER + "/" + files[0]
        f2 = ""

        if len(files) >= 1:
            f2 = IMG_FOLDER + "/" + files[1]

        print("Test de l'image : est-ce l'horoscope ?")
        if is_horoscope(f1) and (md5(f1) != md5(f2)):
            print("C'est l'horoscope !")
            await self.parse_and_send_horoscope(f1)
            return True
        print("Ce n'est pas l'horoscope")
        return False

    def get_time_to_wait(self, hours):
        """How many time to wait before checking
        for a new horoscope ?
        """

        today = dt.datetime.today()
        # Wait until tomorrow
        days_to_wait = 1
        if today.weekday() == 4:
            # it's Friday -> wait two more days
            days_to_wait += 2
        next_day = today.replace(hour=hours[0],minute=0,second=0,microsecond=0) + dt.timedelta(days=days_to_wait)
        return next_day-today

if __name__ == "__main__":
    client = MyClient()
    client.run(TOKEN)
