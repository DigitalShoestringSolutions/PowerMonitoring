import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging
import traceback
import datetime

try:
    import tomllib
except ImportError:
    import tomli as tomllib

logger = logging.getLogger("stats_collector.upload_stats")


URL_BASE = "https://platform.digitalshoestring.net/api/stats/deployments/v1"
CONFIG_FILENAME = "./config/config.toml"
ID_FILENAME = "./data/id_token"

graceful_exit_key = aiohttp.web.AppKey("graceful_exit_key", str)
id_token_key = aiohttp.web.AppKey("id_token", str)
scheduler_key = aiohttp.web.AppKey("scheduler", AsyncIOScheduler)


class IrrecoverableProblem(Exception):
    pass


async def task(app):
    logger.info("Stats sender started as background task")
    while True:
        try:
            ''' 
            This ID token is a JWT.
            Before linking with a company it contains:
            {
                "type":"anon",
                "id": "<anonymous id as UUID>",
                "iat": <issue timestamp>
            },
            After linking it contains:
            {
                "type":"link",
                "id": "<linked id as UUID>",
                "company": "<Company Name at time of link>",
                "iat": <issue timestamp>
            },
            '''
            id_token = await get_id_token()
            if id_token is None:
                id_token = await register_anonymous_deployment()

            app[id_token_key] = id_token

            scheduler = AsyncIOScheduler()

            app[scheduler_key] = scheduler

            scheduler.add_job(  # Runs once immediately
                submit_started_report,
                args=[id_token],
                id="started",
            )

            scheduler.add_job(  # Runs once immediately
                submit_usage_report,
                args=[id_token],
                id="startup_report_usage",
            )

            scheduler.add_job(
                submit_heartbeat_report,
                args=[id_token],
                trigger="interval",
                hours=3,
                jitter=60,  # seconds
                id="heartbeat",
                coalesce=True,
                misfire_grace_time=10800,  # 3h in seconds
            )

            scheduler.add_job(
                submit_usage_report,
                args=[id_token],
                trigger="interval",
                hours=24,
                jitter=60,  # seconds
                id="report_usage",
                coalesce=True,
                misfire_grace_time = 84600 # 24h in seconds
            )

            scheduler.start()

            logger.info("Scheduler set up. Main task waiting till exit signal")
            await app[graceful_exit_key]
            scheduler.shutdown()
            await on_exit(app[id_token_key])
            logger.info("Graceful exit complete")
            break
        except IrrecoverableProblem as e:
            logger.critical(f"Something went badly wrong: {e}")
            logger.critical("The stats uploader is now stopping - it will try again on next boot")
            break
        except asyncio.CancelledError:
            logger.debug("Asyncio task cancelled")
            await on_exit(app[id_token_key])
            break
        except:
            logger.error(
                f"Something unexpected went very wrong: {traceback.format_exc()} - Uploader terminating"
            )


async def get_id_token():
    retry = 0
    while retry < 3:
        logger.debug(f"Fetching id_token from file. Attempt ({retry+1})")
        try:
            with open(ID_FILENAME, "r") as fp:
                id_token = fp.read()
                logger.info("id_token read from file")
                return id_token

        except FileNotFoundError:
            logger.info(f"id file {ID_FILENAME} not found: {traceback.format_exc()}")
            return None
        except:
            logger.error(
                f"Unable to open ID file {ID_FILENAME}: {traceback.format_exc()}"
            )
            retry += 1
            await asyncio.sleep(2)

    logger.critical("Ran out of retries while trying to read ID file")
    raise IrrecoverableProblem("Anonymous ID file exists, but the application can't read it")


async def update_id_token(app,new_id_token):
    app[id_token_key] = new_id_token
    await write_id_token(new_id_token)
    scheduler = app[scheduler_key]
    for job in scheduler.get_jobs():
        job.modify(args=[new_id_token])

async def write_id_token(id_token):
    retry = 0
    while retry < 3:
        logger.debug(f"Writing id_token to file. Attempt ({retry+1})")
        try:
            with open(ID_FILENAME, "w") as fp:
                fp.write(id_token)
                logger.info("Successfully saved id_token to file")
                return
        except:
            logger.error(
                f"Unable to open id file {ID_FILENAME}: {traceback.format_exc()}"
            )
            retry += 1
            await asyncio.sleep(2)

    raise IrrecoverableProblem("Ran out of retries while trying to write to ID file")


