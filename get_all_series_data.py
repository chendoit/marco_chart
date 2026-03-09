from loguru import logger

from get_fed_series import fetch_and_save_fred_data
from get_m_square_chart import fetch_m_square_charts
from get_m_square_series import fetch_m_square_series
from get_ctfc_series import fetch_cftc_data

tasks = [
    ("FRED data", lambda: fetch_and_save_fred_data('STLFSI4')),
    ("MacroMicro charts", fetch_m_square_charts),
    ("MacroMicro series", fetch_m_square_series),
    ("CFTC data", fetch_cftc_data),
]

failed = []
for name, func in tasks:
    try:
        logger.info(f"Starting: {name}")
        func()
        logger.info(f"Completed: {name}")
    except Exception as e:
        logger.error(f"Failed: {name} — {e}")
        failed.append(name)

if failed:
    logger.warning(f"Failed tasks: {', '.join(failed)}")
else:
    logger.info("All tasks completed successfully")
