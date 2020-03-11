from matplotlib import pyplot as plt
from matplotlib import patches
from PIL import Image
import numpy as np

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
