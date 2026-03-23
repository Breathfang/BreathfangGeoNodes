import subprocess
import importlib.util
import sys
import traceback

min_py = (3, 13)
min_py_ver = ".".join(map(str, min_py))

# Check python version
def main():
    print("Check python version...")
    print("Python version minimum: %s" % min_py_ver)
    print("Your current python version: %s" % sys.version)
    print("Your current environment: %s" % sys.executable)

    if not min_py <= sys.version_info:
        raise Exception("Python version must be 3.%s or higher." % min_py_ver)

    # Confirm if you want to install required packages
    confirm = input("Do you want to install required packages? (y/n): ")

    if confirm != "y":
        print("Process stopped by user.")
        input("Press enter to exit...")
        return

    # Required packages
    packages = ["sphinx", "sphinx-autobuild", "sphinx_rtd_theme", "pandas", "logging", "sympy", "numpy"]

    for package in packages:
        spec = importlib.util.find_spec(package)
        
        # Check is it installed or not
        if spec is None:
            subprocess.run(["pip", "install", package])
        else:
            print(f"{package} is already installed. Checking for updates...")
            subprocess.run(["pip", "install", "--upgrade", package])
        
    print("All packages has been installed.")
    input("Press enter to exit...")
    return

try:    
    main()
except Exception as e:
    print("Traceback: %s", traceback.format_exc())
    input("Press enter to exit...")