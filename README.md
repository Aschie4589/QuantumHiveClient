Structure of the client.

worker-client/
│── bin/                      # Precompiled binary lives here
│   ├── moe                   # Compiled executable for computation. Originally empty.
│── src/                      # Python source code
│   ├── job_handler.py        # Handles job fetching & result submission
│   ├── process_manager.py    # Calls the binary and handles results
│── config/                   # Configuration files
│   ├── settings.json         # API URL, paths, etc.
│── install.sh                # Installation script (Bash or Python)
│── requirements.txt          # Python dependencies
│── README.md                 # Documentation
|── moe.py                    # Main script. Requires the python packages to be installed (or the venv to be activated), and the moe executable. Setup using install.sh, run using run.sh