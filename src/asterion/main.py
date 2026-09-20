import uvicorn

from asterion.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "asterion.api.app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
