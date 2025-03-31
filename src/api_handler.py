import aiohttp
import aiofiles
from pathlib import Path
import os
from dataclasses import dataclass
import uuid
class CursesError(Exception):
    """Custom exception for displaying errors in a curses popup."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)



@dataclass
class APIHandlerConfig:
    chunk_size: int = 1024 * 1024  # 1MB chunks
    max_request_filesize = 50 * 1024 * 1024  # 50MB
    split_larger_files = True
class APIHandler:
    def __init__(self, api_url: str, config: APIHandlerConfig = APIHandlerConfig()):
        self.config = config
        self.api_url = api_url
        self.access_token = ''
        self.refresh_token = ''

        self.status = ""

    ##############################
    # Authentication functions   #
    ##############################

    async def login(self, uid: str, pwd: str):
        self.status = "Logging in..."
        # Log in to get the token
        login_data = {"username": uid, "password": pwd}

        # Use aiohttp for asynchronous HTTP request
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/auth/login", data=login_data) as login_response:
                if login_response.status != 200:
                    self.status = f"[Error] Failed to log in: {await login_response.text()}"
                    return False

                # Parse the JSON response asynchronously
                login_info = await login_response.json()
                self.access_token = login_info.get("access_token")
                self.refresh_token = login_info.get("refresh_token")
                self.status = "Logged in successfully"
                return True
    
    async def refresh(self):
        self.status = "Refreshing token..."
        # Refresh the token
        header = {"refresh": self.refresh_token}

        # Use aiohttp to perform the request asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/auth/refresh", headers=header) as refresh_response:
                if refresh_response.status != 200:
                    self.status = f"[Error] Failed to refresh token: {await refresh_response.text()}"
                    return False

                # Parse the JSON response asynchronously
                refresh_info = await refresh_response.json()
                self.access_token = refresh_info.get("access_token")
                self.refresh_token = refresh_info.get("refresh_token")
                return True
            
    def ensure_login(func):
        async def wrapper(self, *args, **kwargs):
            # Ping the server at /auth/ping to check if the access token is still valid
            header = {"Authorization": f"Bearer {self.access_token}"}
            
            # Use aiohttp to perform the ping request asynchronously
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/auth/ping", headers=header) as ping_response:
                    if ping_response.status == 401:
                        # Access token is invalid, try to refresh it
                        if not await self.refresh():
                            # Refresh failed, return False. TODO: raise an exception? Ask the user to log in again?
                            return False
                    elif ping_response.status != 200:
                        # If there are other errors, print or handle them
                        print(f"[Error] Failed to ping server: {await ping_response.text()}")
                        return False

            # We have a valid access token, call the original function
            return await func(self, *args, **kwargs)

        return wrapper

    async def check_login(self):
        # Ping the server at /auth/ping to check if the access token is still valid
        header = {"Authorization": f"Bearer {self.access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/auth/ping", headers=header) as ping_response:
                if ping_response.status == 401:
                    # Access token is invalid, try to refresh it
                    if not await self.refresh():
                        # Refresh failed, return False. TODO: raise an exception? Ask the user to log in again?
                        return False
                elif ping_response.status != 200:
                    # Handle other errors, if needed
                    print(f"[Error] Failed to ping server: {await ping_response.text()}")
                    return False

        return True

    ##############################
    # Channel related functions  #
    ##############################

    @ensure_login
    async def create_channel(self, input_dim: int, output_dim: int, num_kraus: int, method: str = "haar"):
        # This requires admin access
        header = {"Authorization": f"Bearer {self.access_token}"}
        data = {"input_dimension": input_dim, "output_dimension": output_dim, "num_kraus": num_kraus, "method": method}

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/channels/create", headers=header, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to create channel: {await response.text()}, Status code: {response.status}")
                return None    

    @ensure_login
    async def list_channels(self):
        header = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/channels/list", headers=header) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to list channels: {await response.text()}")
                return None

    @ensure_login
    async def update_channel_minimization_attempts(self, channel_id, attempts):
        header = {"Authorization": f"Bearer {self.access_token}"}
        min_attempts_data = {"channel_id": channel_id, "attempts": attempts}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/channels/update-minimization-attempts", headers=header, data=min_attempts_data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to update minimization attempts: {await response.text()}")
                return None

    ##############################
    # File related functions     #
    ##############################

    @ensure_login
    async def request_upload_link(self):
        self.status = "Requesting upload link..."
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/files/request-upload", headers=headers) as response:
                if response.status == 200:
                    self.status = "Upload link received"
                    return await response.json()

                raise CursesError(f"Failed to get upload link: {await response.text()}")


    @ensure_login
    async def upload_file(self, job_id: int, file_type: str, file_path: Path, upload_link: str):
        self.status = "Uploading file..."
        headers = {"Authorization": f"Bearer {self.access_token}"}

        self.status = f"Uploading {file_path.name} to {upload_link}..."

        # Split the upload into multiple requests if the file is too large
        file_size = os.path.getsize(file_path)
        chunk_size = self.config.max_request_filesize  # Define the max chunk size (e.g., 10MB)
        n_uploads = (file_size // chunk_size) + (1 if file_size % chunk_size != 0 else 0)

        # get a random session id
        session_id = uuid.uuid4().hex

        self.status = f"File size: {file_size}, Max request size: {chunk_size}, Number of uploads: {n_uploads}"

        async with aiofiles.open(file_path, "rb") as file:
            for i in range(n_uploads):
                # Calculate the start and end positions of each chunk
                start = i * chunk_size
                end = min(start + chunk_size, file_size)

                # Move to the correct position in the file for each chunk
                await file.seek(start)

                # Read the chunk
                chunk = await file.read(end - start)

                # Prepare the data for the request
                data = aiohttp.FormData()
                data.add_field("job_id", str(job_id))
                data.add_field("file_type", file_type)
                data.add_field("total_chunks", str(n_uploads))
                data.add_field("chunk_index", str(i+1))
                data.add_field("session_id", session_id)

                # Add the file chunk to the form
                data.add_field(
                    "file",
                    chunk,
                    filename=file_path.name,
                    content_type="application/octet-stream"
                )

                async with aiohttp.ClientSession() as session:
                    self.status = f"Sending chunk {i + 1}/{n_uploads}..."
                    async with session.post(self.api_url + upload_link, headers=headers, data=data) as response:
                        if response.status == 200:
                            self.status = f"Chunk {i + 1}/{n_uploads} uploaded successfully"
                        else:
                            self.status = f"[Error] Failed to upload chunk {i + 1}: {await response.text()}"
                            raise Exception(f"Upload failed: {await response.text()}")

        self.status = "File upload completed."
        return {"message": "File uploaded successfully"}

    @ensure_login
    async def request_download_link(self, file_id: str):
        self.status = "Requesting download link..."
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"file_id": file_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/files/request-download/", headers=headers, json=params) as response:
                if response.status == 200:
                    self.status = "Download link received"
                    return await response.json()
                self.status = f"[Error] Failed to get download link: {await response.text()}"
                return None

    @ensure_login
    async def download_file(self, download_link: str, output_path: Path):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.status = f"Downloading file from {download_link} to {output_path}..."
        async with aiohttp.ClientSession() as session:
            async with session.get(self.api_url + download_link, headers=headers) as response:
                self.status = f"Awaiting response status..."
                if response.status == 200:
                    self.status = f"Downloading file to {output_path}..."
                    if os.path.exists(output_path) and os.access(output_path, os.W_OK):
                        self.status = f"[Warning] File {output_path} already exists and is writable."
                    else:
                        if os.path.exists(output_path):
                            self.status = f"[Error] File {output_path} is locked or not writable."
                            return False
                        else:
                            self.status = f"Creating file {output_path}..."
                    async with aiofiles.open(output_path, 'wb') as file:
                        self.status = f"Opened file {output_path} for writing..."
                        i = 0
                        async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                            self.status = f"Downloading chunk {i} of size {len(chunk)} bytes"
                            i += 1
                            await file.write(chunk)
                    self.status = f"File downloaded successfully to {output_path}"
                    return True
                else:
                    self.status = f"[Error] Failed to download file: {await response.text()}"
                    return False

    ##############################
    # Job related functions      #
    ############################## 
       
    @ensure_login
    async def get_job(self):
        header = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/jobs/request", headers=header) as response:
                if response.status == 200:
                    return await response.json()
                # If the server returns 204, it means there are no jobs available
                if response.status == 204:
                    return None
                print(f"[Error] Failed to get job: {await response.text()}")
                return None

    @ensure_login
    async def ping_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/ping", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to ping job: {await response.text()}")
                return None
    
    @ensure_login
    async def pause_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/pause", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to pause job: {await response.text()}")
                return None
        
    @ensure_login
    async def resume_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/resume", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to resume job: {await response.text()}")
                return None
    
    # Asynchronous version of the complete_job method
    @ensure_login
    async def complete_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/complete", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to complete job: {await response.text()}")
                return None
    
    @ensure_login
    async def cancel_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/cancel", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to cancel job: {await response.text()}")
                return None

    # Asynchronous version of the update_iterations method
    @ensure_login
    async def update_iterations(self, job_id: int, iterations: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id, "num_iterations": iterations}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/update-iterations", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to update iterations: {await response.text()}")
                return None

    @ensure_login
    async def update_entropy(self, job_id: int, entropy: float):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id, "entropy": entropy}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/update-entropy", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to update entropy: {await response.text()}")
                return None
 

    @ensure_login
    async def get_status(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/jobs/status", headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                print(f"[Error] Failed to get status: {await response.text()}")
                return None
    