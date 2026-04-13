import logging
import uvicorn

from nexus.graph.driver import init_schema, close_driver

log = logging.getLogger("nexus")


def main():
    logging.basicConfig(level=logging.INFO)
    log.info("Initializing Neo4j schema...")
    init_schema()
    log.info("Starting Nexus API server...")
    uvicorn.run("nexus.api:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    try:
        main()
    finally:
        close_driver()
