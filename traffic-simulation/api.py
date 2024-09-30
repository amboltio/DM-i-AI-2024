import uvicorn
from fastapi import FastAPI
import datetime
import time
from loguru import logger
from pydantic import BaseModel
from sim.dtos import TrafficSimulationPredictResponseDto, TrafficSimulationPredictRequestDto, SignalDto

HOST = "0.0.0.0"
PORT = 9051

app = FastAPI()
start_time = time.time()

@app.get('/api')
def hello():
    return {
        "service": "traffic-simulation-usecase",
        "uptime": '{}'.format(datetime.timedelta(seconds=time.time() - start_time))
    }

@app.get('/')
def index():
    return "Your endpoint is running!"

@app.post('/predict', response_model=TrafficSimulationPredictResponseDto)
def predict_endpoint(request: TrafficSimulationPredictRequestDto):

    # Decode request
    data = request
    vehicles = data.vehicles
    total_score = data.total_score
    simulation_ticks = data.simulation_ticks
    signals = data.signals
    signal_groups = data.signal_groups
    legs = data.legs
    allowed_green_signal_combinations = data.allowed_green_signal_combinations
    is_terminated = data.is_terminated
    

    logger.info(f'Number of vehicles at tick {simulation_ticks}: {len(vehicles)}')

    # Select a signal group to go green
    green_signal_group = signal_groups[0]

    

    # Return the encoded image to the validation/evalution service
    response = TrafficSimulationPredictResponseDto(
        signals=[SignalDto(
            name=green_signal_group,
            state="green"
        )]
        
    )

    return response

if __name__ == '__main__':

    uvicorn.run(
        'api:app',
        host=HOST,
        port=PORT
    )