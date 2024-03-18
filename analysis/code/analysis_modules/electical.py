import logging
import datetime
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync


logger = logging.getLogger(__name__)


async def real_power(args):
    default_voltage = args["global_config"]['default_voltage']
    default_power_factor = args["global_config"]["power_factor"].get(
        "default", 1.0)
    machine_power_factors = args["global_config"]["power_factor"].get(
        "machines", {})

    tables = await __query_current_and_power(args, "power_real")

    output = []

    for table in tables:
        for record in table.records:
            machine = record.values.get("machine")
            if record.values.get("power_real") is not None:
                power_real = record["power_real"]
            else:
                power_factor = machine_power_factors.get(
                    record.values.get("machine"), default_power_factor)
                current = record.values.get("current")
                power_real = current * default_voltage * \
                    power_factor if current is not None else None
            output.append(
                {"timestamp": record["_time"].isoformat(), "power_real": power_real, "machine": machine})

    return output


async def apparent_power(args):
    default_voltage = args["global_config"]['default_voltage']

    tables = await __query_current_and_power(args, "power_apparent")
    output = []

    for table in tables:
        for record in table.records:
            machine = record.values.get("machine")
            if record.values.get("power") is not None:
                power_apparent = record["power_apparent"]
            else:
                current = record.values.get("current")
                power_apparent = current * default_voltage if current is not None else None
            output.append(
                {"timestamp": record["_time"].isoformat(), "power_apparent": power_apparent, "machine": machine})

    return output


async def __query_current_and_power(args, power_type):
    influx_conf = args['global_config']['influx']

    params = args['params']
    dt_from_raw = params.get("from")
    dt_to_raw = params.get("to")
    machine = params.get("machine")
    bucket = params.get("bucket")
    window_raw = params.get("window")

    try:
        if int(window_raw) < 2000:
            window = 2000
        else:
            window = window_raw
    except:
        window = window_raw

    if dt_from_raw:
        # extract and reformat to remove url character escaping
        dt_from = datetime.datetime.fromisoformat(dt_from_raw).isoformat()
    else:
        pass  # todo: throw exception

    if dt_to_raw:
        # extract and reformat to remove url character escaping
        dt_to = datetime.datetime.fromisoformat(dt_to_raw).isoformat()
    else:
        dt_to = datetime.datetime.now(datetime.timezone.utc).isoformat()

    query = f'''
            from(bucket: "{bucket}")
                |> range(start: {dt_from}, stop: {dt_to})
                |> filter(fn: (r) => r["_measurement"] == "equipment_power_usage")
                |> filter(fn: (r) => r["_field"] == "current" or r["_field"] == "{power_type}")
                {f'|> filter(fn: (r) => r["machine"] == "{machine}")' if machine is not None else ''}
                |> aggregateWindow(every: {window}ms, fn: mean, createEmpty: true)
                |> group(columns: ["machine","_field","_time"])
                |> sum()
                |> group(columns: ["machine"])
                |> pivot(columnKey: ["_field"], rowKey: ["_time"], valueColumn: "_value")
            '''

    logger.debug(f"QUERY: {query}")

    async with InfluxDBClientAsync(url=influx_conf['url'], token=influx_conf["token"], org=influx_conf['org']) as client:
        query_api = client.query_api()
        tables = await query_api.query(query)
    return tables


