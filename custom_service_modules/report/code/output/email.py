import aiohttp
import logging

logger = logging.getLogger(__name__)

def send_via_platform(tag, report_date):

    async def wrapped(dataframe):
        url = f"http://platform_link.docker.local:81/alert/{tag}"

        dataframe.rename(columns={"energy": "total_consumption"})
        content = dataframe.to_dict(orient="records")

        body = {
            "report_date": report_date,
            "power_data": [
                content
            ],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body,
            ) as resp:
                if resp.status == 200:
                    pass
                else:
                    logger.warning(f"Send email returned {resp.status}")
    return wrapped
