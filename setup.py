import os
import subprocess
import sys
from time import sleep

# Determine the base directory (where this script resides)
base_path = os.path.dirname(os.path.abspath(__file__))

# Folders to process (llm, ocr, poppler, and the base directory itself)
folders = [
    os.path.join(base_path, 'llm'),
    os.path.join(base_path, 'ocr'),
    os.path.join(base_path, 'poppler'),
    base_path
]

# Function to create a .gitignore if it doesn't exist
def create_gitignore(folder):
    gitignore_path = os.path.join(folder, '.gitignore')
    if os.path.exists(gitignore_path):
        print(f".gitignore already exists in {folder}")
    else:
        print(f"Creating .gitignore in {folder}")
        try:
            with open(gitignore_path, 'w') as f:
                f.write("""__pycache__/
venv/
""")
        except OSError as e:
            print(f"Failed to create .gitignore in {folder}: {e}")

# Function to create a virtual environment if missing
def create_virtualenv(folder):
    venv_path = os.path.join(folder, 'venv')
    if not os.path.exists(folder):
        print(f"Error: Folder {folder} does not exist.")
        sys.exit(1)

    if os.path.exists(venv_path):
        print(f"Virtual environment already exists in {venv_path}")
    else:
        print(f"Creating virtual environment in {venv_path}")
        try:
            subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to create virtual environment in {venv_path}: {e}")

# Collect all requirements.txt paths to install globally later
def gather_requirements(folders):
    req_files = []
    for folder in folders:
        req_path = os.path.join(folder, 'requirements.txt')
        if os.path.isfile(req_path):
            req_files.append(req_path)
        else:
            print(f"No requirements.txt found in {folder}, skipping.")
    return req_files

# Main setup loop
def main():
    requirements = []
    for folder in folders:
        print(f"\nProcessing folder: {folder}")
        create_gitignore(folder)
        create_virtualenv(folder)
        # Pause briefly to avoid overwhelming the system
        sleep(1)

    # After venv creation, gather all requirements
    requirements = gather_requirements(folders)

    # Install all requirements globally
    if requirements:
        for req in requirements:
            print(f"Installing global requirements from {req}")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error installing from {req}: {e}")
    else:
        print("No global requirements to install.")

    print("\nSetup completed successfully.")

    # Instructions for manual steps
    instructions = """
Setup Script Instructions:

This script:
1. Creates a `.gitignore` in each specified folder if missing.
2. Creates a Python virtual environment (`venv`) in each folder if missing.
3. Installs all Python packages globally (not inside the venvs) based on discovered `requirements.txt` files.

To use:
- Run this script with your system Python: `python setup_env.py`
- Ensure you have write permissions to create venvs and install packages globally.

Manual dependencies:
- Ollama & Gemma3:12b: https://ollama.com/download
- Poppler: https://poppler.freedesktop.org/bin
"""
    print(instructions)

if __name__ == '__main__':
    main()