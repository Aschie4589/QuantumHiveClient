import requests
from pathlib import Path

class APIHandler:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.access_token = None
        self.refresh_token = None

    ##############################
    # Authentication functions   #
    ##############################

    def login(self, uid: str, pwd: str):
        # Log in to get the token
        login_data = {"username": uid, "password": pwd}
        login_response = requests.post(f"{self.api_url}/auth/login", data=login_data)
        if login_response.status_code != 200:
            print(f"[Error] Failed to log in: {login_response.text}")
            return False
        login_info = login_response.json()
        self.access_token = login_info["access_token"]
        self.refresh_token = login_info["refresh_token"]
        return True    

    def refresh(self):
        # Refresh the token
        header = {"refresh": self.refresh_token}
        refresh_response = requests.post(f"{self.api_url}/auth/refresh", headers=header)
        if refresh_response.status_code != 200:
            print(f"[Error] Failed to refresh token: {refresh_response.text}")
            return False
        refresh_info = refresh_response.json()
        self.access_token = refresh_info["access_token"]
        self.refresh_token = refresh_info["refresh_token"]
        return True

    def ensure_login(func):
        def wrapper(self, *args, **kwargs): 
            # Ping the server at /auth/ping to check if the access token is still valid
            header = {"Authorization": f"Bearer {self.access_token}"}
            ping_response = requests.get(f"{self.api_url}/auth/ping", headers=header)
            if ping_response.status_code == 401:
                # Access token is invalid, try to refresh it
                if not self.refresh():
                    # Refresh failed, return False. TODO: raise an exception? Ask the user to log in again?
                    return False
            # We have a valid access token, call the function
            return func(self, *args, **kwargs)
        return wrapper
    
    def check_login(self):
        # Ping the server at /auth/ping to check if the access token is still valid
        header = {"Authorization": f"Bearer {self.access_token}"}
        ping_response = requests.get(f"{self.api_url}/auth/ping", headers=header)
        if ping_response.status_code == 401:
            # Access token is invalid, try to refresh it
            if not self.refresh():
                # Refresh failed, return False. TODO: raise an exception? Ask the user to log in again?
                return False
        return True

    ##############################
    # Channel related functions  #
    ##############################

    @ensure_login
    def create_channel(self, input_dim: int, output_dim: int, num_kraus, method: str = "haar"):
        # This requires admin access
        header = {"Authorization": f"Bearer {self.access_token}"}
        data = {"input_dimension": input_dim, "output_dimension": output_dim, "num_kraus": num_kraus, "method": method}
        response = requests.post(f"{self.api_url}/channels/create", headers=header, data=data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to create channel: {response.text}, Status code: {response.status_code}")
        return None
    
    @ensure_login
    def list_channels(self):
        header = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(f"{self.api_url}/channels/list", headers=header)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to list channels: {response.text}")
        return None
    
    @ensure_login
    def update_channel_minimization_attempts(self, channel_id, attempts):
        header = {"Authorization": f"Bearer {self.access_token}"}
        min_attempts_data = {"channel_id": channel_id, "attempts": attempts}
        response = requests.post(f"{self.api_url}/channels/update-minimization-attempts", headers=header, data=min_attempts_data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to update minimization attempts: {response.text}")
        return None

    ##############################
    # File related functions     #
    ##############################

    @ensure_login
    def request_upload_link(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.post(f"{self.api_url}/files/request-upload", headers=headers)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to get upload link: {response.text}")
        return None

    @ensure_login
    def upload_file(self, job_id: int, file_type : str , file_path: Path, upload_link: str):
        # Upload a file to the server. Upload link is relative to the server URL (i.e it is of the form /files/upload/{id})
        with open(file_path, "rb") as file:
            files = {"file": file}
            headers = {"Authorization": f"Bearer {self.access_token}"}
            data = {"job_id": job_id, "file_type": file_type}
            response = requests.post(self.api_url+upload_link, files=files, headers=headers, data=data)
            if response.status_code == 200:
                return response.json()
            print(f"[Error] Failed to upload file: {response.text}")
            return None
        
    @ensure_login
    def request_download_link(self, file_id: str):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"file_id": file_id}
        response = requests.post(f"{self.api_url}/files/request-download/", headers=headers, json=params)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to get download link: {response.text}")
        return None

    @ensure_login
    def download_file(self, download_link: str, output_path: Path):
        # download link is relative to api_url
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(self.api_url+download_link, headers=headers)
        if response.status_code == 200:
            with open(output_path, "wb") as file:
                file.write(response.content)
            return True
        print(f"[Error] Failed to download file: {response.text}")
        return False

    ##############################
    # Job related functions      #
    ############################## 
       
    @ensure_login
    def get_job(self):
        header = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(f"{self.api_url}/jobs/request", headers=header)
        if response.status_code == 200:
            return response.json()
        # If the server returns 204, it means there are no jobs available
        if response.status_code == 204:
            return None
        print(f"[Error] Failed to get job: {response.text}")
        return None

    @ensure_login
    def ping_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        response = requests.post(f"{self.api_url}/jobs/ping", headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to ping job: {response.text}")
        return None
    
    @ensure_login
    def pause_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        response = requests.post(f"{self.api_url}/jobs/pause", headers=headers, data = data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to pause job: {response.text}")
        return None
    
    @ensure_login
    def resume_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        response = requests.post(f"{self.api_url}/jobs/resume", headers=headers, data = data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to resume job: {response.text}")
        return None
    
    @ensure_login
    def complete_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        response = requests.post(f"{self.api_url}/jobs/complete", headers=headers, data = data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to complete job: {response.text}")
        return None
    
    @ensure_login
    def cancel_job(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        response = requests.post(f"{self.api_url}/jobs/cancel", headers=headers, data = data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to cancel job: {response.text}")
        return None

    @ensure_login
    def update_iterations(self, job_id: int, iterations: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id, "num_iterations": iterations}
        response = requests.post(f"{self.api_url}/jobs/update-iterations", headers=headers, data = data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to update iterations: {response.text}")
        return None

    @ensure_login
    def update_entropy(self, job_id: int, entropy: float):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id, "entropy": entropy}
        response = requests.post(f"{self.api_url}/jobs/update-entropy", headers=headers, data = data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to update entropy: {response.text}")
        return None
 

    @ensure_login
    def get_status(self, job_id: int):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"job_id": job_id}
        response = requests.post(f"{self.api_url}/jobs/status", headers=headers, data = data)
        if response.status_code == 200:
            return response.json()
        print(f"[Error] Failed to get status: {response.text}")
        return None
    