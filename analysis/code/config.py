
try:
    import tomllib
except ImportError:
    import tomli as tomllib

import jsonschema
import json
import os
import logging

logger = logging.getLogger("config")

def get_settings():
    with open("./config_schema.json", "rb") as f:
        schema = json.load(f)

    with open("./config/module_config.toml", "rb") as f:
        module_config = tomllib.load(f)

    with open("./config/user_config.toml", "rb") as f:
        user_config = tomllib.load(f)

    do_validate(module_config,schema,"module")

    combined_config = combine(module_config,user_config)
    
    do_validate(combined_config,schema,"module+user")

    env_var_overwrite(combined_config)

    do_validate(combined_config,schema,"module+user+env")

    logger.info(f"Final Config: {combined_config}")
    return combined_config


def do_validate(config,schema, label=""):
    try:
        jsonschema.validate(instance=config,schema=schema,format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER)
    except jsonschema.ValidationError as v_err:
        logger.error(f"{label} config: {v_err.json_path} >> {v_err.message}")

def combine(A,B):
    output = A.copy()
    do_combine(output,B)
    return output

def do_combine(original,new):
    for k,v in new.items():
        if k in original:
            if isinstance(original[k],dict):    # handle nesting
                do_combine(original[k],v)
            else:   # handle value replacement
                original[k] = v
        else: # handle new value
            original[k] = v
            
def env_var_overwrite(config, parent=None):
    for key,value in config.items():
        current_key = f"{parent}__{key.upper()}" if parent else key.upper()
        if isinstance(value,dict):
            env_var_overwrite(value,parent=current_key)
        else:
            new_value = os.environ.get(current_key)
            if new_value is not None:
                logger.info(f"Overwrote config with {current_key}:{new_value}")
                config[key] = new_value
        

if __name__ == "__main__":
    print(get_settings())