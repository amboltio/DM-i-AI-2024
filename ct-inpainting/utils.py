
import numpy as np
import cv2
import base64 
from matplotlib import pyplot as plt
import matplotlib.patches as mpatches

def validate_reconstruction(ct_pred:np.ndarray):
    assert isinstance(ct_pred, np.ndarray), "Reconstruction was not succesfully decoded as a numpy array"
    assert ct_pred.shape == (256,256), f"Reconstruction of shape {ct_pred.shape} is not identical to expected shape (256,256)"
    assert np.max(ct_pred) <= 255 and (np.min(ct_pred) >= 0), f"The predicted CT image contains pixel values outside [0,255]. Only values within [0,255] are allowed."

def l1_score(y_true:np.ndarray, y_pred:np.ndarray):
    #Expects the tensors to have values in [0-255]
    y_true = y_true.astype("float")
    y_pred = y_pred.astype("float")
    return np.abs(y_true-y_pred).mean()

def encode_image(np_array: np.ndarray) -> str:
    # Encode the NumPy array as a png image
    success, encoded_img = cv2.imencode('.png', np_array)
    
    if not success:
        raise ValueError("Failed to encode the image")
    
    # Convert the encoded image to a base64 string
    base64_encoded_img = base64.b64encode(encoded_img.tobytes()).decode()
    
    return base64_encoded_img

def decode_request(request) -> np.ndarray:
    return {
        "corrupted_image":decode_image(request.corrupted_image),
        "tissue_image":decode_image(request.tissue_image),
        "mask_image":decode_image(request.mask_image),
        "vertebrae":request.vertebrae
    }

def decode_image(encoded_img) -> np.ndarray:
    np_img = np.fromstring(base64.b64decode(encoded_img), np.uint8)
    return cv2.imdecode(np_img, cv2.IMREAD_ANYCOLOR)

def load_sample(PATIENT_IX):
    ## Load example data
    corrupted_f = f"data/corrupted/corrupted_{PATIENT_IX}.png"
    tissue_f = f"data/tissue/tissue_{PATIENT_IX}.png"
    mask_f = f"data/mask/mask_{PATIENT_IX}.png"
    ct_f = f"data/ct/ct_{PATIENT_IX}.png"
    vertebrae_f = f"data/vertebrae/vertebrae_{PATIENT_IX}.txt"

    ## NOTE: loading with cv2.IMREAD_ANYCOLOR correctly ignores the color-channel. The resulting
    ## np.ndarray dimension will be (256, 256), which is what the evaluation server expects
    corrupted_image = cv2.imread(corrupted_f,cv2.IMREAD_ANYCOLOR)
    tissue_image = cv2.imread(tissue_f,cv2.IMREAD_ANYCOLOR)
    mask_image = cv2.imread(mask_f,cv2.IMREAD_ANYCOLOR)
    ct_image = cv2.imread(ct_f,cv2.IMREAD_ANYCOLOR)

    with open(vertebrae_f,"r") as handle:
        vertebrae = int(handle.read())

    return {
        "corrupted_image":corrupted_image,
        "tissue_image":tissue_image,
        "mask_image":mask_image,
        "ct_image":ct_image,
        "vertebrae":vertebrae,
    }

def plot_prediction(corrupted_image,tissue_image,mask_image,reconstruction,vertebrae,ct=None):

    if ct is None:
        ct = np.zeros_like(corrupted_image)
        err = np.zeros_like(corrupted_image)
    else:
        err = reconstruction.astype("float")-ct.astype("float")

    plt.figure(figsize=(15,2.5),dpi=300)
    plt.subplot(1,6,1)
    plt.imshow(corrupted_image,cmap="gray",vmin=0,vmax=255)
    plt.axis("off")
    plt.title(f"Corrupted CT, vertebrae {vertebrae}")

    plt.subplot(1,6,2)
    plt.imshow(mask_image,cmap="gray",vmin=0,vmax=255)
    plt.axis("off")
    plt.title("Mask")

    plt.subplot(1,6,3)
    plt.imshow(tissue_image,cmap="gray",vmin=0,vmax=255)
    plt.axis("off")
    plt.title("Tissue")

    plt.subplot(1,6,4)
    plt.imshow(reconstruction,cmap="gray",vmin=0,vmax=255)
    plt.axis("off")
    plt.title(f"Reconstruction")

    plt.subplot(1,6,5)
    plt.imshow(ct,cmap="gray",vmin=0,vmax=255)
    plt.axis("off")
    plt.title(f"CT")

    plt.subplot(1,6,6)
    plt.axis("off")
    plt.imshow(err,cmap="bwr",vmin=-50,vmax=50)
    plt.colorbar()
    plt.title(f"Error")

    plt.tight_layout()
    plt.savefig("inpainting_example.jpg")
    plt.show()
