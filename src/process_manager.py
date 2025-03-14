import os
import asyncio
# Process manager is responsible for running the command line moe commands and managing the output

class ProcessManager():
    def __init__(self, executable_path: str = "./bin/moe"):
        self.executable_path = executable_path
        if not self.check_executable():
            raise Exception("Executable not found")
        pass

        self.logging = False
        self.printing = True
        self.stdout_queue = asyncio.Queue()
        self.stderr_queue = asyncio.Queue()

        self.process = None
    
    def check_executable(self):
        if not os.path.exists(self.executable_path):
            print(f"[Error] Executable not found: {self.executable_path}")
            return False
        return True

    async def run_vector_generation(self, N: int, output_path: str):
        command = [self.executable_path, "vector", "-N", str(N), "-o", output_path]
        if not self.printing:
            command.append("-s")
        if self.logging:
            command.append("-l")
        return await self.run_process(command)

    async def run_kraus_generation(self, N: int, d: int, output_path: str):
        command = [self.executable_path, "kraus", "haar", "-d", str(d), "-N", str(N), "-o", output_path]
        if not self.printing:
            command.append("-s")
        if self.logging:
            command.append("-l")
        return await self.run_process(command)

    async def run_singleshot_minimization(self, output_path: str, vector_path: str, kraus_path: str, predict: bool = False, target_entropy: float = -1.0, iterations: int = 0, checkpointing: bool = False, checkpoint_path: str = "./checkpoint.dat", checkpoint_interval: int = 100):
        command = [self.executable_path, "singleshot", "-v", vector_path, "-k", kraus_path, "-S","-o", output_path]
        if predict and target_entropy > 0:
            command.append("-p")
            command.append("-t")
            command.append(str(target_entropy))
        if iterations > 0:
            command.append("-i")
            command.append(str(iterations))
        if checkpointing:
            command.append("-c")
            if checkpoint_path:
                command.append("-cf")
                command.append(checkpoint_path)
            if checkpoint_interval > 0:
                command.append("-ci")
                command.append(str(checkpoint_interval))
        if not self.printing:
            command.append("-s")
        if self.logging:
            command.append("-l")
        return await self.run_process(command)

    async def run_process(self, command: list):
        # Start the subprocess asynchronously
        if not self.process:
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ) # the await simply waits for the process to be created

    # Asynchronously read stdout and stderr and put them into
    # the respective queues
        async def read_output():
            while True:
                line = await self.process.stdout.readline()
                if not line:  # EOF
                    break
                line_decoded = line.decode('utf-8').rstrip()
                await self.stdout_queue.put(line_decoded)

        async def read_error():
            while True:
                line = await self.process.stderr.readline()
                if not line:  # EOF
                    break
                line_decoded = line.decode('utf-8').rstrip()
                await self.stderr_queue.put(line_decoded)

        # Run the output readers
        await asyncio.gather(read_output(), read_error())

        # Wait for the process to finish and get the return code
        return_code = await self.process.wait()
        # reset the process
        self.process = None

        # return the result
        if return_code != 0:
            return False, None, f"Process failed with return code {return_code}"
        return True, "Process completed successfully", None
    
    def stop_process(self):
        # Just send sigterm to the process, it should handle it
        if self.process:
            self.process.terminate()
