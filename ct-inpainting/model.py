import numpy as np

### CALL YOUR CUSTOM MODEL VIA THIS FUNCTION ###
def predict(corrupted_image,tissue_image,mask_image,vertebrae) -> np.ndarray:
    reconstruction = fill_tissue(
        corrupted_image,
        tissue_image,
        mask_image,
        fill_value=84)
    return reconstruction

### DUMMY MODEL ###
def fill_tissue(corrupted_image:np.ndarray, 
                tissue_image:np.ndarray,
                mask_image:np.ndarray,
                fill_value:int) -> np.ndarray:
    """
    Simple model that fills the body mask with fill_value
    """
    reconstruced_image = corrupted_image.astype(float)
    fill_mask = (tissue_image>0) & (mask_image>0)
    reconstruced_image[fill_mask] = fill_value
    return reconstruced_image
