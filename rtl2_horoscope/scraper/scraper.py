import io
import pickle
import datetime
import aiohttp
import asyncio

from typing import Optional, List
from collections import Counter
from pathlib import Path
from PIL import Image

import numpy as np

from my_constants import IMG_FOLDER
from doctr.models import ocr_predictor
from rtl2_horoscope.utils import log, now

# top,left,bottow,right
true_width, true_height = 2362, 3431
# True Horoscope has the following
# color proportions
true_occurences = Counter({1: 960179, 0: 750054, 2: 179367})
# Tested on a header of size true_width * crop_height
crop_height = 800
true_proportions = np.array([true_occurences[0], true_occurences[1], true_occurences[2]])/(true_width * crop_height)
rtl2_header = np.array([0, 0, true_width, crop_height])

days = {
    "monday": "lundi",
    "tuesday": "mardi",
    "wednesday": "mercredi",
    "thursday": "jeudi",
    "friday": "vendredi",
    "saturday": "samedi",
    "sunday": "dimanche",
}

kmeans = pickle.load(open("horoscope_kmeans.pickle", "rb"))


class Scraper:

    def __init__(self, social_media):
        self.social_media = social_media
        self.model = ocr_predictor(pretrained=True)

    def is_horoscope(self, fp, verbose=False):
        """Check if it is a horoscope or not
        Step 1 : check the picture size
        Step 2 : use pretrained KMeans to compare color proporitons

        Args:
            fp (str, pathlib.Path or a file object) : path to horoscope

        Return:
            Bool : return True if it is an horoscope, False otherwise
        """
        # Step 1
        photo = Image.open(fp)
        width, height = photo.size

        log(f"Image size : {width}x{height}")
        if abs(width/true_width - height/true_height) > 0.05 :
            return False
        log(f"Ratio de l'image correct.")

        # Step 2
        k = width/true_width
        pixels = np.array(photo.crop(tuple(k*rtl2_header))).reshape(-1, 3)
        occurences = Counter(kmeans.predict(pixels))
        proportions = np.array([occurences[0], occurences[1], occurences[2]])/(k*true_width * k*crop_height)
        if verbose:
            log(f"Image proportions: {proportions}")
            log(f"True proportions: {true_proportions}")
            log(f"Distance: {np.sum(np.abs(true_proportions - proportions))}")
        return np.sum(np.abs(true_proportions - proportions)) < 0.05

    def is_horoscope_of_the_day(self, image) -> bool:

        img = np.array(Image.open(image))
        excerpt = self.model([img]).render().lower()[:300]

        today = now()
        quantum = today.strftime("%d")
        day = days[today.strftime("%A").lower()]

        return (day in excerpt or quantum in excerpt)

    def get_last_images(self, **kwargs) -> List[str]:
        """Function to get images hrefs from Social Media"""
        raise NotImplementedError

    async def fetch_new_horoscope(self, img_href: Optional[str] = None, **kwargs) -> str:
        """
        1) Get last image from RTL2 social media,
        2) check if it's a new horoscope using md5
        3) and send the file on Discord
        Args:
            img_href : if not None, download the image from <img_href> url
            kwargs: optional kwargs pass to get_last_images function

        Returns:
            Path to Horoscope image on Disk
        """

        log("Fetch Horoscope")
        if img_href:
            log(f"Lien fourni par l'utilisateur : {img_href}.")
            img_hrefs = [img_href]
        else:
            log(f"Récupération des dernières images depuis {self.social_media.title()}.")
            today = now().strftime("%Y-%m-%d")
            img_hrefs = self.get_last_images(**kwargs)

        if len(img_hrefs) > 0:
            log("Téléchargement des images...")
        else:
            log("Pas d'images aujourd'hui !")

        for img_href in img_hrefs:
            image = await self.download_image(img_href)

            if not image:
                # Got problem with this img_href
                # Skip it
                continue

            log(f"Test de l'image {img_href}")
            if self.is_horoscope(image, verbose=True):
                log("C'est un horoscope !")
                if self.is_horoscope_of_the_day(image):
                    log("C'est l'horoscope du jour")
                    # Stop research
                    filename = Path(IMG_FOLDER) / ( now().strftime("%Y-%m-%d") + ".jpg")
                    with open(filename, "wb") as f:
                        f.write(image.getbuffer())
                    return filename
                else:
                    log("Ce n'est pas l'horoscope du jour")
            else:
                log("Ce n'est pas un nouveau horoscope")
                # Continue research
                await asyncio.sleep(1)

        return ''


    async def download_image(self, url: str, filename: Optional[str] = None):
        """Download image from `url` and save it as JPEG.

        Args:
            url (str) : URL to get the img
            filename (str) : if provided, save the image as `filename`.
                Otherwise, use timestamp as filename

        Return:
            Str : saved file name
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.read()
                return io.BytesIO(data)
