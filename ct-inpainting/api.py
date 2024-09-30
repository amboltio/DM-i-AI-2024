import uvicorn
from fastapi import FastAPI
import datetime
import time
from utils import validate_reconstruction, encode_image, decode_request
from model import predict
from loguru import logger
from pydantic import BaseModel

HOST = "0.0.0.0"
PORT = 9050

# Images are loaded via cv2, encoded via base64 and sent as strings
# See utils.py for details
class InpaintingPredictRequestDto(BaseModel):
    corrupted_image: str 
    tissue_image: str
    mask_image: str
    vertebrae: int

class InpaintingPredictResponseDto(BaseModel):
    reconstructed_image: str

app = FastAPI()
start_time = time.time()

@app.get('/api')
def hello():
    return {
        "service": "ct-inpainting-usecase",
        "uptime": '{}'.format(datetime.timedelta(seconds=time.time() - start_time))
    }

@app.get('/')
def index():
    return "Your endpoint is running!"

@app.post('/predict', response_model=InpaintingPredictResponseDto)
def predict_endpoint(request: InpaintingPredictRequestDto):

    # Decode request
    data:dict = decode_request(request)
    corrupted_image = data["corrupted_image"]
    tissue_image = data["tissue_image"]
    mask_image = data["mask_image"]
    vertebrae = data["vertebrae"]

    logger.info(f'Recieved images: {corrupted_image.shape}')

    # Obtain reconstruction prediction
    reconstructed_image = predict(corrupted_image,tissue_image,mask_image,vertebrae)

    # Validate image format
    validate_reconstruction(reconstructed_image)

    # Encode the image array to a str
    encoded_reconstruction = encode_image(reconstructed_image)

    # Return the encoded image to the validation/evalution service
    response = InpaintingPredictResponseDto(
        reconstructed_image=encoded_reconstruction
    )
    logger.info(f'Returning reconstruction: {reconstructed_image.shape}')
    return response

if __name__ == '__main__':

    uvicorn.run(
        'api:app',
        host=HOST,
        port=PORT
    )