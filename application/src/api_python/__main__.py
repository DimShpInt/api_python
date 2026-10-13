import structlog
import uvicorn

from api_python.config import settings
from api_python.logging_config import setup_logging


def main() -> None:
    setup_logging()
    logger = structlog.get_logger()
    logger.info(
        "application_started",
        env=settings.ENV.value,
        port=settings.API_PORT,
    )
    uvicorn.run(
        "api_python.api:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        # не даём uvicorn перетереть structlog-конфигурацию
        log_config=None,
    )


if __name__ == "__main__":
    main()
