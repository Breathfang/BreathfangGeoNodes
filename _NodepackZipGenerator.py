import os
import zipfile
import logging
from logging.handlers import RotatingFileHandler
import os
import pandas as pd
import shutil

log_file = os.path.join(".", "_NodepackZipGenerator.log")

# Trigger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create log file
handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=5)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Add formatter to handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
handler.setFormatter(formatter)

# Handler to logger
logger.addHandler(handler)
logger.addHandler(console_handler)

def main():
    node_version = input("Node Version: (example: v1.1.0-alpha): ")
    nodepack_name = f"Breathfang's Geometry Nodes Toolset Pack {node_version}"
    
    files = []
    
    # File that needs to be appended
    files.append(("Breathfang's Nodes.blend", f"Breathfang's Geometry Nodes Toolset Pack {node_version}.blend"))
    files.append(("Read Before Use Nodes.txt", "READ THIS BEFORE USE NODES.txt"))
    files.append(("blender_assets.cats.txt", "blender_assets.cats.txt"))

    # Create zip
    with zipfile.ZipFile(f"{nodepack_name}.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for file in files:
            _arcname = file[1] if file[1] else file[0]
            zipf.write(file[0], arcname=_arcname)
            logger.info("Inserted %s into zip" % file[0])
    
    logger.info("Done!")
try:
    main()
    input("Press enter to exit...")
except Exception as e:
    logger.error(f"Error: {e}")
    logger.error("Traceback: %s", e, exc_info=True)
    input("Press enter to exit...")