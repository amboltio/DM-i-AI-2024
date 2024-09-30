from utils import tif_to_ndarray
from model import predict

CELL_IMG = "data/training/007.tif" 

image = tif_to_ndarray(CELL_IMG) # For local testing with tif files
sample_prediction = predict(image)
print(sample_prediction)