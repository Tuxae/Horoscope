from bs4 import BeautifulSoup
import pickle
from PIL import Image
from collections import Counter
import numpy as np

import requests
import re

album_URL = "https://www.facebook.com/pg/rtl2/photos/?tab=album&album_id=248389291078&ref=page_internal"
mobile_URL = "https://mobile.facebook.com/rtl2/photos/a.248389291078/"
get_original_image = "Afficher en taille réelle"

firstPhotoID_re = re.compile(r'"firstPhotoID":"([0-9]*)"')
number_re = re.compile(r'\d+')

rtl2_header_coord = (0, 0, 661, 140)

kmeans = pickle.load(open("horoscope_kmeans.pickle", "rb"))

def is_horoscope(filename):
    """Use pretrained KMeans to test if it's an
    horoscope or not

    Output:
        Bool : return True if it is an horoscope, False otherwise
    """
    try:
        total_pixels = 661*140
        photo = Image.open(filename)
        pixels = np.array(photo.crop(rtl2_header_coord).getdata())
        occurences = Counter(kmeans.predict(pixels))
        # True Horoscope has the following value
        # Counter({0: 41976, 1: 41676, 2: 8888})
        true_prop   = np.array([41976, 41676, 8888])/total_pixels
        proportions = np.array([occ for occ in occurences.values()])/total_pixels
        return np.abs(np.sum(true_prop - proportions)) < 0.03
    except:
        print("File not accessible")

def get_last_image(album_URL = album_URL):
    """ Get the last published image from
    a Facebook album URL
    Input:
        album_URL (str) : the URL to get the last image
    Output:
        str : url of the image. Empty string if there is an error
    """

    nbr = 0
    r = requests.get(album_URL)
    href = ""

    if r.status_code == 200:
        # return the first (group(0)) matched 
        # string with regex
        s = firstPhotoID_re.search(r.text).group(0)
        # extract the number from the string s
        nbr = number_re.search(s).group(0)

    if nbr != 0:
        r = requests.get(mobile_URL+str(nbr))
        if r.status_code == 200:
            soup = BeautifulSoup(r.text)
            href = soup.find_all("a", text=get_original_image)[0].get("href")
    return href
