"""Allow running the worker as: python -m runtime.worker"""

import asyncio
from runtime.worker import run_worker

if __name__ == "__main__":
    asyncio.run(run_worker())
