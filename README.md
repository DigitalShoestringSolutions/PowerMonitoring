# Power Monitoring Starter Solution

This branch demonstrates a minimal implementation of Power Monitoring (in a Basic configuration only) assembled from a recipe of service modules.  
This has flexibility including n-phases, each with different ADCs and CTs.

## Download
- Clone this repo: `git clone https://github.com/DigitalShoestringSolutions/PowerMonitoring -b feature/recipe`
- Open the downloaded folder `cd PowerMonitoring`

## Configure & Assemble
- Edit the file at `/UserConfig/Sensing/main.py` to set the machine name and configure phases and sensors
- Edit the file at `/UserConfig/Analysis/user_config.toml` to set the voltage and power factor for calculations
- Check the recipe contains the Service Modules you desire `nano recipe.txt`
- Assemble the reusuable Service Modules `ServiceModules/Asssembly/get_service_modules.sh`
  - the bespoke `Graph` and `Analysis` Service Modules are included with this Solution 
- Restart to apply the settings to the downloaded Service Modules

## Build
Build using docker: `docker compose build`

## Run
Run using the `./start.sh` script. 

## Usage
View Grafana dashboards in a web browser: `localhost:3000` 
