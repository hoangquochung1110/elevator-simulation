# python -m src.services.run_services
import asyncio
from src.services.scheduler import Scheduler
from src.services.controller import ElevatorController


async def main():
    # initialize global logging using LOGGING_CONFIG
    import logging, logging.config
    from src.config import LOGGING_CONFIG
    logging.config.dictConfig(LOGGING_CONFIG)
    sched = Scheduler()
    controller_1 = ElevatorController(elevator_id=1)
    controller_2 = ElevatorController(elevator_id=2)
    controller_3 = ElevatorController(elevator_id=3)
    await asyncio.gather(
        sched.start(),
        controller_1.start(),
        controller_2.start(),
        controller_3.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
