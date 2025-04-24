# python -m src.services.run_services
import asyncio
from src.services.scheduler import Scheduler
from src.services.controller import ElevatorController
from src.config import NUM_ELEVATORS


async def main():

    sched = Scheduler(id=1)
    # dynamically create controllers based on config
    controllers = [ElevatorController(elevator_id=i+1) for i in range(NUM_ELEVATORS)]
    # start scheduler and all controllers
    await asyncio.gather(
        sched.start(),
        *[c.start() for c in controllers],
    )


if __name__ == "__main__":
    asyncio.run(main())
