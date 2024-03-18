
try:
    import tomllib
except ImportError:
    import tomli as tomllib

import jsonschema
import json

def get_settings():
    with open("config_schema.json", "rb") as f:
        schema = json.load(f)

    with open("module_config.toml", "rb") as f:
        module_config = tomllib.load(f)

    with open("user_config.toml", "rb") as f:
        user_config = tomllib.load(f)

    do_validate(module_config,schema,"module")

    combined_config = combine(module_config,user_config)
    
    do_validate(combined_config,schema,"module+user")
    return combined_config


def do_validate(config,schema, label=""):
    try:
        jsonschema.validate(instance=config,schema=schema,format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER)
    except jsonschema.ValidationError as v_err:
        print(f"ERROR: {label} config: {v_err.json_path} >> {v_err.message}")

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
            


if __name__ == "__main__":
    print(get_settings())