async def register_anonymous_deployment():
    config = get_config()
    payload = {
        "solution_type": config["solution_type"],
        "solution_version": config["solution_version"],
    }
    logger.info(f"Registering Deployment >> {payload}")

    async with aiohttp.ClientSession() as session:
        retry = 0
        while retry < 3:
            logger.debug(f"Submitting registration. Attempt ({retry+1})")
            try:
                async with session.post(
                    f"{URL_BASE}/register",
                    json=payload,
                ) as resp:
                    if resp.status == 201:
                        resp_body = await resp.json()
                        anonymous_id_token = resp_body["token"]
                        await write_id_token(anonymous_id_token)
                        return anonymous_id_token
                    else:
                        logger.error(f"Registration failed: http response {resp.status}")
            except:
                logger.error(
                    f"Registration failed: {traceback.format_exc()} - will retry"
                )
            finally:
                await asyncio.sleep(60)
                retry += 1
        raise IrrecoverableProblem("Unable to register deployment - stopping for now - will retry on next restart")

def get_config():
    try:
        with open(CONFIG_FILENAME, "rb") as f:
            config = tomllib.load(f)
            return config
    except FileNotFoundError:
        raise IrrecoverableProblem(f"Expected config file at {CONFIG_FILENAME}. File Not Found - unable to load config.")


async def submit_started_report(id_token):
    report = {"event": "started"}
    await submit_running_report(id_token, report)


async def submit_heartbeat_report(id_token):
    report = {"event": "heartbeat"}
    await submit_running_report(id_token, report)


async def submit_stopped_report(id_token):
    report = {"event": "stopped"}
    await submit_running_report(id_token, report)


async def submit_running_report(id_token, report):
    headers = {"Authorization": f"Token {id_token}"}
    retry = 0
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10),
        headers=headers
    ) as session:
        while retry < 3:
            logger.debug(f"Submitting running report. Attempt ({retry+1})")
            try:
                async with session.post(
                    f"{URL_BASE}/report/running",
                    json=report,
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Running report submission complete")
                        return
                    else:
                        logger.warning(
                            f"Report transmission failed with code: {resp.status}. Will retry."
                        )
            except aiohttp.ClientConnectionError:
                logger.error("Unable to connect to target")
            except asyncio.CancelledError:
                raise #prevent suppressing error on scheduler shutdown or task cancel
            except:
                logger.error(
                    f"Running report transmission failed: {traceback.format_exc()}"
                )
            finally:
                await asyncio.sleep(60)
                retry += 1

        logger.error(
            f"Ran out of retries while trying to send running report - will try again at next time interval."
        )

last_run = None

async def submit_usage_report(id_token):
    global last_run
    now_floor_1h = datetime.datetime.now(tz=datetime.timezone.utc).replace(minute=0,second=0,microsecond=0)
    now_floor_1h_minus_24h = now_floor_1h - datetime.timedelta(days=1)

    timespan_from = last_run if last_run is not None else now_floor_1h_minus_24h

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        try:
            async with session.post(
                "http://localhost/api/gather",
            ) as resp:
                pass
            async with session.get(
                "http://localhost/api/all",
                params={
                    "from": timespan_from.isoformat(),
                    "to": now_floor_1h.isoformat(),
                },
            ) as resp:
                report = await resp.json()
                logger.debug(f"Usage: {report}")
                last_run = now_floor_1h

        except aiohttp.ClientConnectionError:
            logger.error("Unable to connect to internal target")
            raise
        except asyncio.CancelledError:
            raise #prevent suppressing error on scheduler shutdown or task cancel
        except:
            logger.error(f"Usage data gathering failed: {traceback.format_exc()}")
            raise

    headers = {"Authorization": f"Token {id_token}"}
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10), headers=headers
    ) as session:
        retry = 0
        while retry < 3:
            logger.debug(f"Submitting usage report. Attempt ({retry+1})")
            try:
                async with session.post(
                    f"{URL_BASE}/report/usage",
                    json=report,
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Usage report submission complete")
                        return
                    else:
                        logger.warning(
                            f"Report transmission failed with code: {resp.status}. Will retry."
                        )
                        logger.debug(f"Error Returned: {resp.content}")
            except aiohttp.ClientConnectionError:
                logger.error("Unable to connect to target")
            except asyncio.CancelledError:
                raise #prevent suppressing error on scheduler shutdown or task cancel
            except:
                logger.error(
                    f"Usage report transmission failed: {traceback.format_exc()}"
                )
            finally:
                await asyncio.sleep(60)
                retry += 1

        logger.error(
            f"Ran out of retries while trying to send usage report - will try again at next time interval."
        )


async def on_exit(id_token):
    logger.debug("Handling Exit")
    await submit_stopped_report(id_token)
    logger.info("Sent stop report")
