# coding: utf8
import discord
import asyncio
import datetime as dt
import os
import pytz
import pickle
from PIL import Image
from collections import Counter
import numpy as np

from typing import Optional, List

from my_constants import TOKEN, IMG_FOLDER, channel_horoscope
from scraper import get_last_images, download_image
from parse import parse_horoscope, reformat_horoscope
from utils import convert_timedelta, md5

import nest_asyncio
nest_asyncio.apply()


manual  = """
```Help
<@{id}> test  -- Récupère la dernière photo de RTL2 (horoscope ou pas)
<@{id}> last  -- Donne le dernier horoscope de RTL2
<@{id}> download  <URL> -- Télécharge l'image via l'URL donnée en argument et vérifie s'il s'agit de l'horoscope de RTL2
```
"""

tz_paris = pytz.timezone("Europe/Paris")
TIMESTAMP_FORMAT = "%Y-%m-%d"
USERNAME = "RTL2officiel"

# top,left,bottow,right
true_width, true_height = 2362, 3431
# True Horoscope has the following
# color proportions
true_occurences = Counter({1: 960179, 0: 750054, 2: 179367})
# Tested on a header of size true_width * crop_height
crop_height = 800
true_proportions = np.array([true_occurences[0], true_occurences[1], true_occurences[2]])/(true_width * crop_height)
rtl2_header = np.array([0, 0, true_width, crop_height])

kmeans = pickle.load(open("horoscope_kmeans.pickle", "rb"))

def now():
    return dt.datetime.now().astimezone(tz_paris)

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
    pixels = np.array(photo.crop(tuple(k*rtl2_header))).reshape(-1, 3)
    occurences = Counter(kmeans.predict(pixels))
    proportions = np.array([occurences[0], occurences[1], occurences[2]])/(k*true_width * k*crop_height)
    if verbose:
        print(proportions, "Image proportions")
        print(true_proportions, "True proportions")
        print(np.sum(np.abs(true_proportions - proportions)), "Distance")
    return np.sum(np.abs(true_proportions - proportions)) < 0.03



class HoroscopeDiscordBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.job())

    async def on_ready(self):
        """Initial check"""
        if not os.path.isdir(IMG_FOLDER):
            print(f"Création du dossier {IMG_FOLDER}")
            os.mkdir(IMG_FOLDER)

        print(f"[{now().ctime()}] - Bot ready :-)")
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    def is_for_bot(self, message) -> bool:
        """Check if the message is for the bot.
        Args:
            message: Discord message
        """
        return re.match(f"^<@!?{self.user.id}>", message.content)

    def command(self, message, cmd: str) -> str:
        """Check if the command match the one found in message.
        Args:
            message: Discord message
            cmd: command people sent
        """
        return re.match(f"^<@!?{self.user.id}> {cmd}", message.content)

    async def job(self, fetch_interval=300, days=[0,1,2,3,4], hours=[9,10,11,12]):
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
            today = now()

            while today.weekday() in days and today.hour in hours \
                and not await self.fetch_new_horoscope():
                # while (it's time to fetch horoscope) AND (the horoscope has not been published yet)
                # wait fetch_interval to not spam Twitter
                await asyncio.sleep(fetch_interval)

            time_to_wait = self.get_time_to_wait(hours).total_seconds()
            time_to_wait_message = f"[{now().ctime()}] - " +\
                f"Reprise de l'activité dans {time_to_wait} secondes."
            print(time_to_wait_message)

            await asyncio.sleep(time_to_wait)

    async def on_message(self, message):
        """Handle messages
        See help for features.
        """
        if message.author == client.user:
            return

        if self.command(message, "help"):
            await self.get_channel(channel_horoscope).send(manual.format(id=self.user.id))

        if self.command(message, "download"):
            img_href = message.content.split(" ")[-1]
            if img_href.startswith("http") and await self.fetch_new_horoscope(img_href=img_href):
                time_to_wait = self.get_time_to_wait([10,11,12]).total_seconds()
                time_to_wait_message = f"[{now().ctime()}] - " +\
                    f"Reprise de l'activité dans {time_to_wait} secondes."
                print(time_to_wait_message)
                await asyncio.sleep(time_to_wait)

        if self.command(message, "last"):
            files = sorted(os.listdir(IMG_FOLDER), reverse=True)
            if len(files) == 0:
                await self.get_channel(channel_horoscope).send("Aucun horoscope en stock :-(")
                return
            horoscope_img = IMG_FOLDER + "/" + files[0]
            await self.parse_and_send_horoscope(horoscope_img)

    async def parse_and_send_horoscope(self, filename):
        """Parse the image and send the image and the text found through OCR"""
        print("OCR : en cours.")
        horoscope_dict = parse_horoscope(filename, threads=1)
        horoscope_str = reformat_horoscope(horoscope_dict)
        print("OCR : terminé.")
        await self.get_channel(channel_horoscope).send(file=discord.File(filename))
        await self.get_channel(channel_horoscope).send(horoscope_str)

    async def fetch_new_horoscope(self, img_href: Optional[str] = None):
        """Get last image from RTL2 Twitter page, check if it's a new horoscope (using md5)
        and send the file on Discord
        Args:
            img_href : if not None, download the image from <img_href> url
        """

        print(f"[{now().ctime()}] - Fetch Horoscope")
        if img_href:
            print(f"[{now().ctime()}] - Lien fourni par l'utilisateur : {img_href}.")
            img_hrefs = [img_href]
        else:
            print(f"[{now().ctime()}] - Récupération des dernières images depuis Twitter.")
            today = now().strftime("%Y-%m-%d")
            img_hrefs = get_last_images(username=USERNAME, since=today)

        files = sorted(os.listdir(IMG_FOLDER + "/"), reverse=True)

        if len(img_hrefs) > 0:
            print("Téléchargement des images...")
        else:
            print("Pas d'images tweetées aujourd'hui !")

        for img_href in img_hrefs:
            filename = await download_image(img_href)

            new_image = IMG_FOLDER + "/" + files[0]

            if len(files) >= 1:
                old_image = IMG_FOLDER + "/" + files[1]
            else:
                old_image = ""

            print(f"Test de l'image {img_href}")
            if is_horoscope(new_image, verbose=True):
                print("C'est un horoscope !")
                if md5(new_image) == md5(old_image):
                    print("C'est l'horoscope d'hier")
                    # Stop research
                    return False
                else:
                    print("C'est l'horoscope du jour")
                    await self.parse_and_send_horoscope(new_image)
                    # Stop research
                    return True
            else:
                print("Ce n'est pas un nouveau horoscope")
                # Continue research

        return False

    def get_time_to_wait(self, hours):
        """How many time to wait before checking
        for a new horoscope ?
        """

        today = now()
        # Wait until tomorrow
        days_to_wait = 1
        if today.weekday() == 4:
            # it's Friday -> wait two more days
            days_to_wait += 2
        if today.weekday() == 5:
            # it's Saturday -> wait one more day
            days_to_wait += 1
        next_day = today.replace(hour=hours[0],minute=0,second=0,microsecond=0) + dt.timedelta(days=days_to_wait)
        return next_day-today

if __name__ == "__main__":
    client = HoroscopeDiscordBot()
    client.run(TOKEN)
