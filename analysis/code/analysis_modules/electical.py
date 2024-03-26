import re
import heapq
import logging
import datetime
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from functools import lru_cache

import analysis_modules.utilities as utilities

logger = logging.getLogger(__name__)

# query
# process
# format

async def real_power(args):
    '''
        returns the real power over the requested period
        format:
        [
            {
                "timestamp":"<ISO8601 string>",
                "power_real":<value>,
                "machine":"<machine>"
            },
        ]
    '''
    output = await __get_real_power(args)
    return [{**entry, "timestamp": entry["timestamp"].isoformat()} for entry in output]


async def __get_real_power(args):
    '''
        queries and calculates the real power over the requested period
        format:
        [
            {
                "timestamp": <datetime object>,
                "power_real": <value>,
                "machine":"<machine>"
            },
        ]
    '''
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
                {"timestamp": record["_time"], "power_real": power_real, "machine": machine})

    return output


async def apparent_power(args):
    '''
        returns the real power over the requested period
        format:
        [
            {
                "timestamp":"<ISO8601 string>",
                "power_apparent":<value>,
                "machine":"<machine>"
            },
        ]
    '''
    default_voltage = args["global_config"]['default_voltage']

    tables = await __query_current_and_power(args, "power_apparent")
    output = []

    for table in tables:
        for record in table.records:
            machine = record.values.get("machine")
            if record.values.get("power_apparent") is not None:
                power_apparent = record["power_apparent"]
            else:
                current = record.values.get("current")
                power_apparent = current * default_voltage if current is not None else None
            output.append(
                {"timestamp": record["_time"].isoformat(), "power_apparent": power_apparent, "machine": machine})

    return output


async def __query_current_and_power(args, power_type):
    '''
        queries current and the power type specified over the target period
        returns: list of influxdb_client tables

        if machine not specified in params - returns for all machines
    '''
    influx_conf = args['global_config']['influx']

    params = args['params']
    dt_from_raw = params.get("from")
    dt_to_raw = params.get("to")
    machine = params.get("machine")
    bucket = params.get("bucket")
    window_original = Interval(params.get("window"))

    try:
        minimum_window = Interval("5s")
        if window_original < minimum_window:
            window = minimum_window
        else:
            window = window_original
    except:
        window = window_original

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
                |> aggregateWindow(every: {window}, fn: mean, createEmpty: true)
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