async def energy_bucket(args):
    default_voltage = args["global_config"]['default_voltage']
    default_power_factor = args["global_config"]["power_factor"].get(
        "default", 1.0)
    machine_power_factors = args["global_config"]["power_factor"].get(
        "machines", {})

    influx_conf = args['global_config']['influx']

    params = args['params']
    dt_from_raw = params.get("from")
    dt_to_raw = params.get("to")
    machine = params.get("machine")
    bucket = params.get("bucket")
    window = params.get("window")

    if dt_from_raw:
        # extract and reformat to remove url character escaping
        dt_from = datetime.datetime.fromisoformat(dt_from_raw).isoformat()
    else:
        pass  # todo: throw exception

    if dt_to_raw:
        # extract and reformat to remove url character escaping
        dt_to = datetime.datetime.fromisoformat(dt_to_raw).isoformat()
    else:
        dt_to = datetime.datetime.now(datetime.timezone.utc).isoformat()

    query = f'''
            from(bucket: "{bucket}")
                |> range(start: {dt_from}, stop: {dt_to})
                |> filter(fn: (r) => r["_measurement"] == "equipment_power_usage")
                |> filter(fn: (r) => r["_field"] == "current" or r["_field"] == "power_real")
                {f'|> filter(fn: (r) => r["machine"] == "{machine}")' if machine is not None else ''}
                |> group(columns: ["machine","_field","phase"])
                |> aggregateWindow(every: {window}, fn: integral, createEmpty: true)
                |> group(columns: ["machine","_field","_time"])
                |> sum()
                |> pivot(columnKey: ["_field"], rowKey: ["_time"], valueColumn: "_value")
                |> group(columns: ["machine"])
            '''

    logger.debug(f"QUERY: {query}")

    async with InfluxDBClientAsync(url=influx_conf['url'], token=influx_conf["token"], org=influx_conf['org']) as client:
        query_api = client.query_api()
        tables = await query_api.query(query)

    output = []

    for table in tables:
        for record in table.records:
            machine = record.values.get("machine")
            if record.values.get("power_real") is not None:
                power_integral = record["power_real"]
            else:
                power_factor = machine_power_factors.get(
                    machine, default_power_factor)
                current_integral = record.values.get("current")
                power_integral = current_integral * default_voltage * \
                    power_factor if current_integral is not None else None
            energy = power_integral / 3600  # seconds to hours
            output.append(
                {"timestamp": record["_time"].isoformat(), "energy": energy, "machine": machine})

    return output[1:-1]


async def energy_total(args):
    default_voltage = args["global_config"]['default_voltage']
    default_power_factor = args["global_config"]["power_factor"].get(
        "default", 1.0)
    machine_power_factors = args["global_config"]["power_factor"].get(
        "machines", {})

    influx_conf = args['global_config']['influx']

    params = args['params']
    dt_from_raw = params.get("from")
    dt_to_raw = params.get("to")
    machine = params.get("machine")
    bucket = params.get("bucket")
    window = params.get("window")

    if dt_from_raw:
        # extract and reformat to remove url character escaping
        try:
            dt_from = datetime.datetime.fromisoformat(dt_from_raw).isoformat()
        except ValueError:
            dt_from = dt_from_raw
    else:
        pass  # todo: throw exception

    if dt_to_raw:
        # extract and reformat to remove url character escaping
        dt_to = datetime.datetime.fromisoformat(dt_to_raw).isoformat()
    else:
        dt_to = datetime.datetime.now(datetime.timezone.utc).isoformat()

    query = f'''
            from(bucket: "{bucket}")
                |> range(start: {dt_from}, stop: {dt_to})
                |> filter(fn: (r) => r["_measurement"] == "equipment_power_usage")
                |> filter(fn: (r) => r["_field"] == "current" or r["_field"] == "power_real")
                {f'|> filter(fn: (r) => r["machine"] == "{machine}")' if machine is not None else ''}
                |> group(columns: ["machine","_field","phase"])
                |> integral()
                |> group(columns: ["machine","_field"])
                |> sum()
                |> pivot(columnKey: ["_field"], rowKey: [], valueColumn: "_value")
                |> group(columns: ["machine"])
            '''

    logger.debug(f"QUERY: {query}")

    async with InfluxDBClientAsync(url=influx_conf['url'], token=influx_conf["token"], org=influx_conf['org']) as client:
        query_api = client.query_api()
        tables = await query_api.query(query)

    output = []

    for table in tables:
        for record in table.records:
            machine = record.values.get("machine")
            if record.values.get("power_real") is not None:
                power_integral = record["power_real"]
            else:
                power_factor = machine_power_factors.get(
                    record.values.get(machine), default_power_factor)
                current_integral = record.values.get("current")
                power_integral = current_integral * default_voltage * \
                    power_factor if current_integral is not None else None
            energy = power_integral / 3600  # seconds to hours
            output.append(
                {"total_energy": energy,"machine":machine})

    return output
