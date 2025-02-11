import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Ensure logs are printed to stdout
    ]
)
LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True  # Ensure logs are propagated to Gunicorn
LOGGER.setLevel(logging.DEBUG)

