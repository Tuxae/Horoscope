import json
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
import re

import pandas as pd
pd.options.mode.chained_assignment = None
import numpy as np
from tqdm import tqdm

import pytesseract
from PIL import Image

with open("regions.json", "r") as file:
    regions = json.load(file)


star_centers = {
    "bronze": [243.81, 181.88, 123.16],
    "argent": [190.07, 197.51 , 222.18],
    "or": [235.06, 205.52, 126.56],
}


def read_crop(img, crop_region=None, pb=None):
    """Use Tesseract OCR to extract the text at given coordinates in the given image.
    
    Args:
        img (PIL.Image): Image to read from.
        crop_region (tuple of ints): Coordinates of the rectangle containing the text to read.
    
    Returns:
        str: The text as read by Tesseract.
    """
    if crop_region is None:
        crop_region = (0, 0, img.width, img.height)
    
    crop = img.crop(crop_region)
    
    # Perform OCR
    text = pytesseract.image_to_string(
        crop,
        # lang="eng",
        config=(
            ""
            + "-l fra "
            # + '--tessdata-dir "C:/Program Files/Tesseract-OCR/tessdata_bkp" '
            + "--psm 6 "
        )
    )
    
    text = text.replace("\n", " ")
    
    if pb is not None:
        pb.update()
    
    return text


def read_texts(img, threads=12, verbose=True):
    """Read a horoscope image and return dict of read contents.
    
    Args:
        img (PIL.Image): Image to read.
        threads (int or None): Number of threads to use for multithreading.
            12 (number of text blocks to read) is empirically the fastest.
            Default: 12.
        verbose (bool): Whether to display a progressbar.
            Default: True.
    
    Returns:
        dict with zodiac signs as keys and text as values.
    """
    zodiac_signs = [region["name"] for region in regions]
    text_regions = [region["text"] for region in regions]
    n = len(text_regions)
    
    pb = tqdm(total=n, desc="Reading horoscope", disable=not verbose)
    
    if threads > 1:
        with ThreadPoolExecutor(threads) as pool:
            texts = list(pool.map(
                read_crop,
                repeat(img, n),
                text_regions,
                repeat(pb, n),
            ))
    
    else:
        texts = [read_crop(img, reg, pb) for reg in text_regions]
    
    pb.close()
    
    return dict(zip(zodiac_signs, texts))


def clean_up_text(text):
    """Clean up a text string read by the OCR engine.
    
    Args:
        text (str): Raw text produced by OCR.
    
    Returns:
        str: Cleaned up text.
    """
    # Take care of most problems with a char whitelist.
    acceptable_chars_regex = r"[\w ',\!\?\.]"
    text = "".join(re.findall(acceptable_chars_regex, text))
    
    # Take care of underscores and issues with spaces.
    text = text.replace("_", "").replace("  ", " ").strip()
    
    return text
    

def find_star_colors(img):
    """Parse a horoscope image and return dict of star colors.
    
    Args:
        img (PIL.Image): Image to read.
    
    Returns:
        dict with zodiac signs as keys and text ("bronze", "argent" or "or") as values.
    """
    zodiac_signs = [region["name"] for region in regions]
    star_regions = [region["star"] for region in regions]
    
    # Array of shape (12, 3) containing the RGB mean of each star region
    means = np.array([
        (
            np.array(img.crop(star))
            .reshape(-1, 3)
            .mean(axis=0)
        )
        for star in star_regions
    ])
    
    # DataFrame with zodiac signs as index, color names as columns and mean-square distance as values.
    distances = pd.DataFrame(
        {
            color_name: np.mean(
                (means - np.array(center))**2,
                axis=1
            )
            for color_name, center in star_centers.items()
        },
        index = zodiac_signs
    )
    
    # Get min distance per row
    colors = distances.idxmin(axis=1).to_dict()
    
    return colors


def parse_horoscope(img, threads=12, verbose=True):
    """Parse texts and stars in a horoscope image and return info as a dict.
    
    Args:
        img (PIL.Image or str): Image to read or path to image.
        threads (int or None): Number of threads to use for reading blocks of text.
            12 (number of text blocks to read) is empirically the fastest.
            Default: 12.
        verbose (bool): Whether to display a progressbar.
            Default: True.
    
    Returns:
        dict with zodiac signs as keys and (star_color, text) tuples as values.
    
    Example:
        >>> parse_horoscope("examples/photo103.jpg", threads=1, verbose=False)
        {'belier': ('argent',
          'Votre journée sera rythmée par des bonnes nouvelles les béliers.'),
         'taureau': ('argent',
          'Votre enthousiasme est très apprécié par votre hiérarchie, vous vous démarquez des autres.'),
         'gemeaux': ('bronze',
          'Vous n‘êtes pas dans votre assiette les gémeaux. Ca ira mieux demain.'),
         'cancer': ('argent',
          'Prenez un instant pour vous ! Un peu de détente vous fera le plus grand bien.'),
         'lion': ('argent',
          'Votre tempérament de leader vous ménera loin les lions, on vous fait confiance.'),
         'vierge': ('argent',
          'Vous avez bonne mine et on vous le dit. De quoi retrouver le sourire.'),
         'balance': ('argent',
          'Votre entourage est aux petits soins pour vous ! Vous avez de la chance les balances.'),
         'scorpion': ('or',
          'Votre bienveillance  et votre belle énergie plaisent ! Vous êtes  LA personne avec qui on veut passer du temp:'),
         'sagittaire': ('bronze',
          'Vous prenez tout  par dessus la jambe.  1l est temps de vous impliquer beaucoup plus !'),
         'capricorne': ('argent',
          'Votre persévérance porte ses fruits. Vous devenez incroyable.'),
         'verseau': ('argent',
          'Le moment est venu de vous lancer dans les projets que vous laissiez de côté depuis un moment.'),
         'poisson': ('bronze',
          'Votre corps réclame une pause, ne tirez \\pas trop sur la corde.')}
    """
    if isinstance(img, str):
        img = Image.open(img)
    img.load()
    
    # Read and clean up texts
    texts = read_texts(img, threads=threads, verbose=verbose)
    texts = {sign: clean_up_text(text) for sign, text in texts.items()}
    
    stars = find_star_colors(img)
    
    keys = texts.keys()
    values = zip(stars.values(), texts.values())
    out = dict(zip(keys, values))
    
    return out
