from src.api_handler import APIHandler
from src.process_manager import ProcessManager

import asyncio
import json
import datetime
import re
from dataclasses import dataclass
from os import makedirs
from pathlib import Path
from collections import deque

class AsyncDeque:
    def __init__(self, maxsize=10):
        self.deque = deque(maxlen=maxsize)
        self.lock = asyncio.Lock()

    async def add(self, item):
        """Safely add an item to the deque."""
        async with self.lock:
            self.deque.append(item)

    async def get_last(self, index=0):
        """Safely get an item (default: most recent)"""
        async with self.lock:
            if len(self.deque) > index:
                return self.deque[-(index+1)]  # -1 is last, -2 is second last, etc.
            return "n/a"

    async def get_all(self):
        """Safely get all items as a list"""
        async with self.lock:
            return list(self.deque)

@dataclass
class WorkerConfig():
    api_url: str = "http://localhost:8000"

    # Paths
    data_folder : str = "./data"
    in_subfolder : str = "input"
    out_subfolder : str = "output"
    db : str = "moe.json"
    
    commands_stored : int = 10

    ping_interval : int = 10
    job_ping_interval : int = 30

class Worker():
    def __init__(self, config: WorkerConfig = WorkerConfig()):
        # Save the configuration
        self.config = config

        # Initialize the API handler and the process manager
        self.api_handler = APIHandler(self.config.api_url)
        self.process_manager = ProcessManager()
        if not self.process_manager.check_executable():
            raise Exception("Executable not found")
        
        # Ensure save folder exists. Convert the paths to Path objects
        self.data_folder = Path(config.data_folder)
        self.in_folder = self.data_folder / config.in_subfolder
        self.out_folder = self.data_folder / config.out_subfolder
        makedirs(config.data_folder, exist_ok=True)
        makedirs(self.in_folder, exist_ok=True)
        makedirs(self.out_folder, exist_ok=True)


        ### Files database ###
        # {"in_files": {"file_id": {"type": "kraus/vector", "path": "path/to/file"}}, "out_files": {"job_id": {"type": "kraus/vector", "path": "path/to/file"}}}

        # If db file exists, load it
        self.db_path = self.data_folder / config.db
        if self.db_path.exists():
            with open(self.db_path, "r") as file:
                self.db = json.load(file)
        else:
            self.db = dict()

        # Initialize the flags and variables
        self.running = False # Flag to indicate if the worker is running
        self.has_job = False # Flag to indicate if the worker has a job
        self.stopped = False # Flag to indicate if the worker has been stopped (not just paused)

        self.job_id = None
        self.job_type = None
        self.job_status = None
        self.kraus_file_id = None
        self.vector_file_id = None
        self.channel_id = None
        self.number_kraus = None
        self.input_dimension = None
        self.output_dimension = None
        # These are also used to update the server!
        self.current_entropy = None
        self.current_iterations = 0
        # Background task
        self.task = None

        # These are used to display info to the gui
        # TIMESTAMPS
        self.last_checked = None
        self.logged_in = False
        self.username = None
        # CONSOLE OUTPUTS
        self.last_commands = AsyncDeque(maxsize=config.commands_stored)


    def login(self, uid: str, pwd: str):
        self.logged_in = self.api_handler.login(uid,pwd)
        if self.logged_in:
            self.username = uid
        return self.logged_in
    
    def is_logged_in(self):
        # if the last check was too long ago, check again
        if not self.last_checked or (datetime.datetime.now() - self.last_checked).seconds > self.config.ping_interval:
            self.logged_in = self.api_handler.check_login()
            self.last_checked = datetime.datetime.now()
        
        return self.logged_in

    def get_job(self):
        job_dic = self.api_handler.get_job()
        # Check if we got a job
        if not job_dic:
            return False
        # Extract the job data
        self.job_id = job_dic["job_id"]
        self.job_type = job_dic["job_type"]
        self.job_status = job_dic["job_status"]
        self.kraus_file_id = job_dic["kraus_id"]
        self.vector_file_id = job_dic["vector_id"]
        # Extract the job specific data
        if self.job_type == "generate_kraus":
            self.channel_id = job_dic["job_data"]["channel_id"]
            self.number_kraus = job_dic["job_data"]["number_kraus"]
            self.input_dimension = job_dic["job_data"]["input_dimension"]
            self.output_dimension = job_dic["job_data"]["output_dimension"]
        elif self.job_type == "generate_vector":
            self.input_dimension = job_dic["job_data"]["input_dimension"]
            self.channel_id = job_dic["job_data"]["channel_id"]
        elif self.job_type == "minimize":
            self.channel_id = job_dic["job_data"]["channel_id"]
            self.number_kraus = job_dic["job_data"]["number_kraus"]
            self.input_dimension = job_dic["job_data"]["input_dimension"]
            self.output_dimension = job_dic["job_data"]["output_dimension"]
        
        # Signal that we have a job
        self.has_job = True
        # update last check
        self.last_checked = datetime.datetime.now()
        return True

    def handle_file_download(self):
        # Get the necessary files for the job, if any. This is only relevant for minimization jobs, where both the vector and the kraus operators need to be specified.
        if self.job_type == "minimize":
            if not self.vector_file_id or not self.kraus_file_id:
                print(f"[Error] Missing vector or kraus file")
                return False
            # Download the vector file
            vectorlink = self.api_handler.request_download_link(self.vector_file_id)
            if not vectorlink:
                print(f"[Error] Failed to get download link for vector file")
                return False
            fl = self.api_handler.download_file(vectorlink["download_url"], self.in_folder / f"{self.vector_file_id}_in.dat")
            if not fl:
                print(f"[Error] Failed to download vector file")
                return False
            # Add to db. Use setdefault as the keys don't necessarily exist!
            self.db.setdefault("in_files", dict())[self.vector_file_id] = {"type": "vector", "path": str(self.in_folder / f"{self.vector_file_id}_in.dat")}
            # Download the kraus file
            krauslink = self.api_handler.request_download_link(self.kraus_file_id)
            if not krauslink:
                print(f"[Error] Failed to get download link for kraus file")
                return False
            fl = self.api_handler.download_file(krauslink["download_url"], self.in_folder / f"{self.kraus_file_id}_in.dat")
            if not fl:
                print(f"[Error] Failed to download kraus file")
                return False
            # Add to db
            self.db.setdefault("in_files", dict())[self.kraus_file_id] = {"type": "kraus", "path": str(self.in_folder / f"{self.kraus_file_id}_in.dat")}
            # Update the db in the file
            with open(self.db_path, "w") as file:
                json.dump(self.db, file)

    async def run_job(self):
        # Handle file download
        self.handle_file_download()

        # Run the job
        if self.job_type == "generate_kraus":
            # Need to generate kraus.
            out = await self.process_manager.run_kraus_generation(self.input_dimension, self.number_kraus, self.out_folder / f"{self.job_id}_out.dat")
            # Check that execution was successful
            if not out or not out[0]:
                print(f"[Error] Failed to run job")
                return False
            # Add to db
            self.db.setdefault("out_files", dict())[self.job_id] = {"type": "kraus", "path": str(self.out_folder / f"{self.job_id}_out.dat")}
            # Save db
            with open(self.db_path, "w") as file:
                json.dump(self.db, file)
        elif self.job_type == "generate_vector":
            # Need to generate vector
            out = await self.process_manager.run_vector_generation(self.input_dimension, self.out_folder / f"{self.job_id}_out.dat")
            # Check that execution was successful
            if not out or not out[0]:
                print(f"[Error] Failed to run job")
                return False
            # Add to db
            self.db.setdefault("out_files", dict())[self.job_id] = {"type": "vector", "path": str(self.out_folder / f"{self.job_id}_out.dat")}
            # Save db
            with open(self.db_path, "w") as file:
                json.dump(self.db, file)
        elif self.job_type == "minimize":
            # Need to minimize
            out = await self.process_manager.run_singleshot_minimization(self.out_folder / f"{self.job_id}_out.dat", self.in_folder / f"{self.vector_file_id}_in.dat", self.in_folder / f"{self.kraus_file_id}_in.dat")
            # Check that execution was successful
            if not out or not out[0]:
                print(f"[Error] Failed to run job")
                return False
            # Add to db
            self.db.setdefault("out_files", dict())[self.job_id] = {"type": "vector", "path": str(self.out_folder / f"{self.job_id}_out.dat")}                          
            # Save db
            with open(self.db_path, "w") as file:
                json.dump(self.db, file)

        else:
            print(f"[Error] Unknown job type: {self.job_type}")
            # Signal that we no longer have a job (TODO: should we do this?)
            self.has_job = False
            return False

         # Upload the results if necessary and update the job status and info
        # Case 1: generate_kraus
        if self.job_type == "generate_kraus":
            # get upload link
            upload_link = self.api_handler.request_upload_link()
            if not upload_link:
                print(f"[Error] Failed to get upload link")
                return False
            # Upload the kraus file
            # Search for the file in the db
            file = self.db["out_files"].get(self.job_id)
            if not file:
                print(f"[Error] File not found in db")
                return False
            fl = self.api_handler.upload_file(self.job_id, "kraus", Path(file["path"]), upload_link["upload_url"])
            if not fl:
                print(f"[Error] Failed to upload kraus file")
                return False
            # Update the job status
            fl = self.api_handler.complete_job(self.job_id)
            if not fl:
                print(f"[Error] Failed to update job status")
                return False
        # Case 2: generate_vector
        elif self.job_type == "generate_vector":
            # get upload link
            upload_link = self.api_handler.request_upload_link()
            if not upload_link:
                print(f"[Error] Failed to get upload link")
                return False
            # Upload the vector file
            # Search for the file in the db
            file = self.db["out_files"].get(self.job_id)
            if not file:
                print(f"[Error] File not found in db")
                return False
            fl = self.api_handler.upload_file(self.job_id, "vector", Path(file["path"]), upload_link["upload_url"])
            if not fl:
                print(f"[Error] Failed to upload vector file")
                return False
            # Update the job status
            fl = self.api_handler.complete_job(self.job_id)
            if not fl:
                print(f"[Error] Failed to update job status")
                return False
        # Case 3: minimize
        elif self.job_type == "minimize":
            # get upload link
            upload_link = self.api_handler.request_upload_link()
            if not upload_link:
                print(f"[Error] Failed to get upload link")
                return False
            # Upload the vector file
            # Search for the file in the db
            file = self.db["out_files"].get(self.job_id)
            if not file:
                print(f"[Error] File not found in db")
                return False
            fl = self.api_handler.upload_file(self.job_id, "vector", Path(file["path"]), upload_link["upload_url"])
            if not fl:
                print(f"[Error] Failed to upload vector file")
                return False
            # Update the number of iterations.
            if self.current_iterations > 0:
                fl = self.api_handler.update_iterations(self.job_id, self.current_iterations)
                if not fl:
                    print(f"[Error] Failed to update iterations")
                    return
            # Update the entropy value
            if self.current_entropy:
                fl = self.api_handler.update_entropy(self.job_id, self.current_entropy)
                if not fl:
                    print(f"[Error] Failed to update entropy")
            # Update the job status
            fl = self.api_handler.complete_job(self.job_id)
            if not fl:
                print(f"[Error] Failed to update job status")
                return False

        # Signal that we no longer have a job
        self.has_job = False

            

        return True
    

    async def parse_line(self, line):
        # add line to queue
        await self.last_commands.add(line)
        # check if the line contains the entropy value of the current iteration
        # Regex pattern
        pattern = r"\[\s*Iteration\s*(\d+)\s*\].*Entropy:\s*([\d\.]+)"
        # Find matches
        match = re.search(pattern, line)
        # debug
        # If we have a match, extract the values
        if match:
            self.current_iterations = int(match.group(1))  # Extracted iteration number
            self.current_entropy = float(match.group(2))     # Extracted entropy value
    


    async def consume_output(self, queue):
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=1.0)  # Avoid waiting forever
            except asyncio.TimeoutError:
                continue


            if item is None:
                break  # Stop on sentinel

            await self.parse_line(item)
            await asyncio.sleep(0)

    async def ping_server(self):

        while not self.stopped:
            # check that we have a job
            if self.running and self.has_job:
                # if that is the case, ping the server
                self.api_handler.ping_job(self.job_id)

            await asyncio.sleep(self.config.job_ping_interval)
        


    def start(self):
        if not self.running:
            self.running = True
            self.stopped = False

            loop = asyncio.get_event_loop()
            self.task = loop.create_task(self.worker_main())

    def pause(self):
        self.running = False

    def stop(self):
        self.running = False
        self.stopped = True
        #Actually stop the running processes from the process manager
        print("Stopping the running process...")
        self.process_manager.stop_process()

