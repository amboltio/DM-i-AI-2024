# Traffic Simulation
In this use-case the objective is to control the traffic lights at a congested intersection. 
Your job is to get as many vehicles through the intersection, thus minimizing the time waiting at the stop lights.

<p align="center">
  <img src="../images/trafficsim.png" width=650>
</p>

The simulation runs in real time at our server. Every second, we ask you to set the state of the traffic lights. In return, you will get a list of vehicles either approaching the intersection or waiting at your red lights.

## About the game
The simulation is based on the [SUMO framework](https://eclipse.dev/sumo/) (Simulation of Urban MObility).

Each evaluation and validation runs in real time for ten minutes. The observable state of the intersection is updated every second and is sent to your REST API for instructions on the future signal state. Once received, we will use your signal commands for the *next* update of the simulation (e.g. max 1 second after).

Thus, your API service needs to provide a response within 1 second but there is no reason to chase single-digit millisecond response times; we only update the state of the traffic lights every second.

### Intersection legs
Each intersection has tree to four legs where vehiches approach and leave the intersection. 
Each leg may have one or more lanes. Each of these lanes is controlled by a traffic light - and it is up to you(r algorithm) to control the traffic light.

Intersection with designated legs:
<p align="center">
  <img src="../images/intersection-with-legs.png" width=650>
</p>

A lane allows for a vehicle to cross the intersection in a certain manner. You may experience the following lane types in this use case:

- **Main**: Allows for traffic to go straight, left, or right at the lane
- **Straight**: Allows for trafic to go straight at the lane
- **RightTurn**: Allows for traffic to turn right at the lane
- **LeftTurn**: Allows for traffic turn turn left at the lane

### Vehicles
We observe the vehicles as they approach the intersection. You will receive a list of all approaching vehicles that are within 100 meters of the intersection with the following attributes:

- Distance_to_stop (m) (Distance to the traffic light)
- Speed (m/s)
- Leg (Name of the intersection leg that the vehicle is travelling on)

We do not care about the vehicles leaving the intersection. Thus, if a vehicle crosses the traffic light, it disappears. 

### Traffic lights 🚦

The observable states of the traffic lights are:

| Red   | Red/yellow    | Yellow | Green    |
|-------|---------------|--------|----------|
| 🔴    | 🔴            | ⚫     | ⚫       |
| ⚫    | 🟡            | 🟡     |⚫        |
| ⚫    | ⚫            | ⚫     |🟢        |

We impose the following restrictions on the signals:

1. The signal cannot change directly from red to green and vice versa. The transitions are:

    a) Red -> Red/yellow -> Green

    b) Green -> Yellow -> Red
2. Each signal state must be activated for at least:

    a) Red/yellow: 2 seconds
    b) Yellow: 4 seconds
    c) Green: 6 seconds

3. Our simulation controller will make sure that these restrictions are enforced. Thus, if you ask to switch the signal from red to green, we will make sure that the signal goes through the red/yellow phase for two seconds before switching to green.

4. According to 3), it is only necessary for your model to ask for either red light or green light.

**Allowed green light combinations** It is not possible (and probably not desirable, either!) to set the state to green for all of the traffic lights. In the intersection above, we would not want to turn on the green lights for both leg A1 and B1 - the cars would potentially collide, and the cars behind would form a looong queue (hello exponential penalty!). 


### Scoring
You will receive a score based on the total waiting time at the stop lights.
We compute the score based on the following:

**Total score**

$$
\text{score} = \sum_{i=1}^N Q_i + \sum_{i=1}^N \text{max}(0, (90-Q_i)^{1.5})
$$

where $Q_i$ is the total waiting time in seconds for vehicle *i* and $N$ is the number if vehicles in the simulation. 

We impose a penalty for every car that has waited more than 90 seconds in total. No one wants to wait forever!

**Final score** 

The final score that you see in the leaderboard is normalized in the interval between 0 to 1 by:

$$
\text{final\_score} = \frac{1}{\text{score}}
$$

## Interaction
Every second of the simulation, you will receive a payload containing the following:

- **vehicles** List[VehicleDto]: A list of vehicles approaching the intersection
- **total_score** float: The total score (so far)
- **simulation_ticks** int: The current simulation tick
- **signals** List[SignalDto]: The current state of the signals
- **signal_groups**: List[str]: A list of all the signal groups (e.g. signals) at the intersection
- **legs**: List[LegDto]: The names of the legs of the intersection, with a list of all the lanes and signal groups that belong to the leg.
- **allowed_green_signal_combinations**: List[AllowedGreenSignalCombinationDto]: A list for each signal group, denoting the *other* signal groups that may go into green states together with the first. 

## Evaluation
During the week of the competition, you will be able to validate your solution against the validation set. You can do this multiple times, however, **you can only submit to the evaluation set once!** The best validation and evaluation score your model achieves will be displayed on the <a href="https://cases.dmiai.dk"> scoreboard</a> . We encourage you to validate your code and API before you submit your final model to evaluation. 

Randomness: We use a random seed for running the validation endpoint. Thus, you will probably receive different scores even if your algorithm stays the same. This is to remind you to not overfit to the validation set. The random seed is fixed for the evaluation endpoint.

## Quickstart

```cmd
git clone https://github.com/amboltio/DM-i-AI-2024
cd DM-i-AI-2024/traffic-simulation
```

Install sumo according to the <a href="https://sumo.dlr.de/docs/Installing/index.html">instructions</a>.

Install dependencies
```cmd
pip install -r requirements.txt
```


### Serve your endpoint
Serve your endpoint locally and test that everything starts without errors

```cmd
python api.py
```
Open a browser and navigate to http://localhost:9051. You should see a message stating that the endpoint is running. 
Feel free to change the `HOST` and `PORT` settings in `api.py`. 

You can request the following signal states in the response:

* "red"
* "redamber"
* "amber"
* "green"

Tip: Only request the "green" and "red" states, our endpoint will take care of the rest.



### Run the simulation locally
```cmd
cd DM-i-AI-2024/traffic-simulation/sim
python3 run_sim.py
```