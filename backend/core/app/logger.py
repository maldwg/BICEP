import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # Ensure logs are printed to stdout
        logging.StreamHandler()  
    ]
)
LOGGER = logging.getLogger(__name__)
# Ensure logs are propagated to Gunicorn
LOGGER.propagate = True  
LOGGER.setLevel(logging.DEBUG)
# TO reduce the otherwise massive amounts of sql alchemy logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)