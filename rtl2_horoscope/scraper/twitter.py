import twint

from typing import Optional, List

from rtl2_horoscope.scraper import Scraper

USERNAME = "RTL2officiel"

class TwitterScraper(Scraper):

    def __init__(self, username: str = USERNAME):
        super().__init__(social_media="twitter")
        self.username = username

    def get_last_images(self, since: Optional[str] = None, **kwargs) -> List[str]:
        """Retrieve images from a twitter account"""
        c = twint.Config()
        c.Username = self.username
        c.Store_object = True
        c.Hide_output = True

        if since:
            c.Since = since

        twint.run.Search(c)

        image_hrefs = []

        for tweet in twint.output.tweets_list:
            image_hrefs += tweet.photos

        return image_hrefs

