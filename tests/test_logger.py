from services.logger import get_logger


logger = get_logger("test_logger")

logger.info("Logger test started")
logger.info("This is an INFO test")
logger.warning("This is a WARNING test")
logger.error("This is an ERROR test")

print("Logger test completed.")
print("Check logs/app.log")