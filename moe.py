# Main class for the MOE system
# import the necessary packages
from src.worker import Worker
import asyncio

from src.api_handler import APIHandler



'''
{   
    'job_id': 14, 
    'job_type': 'generate_kraus', 
    'job_data': {   
                    'channel_id': 76, 
                    'number_kraus': 10, 
                    'input_dimension': 100, 
                    'output_dimension': 100
                }, 
    'job_status': 'running', 
    'kraus_id': None, 
    'vector_id': None, 
    'channel_id': 76
}
'''

worker = Worker()

# Log in to the API
worker.login("client4", "password123")


async def main():
    pm = worker.process_manager

    # Start consuming stdout and stderr in the background
    stdout_task = asyncio.create_task(pm.consume_output(pm.stdout_queue))
    stderr_task = asyncio.create_task(pm.consume_output(pm.stderr_queue))

    # Run your async worker while consuming logs
    await worker.run()

    # Stop consuming output by sending a sentinel (None)
    await pm.stdout_queue.put(None)
    await pm.stderr_queue.put(None)

    # Wait for background tasks to finish
    await stdout_task
    await stderr_task

asyncio.run(main())