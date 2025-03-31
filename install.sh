#!/bin/bash

# Function to install system dependencies (for Ubuntu/Debian-based systems)
install_system_dependencies() {
    echo "Installing system dependencies..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # For Linux-based systems
        apt-get update
        apt-get install -y python3 python3-pip curl git
        apt-get install -y libopenblas-dev liblapack-dev # For OpenBLAS

    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # For macOS
        brew install python3 curl git
        # Install xcode command line tools
        xcode-select --install
    fi
}

# Function to install Python dependencies
install_python_dependencies() {
    echo "Installing Python dependencies..."
    # Create a virtual environment called moe-venv
    python3 -m venv moe-venv
    # Activate it
    source moe-venv/bin/activate
    # Install the necessary Python libraries from requirements.txt
    pip install --upgrade pip
    pip install -r requirements.txt
}


# Function to clone the repository and build the binary
clone_and_build_binary() {
    # Check if the 'git' command is available
    if ! command -v git &> /dev/null; then
        echo "The 'git' command is not available. Please install Git and try again."
        exit 1
    fi

    # Check that "moe" binary does not already exist
    if [ -f "bin/moe" ]; then
        echo "Binary 'moe' already exists. Skipping the build process. If you want to rebuild, run 'rm ./bin/moe' in this folder and re-run this script."
        return
    fi

    echo "Cloning the EntropyMinimizerCpp repository and building the binary..."

    mkdir -p tmp
    cd tmp

    # Clone the repository
    git clone https://github.com/Aschie4589/EntropyMinimizerCpp

    # Change into the repository directory
    cd EntropyMinimizerCpp

    # Check for macOS (Accelerate) or Linux (OpenBLAS) for LAPACK setting
    if [[ "$OSTYPE" == "darwin"* ]]; then
        LAPACK="accelerate"
        PLATFORM="apple"
        echo "Detected OS: macOS. Using Accelerate for LAPACK. If Accelerate is not installed, this next step will fail."
    else
        LAPACK="openblas"
        PLATFORM="linux"
        echo "Detected Linux or other OS. Using OpenBLAS for LAPACK. If OpenBLAS is not available, this next step will fail."
    fi

    # Run the build process
    echo "Building the 'moe' binary..."
    make LAPACK=$LAPACK PLATFORM=$PLATFORM

    # Check if the build was successful
    if [ $? -ne 0 ]; then
        echo "The build process failed. Please check the error messages above."
        # cleanup
        echo "Will cleanup and exit..."
        cd ../..
        rm -rf tmp

        exit 1
    fi

    # Move the 'moe' binary to the ./bin directory
    mkdir -p ../../bin
    mv moe ../../bin/

    # Return to the original directory
    cd ../..

    # Echo a message to the user
    echo "The 'moe' binary has been built and placed in the 'bin' directory."
}

cleanup() {
    echo "Cleaning up..."
    # Deactivate the virtual environment
    deactivate
    # Remove the cloned repository
    rm -rf tmp
}


# Main script
echo "Starting the installation..."

# Step 1: Install system dependencies
install_system_dependencies

# Step 2: Install Python dependencies
install_python_dependencies

# Step 3: Download the binary
clone_and_build_binary

# Step 4: Cleanup
cleanup

echo "Installation complete. Run using ./run.sh"