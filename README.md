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
- `cd ~/PowerMonitoring/`
- `shoestring assemble`
- Follow the prompts
  - How to cancel addition of second machine?
  - How to configure analysis? No prompt for assumed voltage.

## Build
- `docker compose build`

### Start
- `docker compose up`