# function to run the worker
    async def worker_main(self):

        parse_task = asyncio.create_task(self.consume_output(self.process_manager.stdout_queue)) # This task will run in the background, consuming the output of the process
        ping_task = asyncio.create_task(self.ping_server()) # This task will run in the background, pinging the server every 30 seconds

        # Run the async worker
        await asyncio.create_task(worker.run())

        # Wait for the pinging task to finish (it will since worker has stopped)
        await ping_task

        # Stop consuming output by sending a sentinel (None)
        await self.process_manager.stdout_queue.put(None)

        # Wait for background tasks to finish
        await parse_task



    async def run(self):
        while True:
            if self.running:
                if not self.has_job:
                    # Get a new job
                    if not self.get_job():
                        await asyncio.sleep(1)
                        continue
                else:
                    # Run the job
                    await self.run_job()
                    await asyncio.sleep(1)
            if self.stopped:
                # The running process is already stopped in the self.stop method, otherwise we never exit run_job().
                # Either run_job was running non minimizing tasks, in which case it finished running normally, or it was running a minimization task, in which case it was stopped by the stop method.
                # If minimization was running, we should update the server with the current vector and info, then cancel the job so the server can reassign it.
                if self.job_type == "minimize":
                    # Assume that self.job_id is still set
                    # get upload link
                    upload_link = self.api_handler.request_upload_link()
                    if not upload_link:
                        print(f"[Error] Failed to get upload link")
                        return False
                    # Upload the vector file
                    # Search for the file in the db
                    file = self.db["out_files"].get(self.job_id)
                    if not file:
                        print(f"[Error] File not found in db")
                        return False
                    fl = self.api_handler.upload_file(self.job_id, "vector", Path(file["path"]), upload_link["upload_url"])
                    if not fl:
                        print(f"[Error] Failed to upload vector file")
                        return False
                    # Update the number of iterations.
                    if self.current_iterations > 0:
                        fl = self.api_handler.update_iterations(self.job_id, self.current_iterations)
                        if not fl:
                            print(f"[Error] Failed to update iterations")
                            return
                    # Update the entropy value
                    if self.current_entropy:
                        fl = self.api_handler.update_entropy(self.job_id, self.current_entropy)
                        if not fl:
                            print(f"[Error] Failed to update entropy")
                    # Update the job status to pending, so it can be resumed later
                    fl = self.api_handler.cancel_job(self.job_id)
                    if not fl:
                        print(f"[Error] Failed to update job status")
                        return False                


                break



worker = Worker()