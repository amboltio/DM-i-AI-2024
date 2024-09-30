
from time import time
from time import sleep
from uuid import uuid4
import threading

from sumolib import checkBinary  # noqa
import traci  # noqa

import os
import sys
from multiprocessing import Queue
import yaml
import pathlib

from loguru import logger

from dtos import (
    TrafficSimulationPredictRequestDto, VehicleDto, SignalDto, LegDto, AllowedGreenSignalCombinationDto
)

def load_configuration(configuration_file, start_time, test_duration_seconds):

    model_folder = pathlib.Path(configuration_file).parent

    with open(configuration_file, 'r') as cfile:
        configuration = yaml.safe_load(cfile)


    for intersection in configuration['intersections']:
        connections = []
        signal_groups = []
        legs = {}

        for group in intersection['groups']:
            signal_groups.append(group)

        for leg in intersection['legs']:
            l = {}
            l['name'] = leg['name']
            l['lanes'] = leg['lanes']
            l['radar'] = leg['radar']
            l['groups'] = leg['groups']
            l['segments'] = leg['segments']

            legs[leg['name']] = l

        for connection in intersection['connections']:
            connections.append(Connection(
                connection['index'],
                connection['groups'],
                connection['priority']
            ))

        env = TrafficSimulationEnvHandler(start_time, 
                                        test_duration_seconds,
                                        model_folder,
                                        intersection['groups'],
                                        connections,
                                        intersection['junction'],
                                        signal_groups,
                                        legs,
                                        allowed_green_signal_combinations=intersection['allowed_green_signal_combinations'],
                                        amber_time=4,
                                        red_amber_time=2,
                                        min_green_time=6)

        return env
        
    return None

def load_and_run_simulation(configuration_file, start_time, test_duration_seconds, random_state, input_q, output_q, error_q):
    env = load_configuration(configuration_file, start_time, test_duration_seconds)
    env.set_queues(input_q, output_q, error_q)

    env.set_random_state(random_state)
    env.run_simulation()
    return env.get_observable_state()

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)

lock = threading.Lock()

class Connection:
    def __init__(self, number, groups, priority):
        self.number = number
        self.groups = groups
        self.priority = priority

