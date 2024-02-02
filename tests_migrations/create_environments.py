"""This is required to run the migration tests in this folder."""
import platform
import subprocess

from constants import SUPPORTED_TOOLKIT_VERSIONS, TEST_DIR_ROOT, chdir


def create_environments():
    with chdir(TEST_DIR_ROOT):
        for version in SUPPORTED_TOOLKIT_VERSIONS:
            print(f"Creating environment for version {version}")
            environment_directory = f".venv{version}"
            if (TEST_DIR_ROOT / environment_directory).exists():
                print(f"Environment for version {version} already exists")
                continue
            subprocess.run(["python", "-m", "venv", environment_directory])
            if platform.system() == "Windows":
                subprocess.run([f"{environment_directory}/Scripts/pip", "install", f"cognite-toolkit=={version}"])
            else:
                subprocess.run([f"{environment_directory}/bin/pip", "install", f"cognite-toolkit=={version}"])
            print(f"Environment for version {version} created")


if __name__ == "__main__":
    create_environments()