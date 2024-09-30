import uvicorn
from fastapi import FastAPI
import datetime
import time
from model import predict
from loguru import logger
from pydantic import BaseModel
from typing import List
from utils import load_sample

HOST = "0.0.0.0"
PORT = 4321

# Images are loaded via cv2, encoded via base64 and sent as strings
# See utils.py for details
class CellClassificationPredictRequestDto(BaseModel):
    cell: str

class CellClassificationPredictResponseDto(BaseModel):
    is_homogenous: int

app = FastAPI()
start_time = time.time()

@app.get('/api')
def hello():
    return {
        "service": "cell-segmentation-usecase",
        "uptime": '{}'.format(datetime.timedelta(seconds=time.time() - start_time))
    }

@app.get('/')
def index():
    return "Your endpoint is running!"

@app.post('/predict', response_model=CellClassificationPredictResponseDto)
def predict_endpoint(request: CellClassificationPredictRequestDto):

    # Decode request
    image_id = load_sample(request.cell)

    predicted_homogenous_state = predict(image_id)
    
    # Return the encoded image to the validation/evalution service
    response = CellClassificationPredictResponseDto(
        is_homogenous=predicted_homogenous_state
    )
    
    return response

if __name__ == '__main__':

    uvicorn.run(
        'api:app',
        host=HOST,
        port=PORT
    )