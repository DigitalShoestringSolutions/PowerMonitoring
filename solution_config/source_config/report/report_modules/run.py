# Standard library imports
import logging
import datetime

# Internal module imports
import analysis.general
from trigger.engine import TriggerEngine
from pipeline import Pipeline
import analysis.electrical
import query.influx
import config_manager
import output.email


# Parse command-line arguments and configure logging again based on those
args = config_manager.handle_args()
logging.basicConfig(level=args["log_level"])
logger = logging.getLogger(__name__)

# Load configuration from config files
config = config_manager.get_config(
    args.get("module_config_file"), args.get("user_config_file")
)

# Initialize the trigger engine with loaded configuration
trigger = TriggerEngine(config)

"""
In Chat GPT enter:
    My cron implementation treats day of week and day of month as an AND. 
    I don't want logic in a script. What is the cron tab expression for 
followed by when you want it to run.
it will give you a set of 5 numbers or characters separated by a space. Put that in the task.

For example: every friday at 17:00 gives:
0 18 * * 5 your-command

so we would use: "0 18 * * 5"

Another example: fourth friday of the month at 6pm:
"0 18 22-28 * 5"

Every ten minutes:
"*/10 * * * *"

"""


"""
Explanation of cron syntax for task scheduling using the @trigger.scheduler.task decorator.
Examples:
- Every Friday at 6pm:          "0 18 * * 5"
- Fourth Friday of the month:  "0 18 22-28 * 5"
- Every 10 minutes:            "*/10 * * * *"
"""


# Scheduled task that runs every friday at 6pm summarising the week's power usage
@trigger.scheduler.task("0 18 * * 5")
async def weekly_report(last_run=None, execution_time=None, config={}):
    pipeline = Pipeline.start()

    # Use an offset to ensure all necessary data is available (e.g., due to data delays)
    historic_offset = datetime.timedelta(minutes=1)
    window_start = last_run - historic_offset
    window_end = execution_time - historic_offset

    logger.info(f"## Weekly Report: {window_start} {window_end}")

    prev_window_start = window_start - (window_end - window_start)

    # Pipeline steps: fetch data -> compute power -> write results
    await pipeline.next(query.influx.total_energy(config,prev_window_start, window_start, window_end))
    logger.debug(pipeline.result)
    await pipeline.next(
        analysis.general.percentage_change("energy_prev", "energy_curr", "change")
    )
    logger.debug(pipeline.result)

    await pipeline.next(
        output.email.send_via_platform(
            "power_monitoring_weekly", window_end.strftime("%Y-%m-%d")
        )
    )
    logger.debug(pipeline.result)

# Start the trigger engine and its scheduler/event loops
trigger.start()
