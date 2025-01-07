# main.py for PowerMonitoring (Basic) assembled from recipe

## -- Imports ---------------------------------------------------------------------
# standard imports
from time import sleep
# installed imports
#none
# local imports from Sensing Service Module version lite-v0.5
from utilities.mqtt_out import publish
from hardware.ICs.BCRoboticsADCHAT import BCRoboticsADCHAT
from hardware.ICs.ads1115 import ADS1115
from hardware.generic.genericCT import CurrentTransformer
## --------------------------------------------------------------------------------



## -- Settings --------------------------------------------------------------------
machine_name = "MyMachine"
sample_interval = 1 # seconds
phases = (
# Phase name, ADC and channel, current transformer/clamp/shunt with gain (and offset)
    #("L1", BCRoboticsADCHAT(15), CurrentTransformer(gain=20*0.4)),
    ("DC", ADS1115(0), CurrentTransformer(gain=15.65, offset=1.6408)),
)
## --------------------------------------------------------------------------------



## -- PowerMonitoring (Basic) ------------------------------------------------------
while True:
    for phase in phases:
        phase_name = phase[0]
        adc = phase[1]
        ct = phase[2]

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