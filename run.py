import logging
from health_server import start_health_server
import bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("🚀 SSC Quiz Bot Application Starting...")
    start_health_server()
    bot.main()
