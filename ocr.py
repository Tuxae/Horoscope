import json
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat

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
    """
    if isinstance(img, str):
        img = Image.open(img)
    img.load()
    
    texts = read_texts(img, threads=threads, verbose=verbose)
    stars = find_star_colors(img)
    
    keys = texts.keys()
    values = zip(stars.values(), texts.values())
    out = dict(zip(keys, values))
    
    return out
