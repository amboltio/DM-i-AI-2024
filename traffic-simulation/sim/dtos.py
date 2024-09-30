from typing import List
from pydantic import BaseModel

class VehicleDto(BaseModel):
    speed: float
    distance_to_stop: float
    leg: str

class SignalDto(BaseModel):
    name: str
    state: str

class LegDto(BaseModel):
    name: str
    lanes: List[str]
    signal_groups: List[str]

class AllowedGreenSignalCombinationDto(BaseModel):
    name: str
    groups: List[str]

class TrafficSimulationPredictRequestDto(BaseModel):
    vehicles: List[VehicleDto]
    total_score: float
    simulation_ticks: int
    signals: List[SignalDto]
    signal_groups: List[str]
    legs: List[LegDto]
    allowed_green_signal_combinations: List[AllowedGreenSignalCombinationDto]
    is_terminated: bool

    class Config:
        arbitrary_types_allowed = True


class TrafficSimulationPredictResponseDto(BaseModel):
    signals: List[SignalDto]

    class Config:
        arbitrary_types_allowed = True

