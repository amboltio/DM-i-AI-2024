import numpy as np
import cv2
import base64 

def decode_image(encoded_img) -> np.ndarray:
    np_img = np.fromstring(base64.b64decode(encoded_img), np.uint8)
    return cv2.imdecode(np_img, cv2.IMREAD_ANYCOLOR)


def tif_to_ndarray(tif_path):
    img_array = cv2.imread(tif_path, cv2.IMREAD_UNCHANGED)
    return img_array



# There was an attempt. Unsure if this works w opencv and tif
def load_sample(enc_img: np.ndarray):
    image = decode_image(enc_img)  # For decoding validation and evaluation files
    return {
        "image":image
    }
