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

true_width, true_height = 1181, 1716

with open("regions.json", "r") as file:
    regions = json.load(file)


star_centers = {
    "bronze": [243.81, 181.88, 123.16],
    "argent": [190.07, 197.51 , 222.18],
    "or": [235.06, 205.52, 126.56],
}

ball_radius = 28

star_emojis = {
    "or": ":first_place:",
    "argent": ":second_place:",
    "bronze": ":third_place:",
}


def scale_regions(factor, regions=regions):
    """Scale all the star and text regions in a list of regions by a constant factor.
    
    Args:
        factor (float): Factor to scale by. Will round to the nearest integer.
        regions (list): List of regions in the format of regions.json.
            Default: regions.
    """
    out = []
    for d in regions:
        d = d.copy() # Don't modify the input in place
        for key in ["star", "text"]:
            d[key] = (np.array(d[key])*factor).tolist()
        out.append(d)
    
    return out


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


def read_texts(img, threads=12, regions=regions, verbose=True):
    """Read a horoscope image and return dict of read contents.
    
    Args:
        img (PIL.Image): Image to read.
        threads (int or None): Number of threads to use for multithreading.
            12 (number of text blocks to read) is empirically the fastest.
            Default: 12.
        regions (list): List of regions to use.
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
    

def find_star_colors(img, robust=True, regions=regions):
    """Parse a horoscope image and return dict of star colors.
    
    Args:
        img (PIL.Image): Image to read.
        robust (bool): Whether to use a more robust algorithm. With this enabled, processing time
            goes from 30ms to about 300ms, but errors are less frequent.
            Default: True.
        regions (list): List of regions to use.
    
    Returns:
        dict with zodiac signs as keys and text ("bronze", "argent" or "or") as values.
    """
    zodiac_signs = [region["name"] for region in regions]
    star_regions = [region["star"] for region in regions]
    
    # List containing the vector of pixels of each star region
    pixels = [
        np.array(img.crop(star)).reshape(-1, 3)
        for star in star_regions
    ]
    
    rng = range(31) if robust else [ball_radius]
    
    distances = [
        pd.DataFrame(
            {
                color_name: [
                    np.mean(
                        np.mean((px - center)**2, axis=-1)**(1/2)
                        >= ball_radius
                    )
                    for px in pixels
                ]
                for color_name, center in star_centers.items()
            },
            index = zodiac_signs
        )
        for ball_radius in rng
    ]
    
    guesses = pd.concat([df.idxmin(axis=1) for df in distances], axis=1)
    
    # Get min distance per row
    colors = guesses.mode(axis=1).squeeze().to_dict()
    
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
    
    # Rescale regions if necessary
    factor =  img.width/true_width
    print("scale factor:", factor)
    if factor != 1:
        scaled_regions = scale_regions(factor, regions)
    else:
        scaled_regions = regions
    
    # Read and clean up texts
    texts = read_texts(img, threads=threads, regions=scaled_regions, verbose=verbose)
    texts = {sign: clean_up_text(text) for sign, text in texts.items()}
    
    stars = find_star_colors(img, regions=scaled_regions, robust=True)
    
    keys = texts.keys()
    values = zip(stars.values(), texts.values())
    out = dict(zip(keys, values))
    
    return out


def reformat_horoscope(horoscope_dict):
    """Reformat the horoscope dictionary into a string which displays well as a discord message.
    
    Args:
        horoscope_dict (dict): Horoscope as a {sign:(star, text)} dictionary.
    
    Returns:
        str: Sendable message.
    """
    def gen_bullet_point(sign, star, text):
        emoji = star_emojis[star]
        return f"- **{sign.title()}** {emoji}: {text}"
    
    bullet_points = [
        gen_bullet_point(sign, star, text)
        for sign, (star, text) in horoscope_dict.items()
    ]
    
    message = "\n".join(bullet_points)
    
    return message
