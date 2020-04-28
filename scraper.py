import datetime
import io
import aiohttp
import requests
import re
import pickle
import numpy as np

from bs4 import BeautifulSoup
from PIL import Image
from collections import Counter


album_url = "https://www.facebook.com/pg/rtl2/photos/?tab=album&album_id=248389291078&ref=page_internal"
mobile_url = "https://mobile.facebook.com/rtl2/photos/a.248389291078/"
get_original_image = "Afficher en taille réelle"

firstPhotoID_re = re.compile(r'"firstPhotoID":"([0-9]*)"')
number_re = re.compile(r'\d+')


async def get_last_image(album_url = album_url):
    """ Get the last published image from
    a Facebook album url

    Args:
        album_url (str) : the url to get the last image
    Return:
        Str : empty string if an error occured. URL of the img otherwise
    """

    nbr = 0
    href = ""
    
    async with aiohttp.ClientSession() as session:
        async with session.get(album_url) as r:
            if r.status != 200:
                return None

            # return the first (group(0)) matched 
            # string with regex
            s = firstPhotoID_re.search(await r.text()).group(0)
            # extract the number from the string s
            nbr = number_re.search(s).group(0)
        
            if nbr == 0:
                return None
        
    async with aiohttp.ClientSession() as session:
        async with session.get(mobile_url + str(nbr)) as r:
            if r.status != 200:
                return None
            soup = BeautifulSoup(await r.text(), features="lxml")
            href = soup.find_all("a", text=get_original_image)[0].get("href")
            print(href)
            return href

async def download_image(url, filename=""):
    """Download image from `url` and save
    the file in JPEG.

    Args:
        url (str) : URL to get the img
        filename (str) : save with the provided filename, use timestamp otherwise

    Return:
        Str : saved file name
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status != 200:
                return None
            if not filename:
                now = datetime.datetime.now()
                filename = "images/" + now.strftime("%Y-%m-%d") + ".jpg"
            with open(filename, "wb") as f:
                f.write(await r.read())
            return filename
