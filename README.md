Notes to selves while guessing how this is intended to be used.  
Goal is to outline a robust process that will allow alpha testing.  
Hopefully many of these steps can be later removed.  

### Install pipx
- `sudo apt install pipx`
- `pipx ensurepath`
- `sudo reboot` for PATH changes to take effect

### Shoestring Setup (Install shoestring assembler and docker)
- `sudo pipx run shoestring-setup`
- `pipx upgrade shoestring-assembler` (in case you have an old version)

### Download solution files
- `shoestring app`
- Use the `Download` button to select power monitoring. Select any release tag (none of them will work as none are assembler compatible yet).
- Expect `Exception: <shoestring_assembler.interface.state_machine.steps.PromptNoRecipe object at 0x7ffedbb3db10>`
- Switch to this branch `git -C PowerMonitoring checkout experiment/assembler`

### Assemble & Configure
- Back into `shoestring app`
- Reconfigure
- Follow the prompts

## Build, Start and Stop
If you accepted the prompt to `Build the solution now` at the end of Reconfiguring, the solution will build and start immediately.  
Otherwise use the buttons in `shoestring app`.
