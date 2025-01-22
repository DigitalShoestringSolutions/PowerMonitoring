"""main.py for PowerMonitoring (Basic) assembled from recipe"""

## -- Imports ---------------------------------------------------------------------

# standard imports
from time import sleep

# installed imports
#none

# local imports from Sensing Service Module version lite-v0.5
from utilities.mqtt_out import publish
from hardware.ICs.BCRoboticsADCHAT import BCRoboticsADCHAT
from hardware.ICs.ads1115 import ADS1115
from hardware.ICs.sequent_16_universal_inputs import Sequent_16chADC
from hardware.generic.genericCT import CurrentTransformer

## --------------------------------------------------------------------------------




## -- Settings --------------------------------------------------------------------

sample_interval = 1 # seconds

phases = (
    # Machine name, Phase name, ADC and channel, current transformer/clamp/shunt with gain (and offset)
    ("Machine_1", "L1", BCRoboticsADCHAT(2), CurrentTransformer(gain=20*0.4)),               # 3pu AC with 20A clamps
    ("Machine_1", "L2", BCRoboticsADCHAT(4), CurrentTransformer(gain=20*0.4)),
    ("Machine_1", "L3", BCRoboticsADCHAT(7), CurrentTransformer(20*0.4)),                    # gain is first positional arg, does not need to be explicit
    ("Machine_2", "single",      ADS1115(0), CurrentTransformer(gain=50*0.4)),               # 1ph AC with 50A clamp
    ("Machine_3", "DC",          ADS1115(2), CurrentTransformer(gain=15.65, offset=1.6408)), # single phase DC
    ("Machine_4", "L1",  Sequent_16chADC(1), CurrentTransformer(30*0.4)),                    # 2pu with 30A clamp on L1
    ("Machine_4", "L2",  Sequent_16chADC(3), CurrentTransformer(10*0.4)),                    #     but only 10A on L2
)

## --------------------------------------------------------------------------------




## -- PowerMonitoring (Basic) ------------------------------------------------------

while True:
    for phase in phases:
        machine_name = phase[0]
        phase_name = phase[1]
        adc = phase[2]
        ct = phase[3]

        current = ct(adc.read_voltage())

        publish( {
            "current": current,
            "phase": phase_name,
            "machine": machine_name
            },
            "power_monitoring/" + machine_name + "/" + phase_name
            )

    sleep(sample_interval)

## --------------------------------------------------------------------------------