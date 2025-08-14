Notes to selves while guessing how this is intended to be used

### Install pipx
- `sudo apt install pipx`
- `pipx ensurepath`
- `sudo reboot` for PATH changes to take effect

### Install assembler
- `pipx install shoestring-assembler`
- ` pipx upgrade shoestring-assembler` in case an old version is already installed

### Download solution files
- `git clone https://github.com/DigitalShoestringSolutions/PowerMonitoring -b experiment/assembler`

### Assemble & Configure
- Check `recipe.toml` contains the modules you desire. By defaut there are two machines monitored locally.
- `cd ~/PowerMonitoring/`
- `shoestring assemble`
- Follow the prompts

## Build, Start and Stop
If you accepted the prompt to `Build the solution now` at the end of Assembling, the solution will build and start immediately.  
If not, you can manually build with `docker compose build` and start with `docker compose up`.  
To stop the solution, run `docker compose down`.  
