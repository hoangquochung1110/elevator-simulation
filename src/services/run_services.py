# python -m src.services.run_services
import asyncio
from src.services.scheduler import Scheduler
from src.services.controller import ElevatorController


async def main():
    sched = Scheduler()
    controller = ElevatorController(elevator_id=1)
    await asyncio.gather(sched.start(), controller.start())

if __name__ == "__main__":
    asyncio.run(main())
