from src.api_handler import APIHandler
from src.process_manager import ProcessManager
import asyncio
from dataclasses import dataclass
from os import makedirs
from pathlib import Path
import json

@dataclass
class WorkerConfig():
    api_url: str = "http://localhost:8000"

    # Paths
    data_folder = "./data"
    in_subfolder = "input"
    out_subfolder = "output"
    db = "moe.json"


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

        # Initialize the variables
        self.running = False
        self.has_job = False

        self.job_id = None
        self.job_type = None
        self.job_status = None
        self.kraus_file_id = None
        self.vector_file_id = None
        self.channel_id = None
        self.number_kraus = None
        self.input_dimension = None
        self.output_dimension = None



    def login(self, uid: str, pwd: str):
        return self.api_handler.login(uid,pwd)

        
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
        
        # Signal that we have a job
        self.has_job = True
        return True

    def handle_file_download(self):
        # Get the necessary files for the job, if any. This is only relevant for minimization jobs, where both the vector and the kraus operators need to be specified.
        if self.job_type == "minimize":
            print("Have a minimization job")
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
            # Update the number of iterations. For now use a dummy value
            fl = self.api_handler.update_iterations(self.job_id, 1)
            # Update the job status
            fl = self.api_handler.complete_job(self.job_id)
            if not fl:
                print(f"[Error] Failed to update job status")
                return False

        # Signal that we no longer have a job
        self.has_job = False

            

        return True

    async def run(self):
        while True:
            if not self.has_job:
                # Get a new job
                if not self.get_job():
                    print("No jobs found")
                    await asyncio.sleep(1)
                    continue
            else:
                # Run the job
                await self.run_job()
                await asyncio.sleep(1)