import twint
import datetime
import io
import aiohttp
import requests

from typing import Optional, List

def get_last_images(username: str, since: Optional[str] = None) -> List[str]:
    """Retrieve images from a twitter account"""
    c = twint.Config()
    c.Username = username
    c.Store_object = True

    if since:
        c.Since = since

    twint.run.Search(c)

    image_hrefs = []

    for tweet in twint.output.tweets_list:
        image_hrefs += tweet.photos

    return image_hrefs

async def download_image(url: str, filename: Optional[str] = None):
    """Download image from `url` and save it as JPEG.

    Args:
        url (str) : URL to get the img
        filename (str) : if provided, save the image as `filename`.
            Ohterwise, use timestamp as filename

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
