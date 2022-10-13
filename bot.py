# coding: utf8
import discord
import logging
import asyncio
import re
import os
import pickle
import datetime as dt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

from PIL import Image
from typing import Optional, List

from my_constants import TOKEN, IMG_FOLDER, channel_horoscope
from rtl2_horoscope.scraper.facebook import FacebookScraper
from rtl2_horoscope.parse import parse_horoscope, reformat_horoscope
from rtl2_horoscope.utils import now

#import nest_asyncio
#nest_asyncio.apply()


manual  = """
```Help
<@{id}> test  -- Récupère la dernière photo de RTL2 (horoscope ou pas)
<@{id}> last  -- Donne le dernier horoscope de RTL2
<@{id}> download  <URL> -- Télécharge l'image via l'URL donnée en argument et vérifie s'il s'agit de l'horoscope de RTL2
```
"""

TIMESTAMP_FORMAT = "%Y-%m-%d"


class HoroscopeDiscordBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scraper = FacebookScraper()

    async def setup_hook(self):
        # create the background task and run it in the background
        self.loop.create_task(self.job())

    async def on_ready(self):
        """Initial check"""
        if not os.path.isdir(IMG_FOLDER):
            logging.info(f"Création du dossier {IMG_FOLDER}")
            os.mkdir(IMG_FOLDER)

        logging.info("Bot ready :-)")
        logging.info('Logged in as')
        logging.info(self.user.name)
        logging.info(self.user.id)
        logging.info('------')

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
            time_to_wait_message = f"Reprise de l'activité dans {time_to_wait} secondes."
            logging.info(time_to_wait_message)

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
                time_to_wait_message = f"Reprise de l'activité dans {time_to_wait} secondes."
                logging.info(time_to_wait_message)
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
        logging.info("OCR : en cours.")
        horoscope_dict = parse_horoscope(filename, threads=1)
        horoscope_str = reformat_horoscope(horoscope_dict)
        logging.info("OCR : terminé.")
        await self.get_channel(channel_horoscope).send(file=discord.File(filename))
        await self.get_channel(channel_horoscope).send(horoscope_str)

    async def fetch_new_horoscope(self, img_href: Optional[str] = None) -> bool:
        """Get last image from RTL2 social media page, check if it's a new horoscope
        and send the file on Discord
        Args:
            img_href : if not None, download the image from <img_href> url
        """
        horoscope = await self.scraper.fetch_new_horoscope(img_href)
        if horoscope:
            await self.parse_and_send_horoscope(horoscope)
            return True
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
    intents = discord.Intents.default()
    intents.message_content = True
    client = HoroscopeDiscordBot(intents=intents)
    client.run(TOKEN)
