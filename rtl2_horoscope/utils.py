import hashlib
import os
import datetime as dt
import pytz
from matplotlib import pyplot as plt
from matplotlib import patches
from PIL import Image
import numpy as np

tz_paris = pytz.timezone("Europe/Paris")

def log(message: str):
    print(f"[{now().ctime()}] - {message}")

def now():
    return dt.datetime.now().astimezone(tz_paris)

def disp_image_with_rectangle(path, coords):
    img = np.array(Image.open(path))
    fig, ax = plt.subplots(1)
    ax.imshow(img)
    rect = patches.Rectangle(
        (coords[0], coords[1]),
        coords[2]-coords[0],
        coords[3]-coords[1],
        linewidth=1,
        edgecolor='r',
        facecolor='none'
    )
    ax.add_patch(rect)
    plt.show()
    return fig, ax

def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return days, hours, minutes, seconds

#https://stackoverflow.com/a/3431838
def md5(fname):
    hash_md5 = hashlib.md5()
    if os.path.isfile(fname):
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    return None