async def __query_current_and_power_integral(args):
    influx_conf = args['global_config']['influx']

    params = args['params']
    dt_from_raw = params.get("from")
    dt_to_raw = params.get("to")
    machine = params.get("machine")
    bucket = params.get("bucket")
    window = params.get("window")
    total = params.get("total","false")

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
                |> aggregateWindow(every: {window}, fn: integral, createEmpty: true, timeSrc:"_start")
                {'|> group(columns: ["machine","_field","_time"])' if total != "true" else '|> group(columns: ["_field","_time"])'}
                |> sum()
                |> pivot(columnKey: ["_field"], rowKey: ["_time"], valueColumn: "_value")
                |> group(columns: ["machine"])
            '''

    logger.debug(f"QUERY: {query}")

    async with InfluxDBClientAsync(url=influx_conf['url'], token=influx_conf["token"], org=influx_conf['org']) as client:
        query_api = client.query_api()
        tables = await query_api.query(query)

    return tables


async def energy_bucket(args):
    '''
        returns energy used within the specific timeframe grouped into buckets
        format:
        [
            {
                "timestamp":"<ISO8601 string>",
                "energy":<value>,
                "machine":"<machine>"
            },
        ]

        if machine not specified in params - returns for all machines
    '''
    output = await __get_energy(args)
    return [{**entry, "timestamp": entry["timestamp"].isoformat()} for entry in output[1:-1]]


async def __get_energy(args):
    default_voltage = args["global_config"]['default_voltage']
    default_power_factor = args["global_config"]["power_factor"].get(
        "default", 1.0)
    machine_power_factors = args["global_config"]["power_factor"].get(
        "machines", {})

    tables = await __query_current_and_power_integral(args)

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
                {"timestamp": record["_time"], "energy": energy, "machine": machine})

    return output


async def energy_total(args):
    '''
        returns the total energy used within the specific timeframe
        format:
        [
            {
                "timestamp":"<ISO8601 string>",
                "energy":<value>,
                "machine":"<machine>"
            },
        ]

        if machine not specified in params - returns for all machines
        There should be one value in the returned list for each machine
    '''
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
                {"total_energy": energy, "machine": machine})

    return output


async def period_comparison(args):
    '''
        returns the average power usage divided into series and buckets so that usage can be compared
        format:
        {
            "buckets":[<bucket_labels>],
            "series:{
                <series_label>:[<bucket_values>]
            }
        }

        supports windows of:
        > 10m - compare hour over hour in ten minute increments 
        > 1h  - compare day over day in hour increments (what does our usage look like at 9am)
        > 1d  - compare week over week in day increments (what does our usage look like on Mondays)
        > 1w  - compare year over year in week increments (what does our usage look like in the 3rd week of each year)
    '''
    window = args['params'].get("window")

    settings_collection = {
        "10m": {
            "bucket_function": lambda timestamp: (timestamp.minute, timestamp.strftime(':%M')),
            "series_function": lambda timestamp: (timestamp.year*1000000+timestamp.month*10000+timestamp.day*100+timestamp.hour, timestamp.strftime('%H:xx  %d/%m/%Y')),
        },
        "1h": {
            "bucket_function": lambda timestamp: (timestamp.hour, timestamp.strftime('%H:00')),
            "series_function": lambda timestamp: (timestamp.year*10000+timestamp.month*100+timestamp.day, timestamp.strftime('%d/%m/%Y')),
        },
        "1d": {
            "bucket_function": lambda timestamp: (timestamp.weekday(), timestamp.strftime('%A')),
            "series_function": lambda timestamp: (int(timestamp.strftime('%Y%W')), timestamp.strftime('Week %W, %Y')),
        },
        "1w": {
            "bucket_function": lambda timestamp: (int(timestamp.strftime('%Y%W')), timestamp.strftime('Week %W')),
            "series_function": lambda timestamp: (timestamp.year, timestamp.strftime('%Y')),
        }
    }

    settings = settings_collection[window]

    # query power data
    # dataset = await __get_real_power(args)
    dataset = await __get_energy(args)
    return utilities.put_in_timebuckets(dataset, settings['series_function'], settings['bucket_function'], value_key="energy")


async def top_10(args):
    print(args)
    dataset = await __get_energy(args)
    print(dataset)
    top10 = heapq.nlargest(10, dataset, key=lambda x: x["energy"] if x["energy"] is not None else 0)
    print(top10)
    return [{**entry, "timestamp": entry["timestamp"].isoformat()} for entry in top10]

'''
  |> aggregateWindow(every: 1m, fn: integral, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value / float(v: int(v:1m)/int(v:1s)) }))
  |> group(columns: ["machine","_field","phase"])
  '''

@lru_cache
def get_period_regex():
    return re.compile('(?P<number>\d*)(?P<unit>\w*)')


@lru_cache
def parse_period(period):
    regex = get_period_regex()
    match = regex.match(period)
    match_dict = match.groupdict()
    if "number" in match_dict and "unit" in match_dict:
        return int(match_dict["number"]), match_dict["unit"]
    else:
        raise Exception("Invalid period")


class Interval:
    multipliers = {
        'ms':1,
        's':1000,
        'm':60*1000,
        'h':60*60*1000,
        'd':24*60*60*1000,
    }
    def __init__(self, period_string) -> None:
        self.__number, self.__unit = parse_period(period_string)
        self.__normalised = self.__number * self.multipliers[self.__unit]

    def __str__(self) -> str:
        return f"{self.__number}{self.__unit}"

    def __lt__(self,other): 
        return self.__normalised<other.__normalised
    
    def __gt__(self,other):
        return other<self