class TrafficSimulationEnvHandler():
    def __init__(self, 
                 start_time, 
                 test_duration_seconds, 
                 model_folder,
                 groups, 
                 connections, 
                 junction, 
                 signal_groups,
                 legs,
                 allowed_green_signal_combinations,
                 amber_time, 
                 red_amber_time,
                 min_green_time) -> None:
        
        # Initialize simulation
        self._game_ticks = 0
        self._total_score = 0
        self._start_time = start_time
        self._test_duration_seconds = test_duration_seconds
        self._model_folder = model_folder
        self._random = False

        self.maxdistance = 100
        self.groups = groups
        self.connections = connections
        
        self.junction = junction
        self.signal_groups = signal_groups

        self.legs_dto = []
        self.intern_legs = legs

        for leg_name, l in legs.items():
            # Populate the array for the observable state
            self.legs_dto.append(LegDto(name=leg_name, 
                                    lanes=l['lanes'],
                                    signal_groups=l['groups']))
            
        self.allowed_green_signal_combinations = {}

        for g in allowed_green_signal_combinations:           
            self.allowed_green_signal_combinations[g['signal'][0]] = g['allowed']


        self.allowed_green_signal_comb_dto = []

        for g in allowed_green_signal_combinations:
            self.allowed_green_signal_comb_dto.append(AllowedGreenSignalCombinationDto(name=g['signal'][0], groups=g['allowed']))

        self.amber_time = amber_time
        self.red_amber_time = red_amber_time
        self.min_green_time = min_green_time

        self.group_states = {}

        for group in groups:
            self.group_states[group] = ('red', 0)

        self.next_groups = {}

        for group in groups:
            self.next_groups[group] = 'red'

        self.vehicle_waiting_time = {}
        self.observable_state = TrafficSimulationPredictRequestDto(
            vehicles=[],
            total_score=0,
            simulation_ticks=0,
            signals=[],
            signal_groups=self.signal_groups,
            legs=self.legs_dto,
            allowed_green_signal_combinations=self.allowed_green_signal_comb_dto,
            is_terminated=False
        )

        self._is_initialized = False
        self._simulation_is_running = False
        self.simulation_ticks = 0

        self.delay_penalty_coefficient = 1.5
        self.delay_penalty_start_seconds = 90
        self.warm_up_ticks = 10

        self.errors = []

        self._traci_connection = None

        self._input_queue = None
        self._output_queue = None
        self._error_queue = None

    def set_queues(self, input_q, output_q, error_q):
        self._input_queue = input_q
        self._output_queue = output_q
        self._error_queue = error_q
        
    def distance_to_stop(self, vehicle):
        for (intersection, _, distance, _) in self._traci_connection.vehicle.getNextTLS(vehicle):
            if intersection == self.junction:
                return distance
        return None
    
    def set_random_state(self, random):
        self._random = random

    def _calculate_score(self):
        score = 0.0

        for vehicle, waiting_time in self.vehicle_waiting_time.items():
            score += waiting_time

            if waiting_time > self.delay_penalty_start_seconds:
                score += (self.vehicle_waiting_time[vehicle] - self.delay_penalty_start_seconds)**self.delay_penalty_coefficient


        return score
    
    def get_simulation_is_running(self):
        if self._is_initialized == False:
            return True
        else:
            return self._simulation_is_running
    
    def get_simulation_ticks(self): 
        return self.simulation_ticks
    
    def get_observable_state(self):
        return self.observable_state
    
    def _validate_next_signals(self, next_groups):

        all_signals = {}
        logic_errors = []
        green_lights = []

        # Per default, all signals are red
        for s in self.next_groups:
            all_signals[s] = "red"

        for group, color in next_groups.items():
            if not group in self.next_groups:
                # Is this even possible to get here?
                logic_errors.append(f"Invalid signal group {group} at time step {self.get_simulation_ticks()}")
                continue

            c = color.lower()
            all_signals[group] = c

            if c == 'green':
                green_lights.append(group)

        # Check the logic according to the green light combinations
        for group, color in all_signals.items():
            if color == "green":
                # Check if we can allow this green light in combination with the other green light requests

                for other_green_lights in green_lights:
                    if group == other_green_lights:
                        continue

                    if not other_green_lights in self.allowed_green_signal_combinations[group]:
                        green_lights.remove(group)
                        logic_errors.append(f"Invalid green light combination at time step {self.get_simulation_ticks()}: {group} and {other_green_lights}. Removed {group} from green lights.")
                        break


        # Set the green lights in the next groups
        for group in green_lights:
            self.next_groups[group] = 'green'

        if len(logic_errors) == 0:
            return None

        logger.info(f"logic_errors: {logic_errors}")
        return ";".join(logic_errors)
                    
    def set_next_signals(self, next_groups):

        errors = self._validate_next_signals(next_groups)
        
        return errors

    def _update_group_states(self, next_groups):

        for group, color in next_groups.items():
            if not group in self.group_states:
                continue
            current_color, time = self.group_states[group]
            if color == current_color:
                self.group_states[group] = (current_color, time+1)
            elif current_color == 'redamber':
                if time == self.red_amber_time:
                    self.group_states[group] = ('green', 1)
                else:
                    self.group_states[group] = ('redamber', time+1)
            elif current_color == "amber":
                if time == self.amber_time:
                    self.group_states[group] = ('red', 1)
                else:
                    self.group_states[group] = ('amber', time+1)
            elif color == 'red' and current_color == 'green':
                if time == self.min_green_time:
                    self.group_states[group] = ('amber', 1)
                else:
                    self.group_states[group] = ('green', time+1)
            elif color == 'green' and current_color == 'red':
                self.group_states[group] = ('redamber', 1)
            else:
                raise Exception("Invalid state transition at tick {self.simulation_ticks}, {current_color} -> {color}")
            
    def _color_to_letter(self, color):
        if color == 'red':
            return 'r'
        elif color == 'amber' or color == 'redamber':
            return 'y'
        elif color == 'green':
            return 'g'
        else:
            raise ValueError(f"Got unknown color {color}")

    def _get_phase_string(self):
        res = ""
        for connection in self.connections:
            to_set = 'r'
            for g in connection.groups:
                (color, _time) = self.group_states[g]
                color = self._color_to_letter(color)
                if to_set == 'r':
                    to_set = color
                elif to_set == 'y' and color == 'g':
                    to_set == 'g'
                elif to_set == 'g' or to_set == 'y':
                    pass
                else:
                    raise ValueError("Invalid state reached in get_phase_string")
            if to_set == 'g' and connection.priority:
                to_set = 'G'
            res += to_set
        assert(len(res) == len(self.connections))

        return res

    def _set_signal_state(self):
        phase_string = self._get_phase_string()
        
        self._traci_connection.trafficlight.setRedYellowGreenState(
            self.junction, phase_string)
        
    def _update_vehicles(self):
                        
        observed_vehicles = []

        for leg_name, values in self.intern_legs.items():
            segments = values['segments']

            for segment in segments:
                vehicles = list(traci.edge.getLastStepVehicleIDs(segment))
                for vehicle in vehicles:
                    distance = self.distance_to_stop(vehicle)
                    if distance == None or distance > self.maxdistance:
                        continue
                    vehicle_speed = abs(traci.vehicle.getSpeed(vehicle))

                    observed_vehicles.append(VehicleDto(speed=round(vehicle_speed, 1), 
                                                        distance_to_stop=round(distance, 1),
                                                        leg=leg_name))

                    if vehicle_speed < 0.5: # Vehicle travels at less than 1.8 km/h
                        if vehicle not in self.vehicle_waiting_time:
                            self.vehicle_waiting_time[vehicle] = 0
                        self.vehicle_waiting_time[vehicle] += 1

        return observed_vehicles

    def demo(self):
        sumoBinary = checkBinary('sumo')

        logger.info('Traffic simulation - starting sumo....')

        sim_instance = uuid4().hex

        traci.start([sumoBinary, "--start", "--random", "--quit-on-end", "-c", (self._model_folder / "net.sumocfg").as_posix()], label=sim_instance)
        self._traci_connection = traci.getConnection(sim_instance)
        self._is_initialized = True

        simulationTicks = self.warm_up_ticks

        self.set_next_signals({
            'B2': 'green',
            'B1': 'green'
        })

        for i in range(simulationTicks):
            self._run_one_tick()

        logger.info('Traffic simulation - finished....')

        self._traci_connection.close()

        return self.observable_state

    def _run_one_tick(self, terminates_now=False):
        self._traci_connection.simulationStep()
        self.simulation_ticks += 1

        observed_vehicles = []
        signals = []

        # Get the current state of the simulation
        observed_vehicles = self._update_vehicles()

        # Update the score
        self._total_score = self._calculate_score()

        # Get the next phase from the request and set it
        with lock:
            try:
                if self._input_queue:
                    next_groups = self._input_queue.get_nowait()

                    signal_logic_errors = self.set_next_signals(next_groups)

                    if self._error_queue and signal_logic_errors:
                        self._error_queue.put(signal_logic_errors)

                self._update_group_states(self.next_groups)
            except Exception as e:
                self.errors.append(e)

        self._set_signal_state()

        for group, state in self.group_states.items():
            signals.append(SignalDto(name=group, state=state[0]))

        # Update the observable state
        self.observable_state = TrafficSimulationPredictRequestDto(
            vehicles=observed_vehicles,
            total_score=self._total_score,
            simulation_ticks=self.simulation_ticks,
            signals=signals,
            legs=self.legs_dto,
            signal_groups=self.signal_groups,
            allowed_green_signal_combinations=self.allowed_green_signal_comb_dto,
            is_terminated=terminates_now
        )       

        if self._output_queue:
            self._output_queue.put(self.observable_state)         

    def run_simulation(self):

        self._simulation_is_running = True

        logger.info('Traffic simulation - starting sumo....')
        sumoBinary = checkBinary('sumo')

        sim_instance = uuid4().hex

        if self._random:
            traci.start([sumoBinary, "--start", "--random", "--quit-on-end", "-c", (self._model_folder / "net.sumocfg").as_posix()], label=sim_instance)
        else:
            traci.start([sumoBinary, "--start", "--quit-on-end", "-c", (self._model_folder / "net.sumocfg").as_posix()], label=sim_instance)

        self._traci_connection = traci.getConnection(sim_instance)
        self._is_initialized = True
        
        self.simulation_ticks = 0

        for i in range(self.warm_up_ticks):
            self._run_one_tick()

        while True:
            logger.info(f'Traffic simulation - tick {self.simulation_ticks}....')
            
            if self.simulation_ticks < (self._test_duration_seconds + self.warm_up_ticks):
                self._run_one_tick()
                sleep(1)
            else:
                self._run_one_tick(terminates_now=True)
                break

        self._traci_connection.close()
        self._simulation_is_running = False









    
    