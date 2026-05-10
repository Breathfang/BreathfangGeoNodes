import logging
from logging.handlers import RotatingFileHandler
import os
import pandas as pd
import shutil

log_file = os.path.join(".", "_UpdateRawIcons.log")

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


"""
Start Program
"""

def main():
    # Check is .output_resized empty or not
    if os.path.exists("raw_icons/.output_resized"):
        logger.info(".output_resized is not empty.")
    else:
        logger.error(".output_resized is empty.")
        logger.error("Process stopped due to spritesheet.png not found.")
        logger.info("Try to run 'raw_icons/image_divider.py' first.")
        input("Press enter to exit...")
        return
    
    spritesheet_index = 0

    while True:
        try:
            spritesheet_index = int(input("Spritesheet index (0-3):"))
            
            if spritesheet_index < 0 or spritesheet_index > 3:
                logger.error("Invalid index. Try again.")
                continue
            else:
                break
        except ValueError as e:
            logger.error(f"Inputted non-integer value: {e}")
            logger.error("Traceback: %s", e, exc_info=True)
    
    # Fetch _UpdateRawIconMappings.csv
    target_files = []
    files_output = []
    
    try:
        df = pd.read_csv("_UpdateRawIconMappings.csv")
        for i in range(len(df)):
            if df["mapping_spritesheet_part"][i] == spritesheet_index:
                target_files.append(df["file_output"][i])
                files_output.append(df["target_file"][i])
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error("Traceback: %s", e, exc_info=True)
        input("Press enter to exit...")
        return
    
    # Check is it empty or not and not nan
    target_files_len = len([i for i in files_output if not pd.isna(i)])
    logger.info(f"Found {target_files_len} mapping to update.")
    
    if target_files_len == 0:
        logger.error("Mapping file is empty for this spritesheet index given.")
        logger.error("Process stopped due to mapping file is empty.")
        input("Press enter to exit...")
        return
    
    # Show as table to view before attempt
    logger.info("Target files to update:")
    for i in range(len(target_files)):
        
        #skip nan
        if pd.isna(target_files[i]) or pd.isna(files_output[i]):
            continue
        
        logger.info(f"{i+1}. {target_files[i]} => {files_output[i]}")
        
    confirm = input("Are you sure? (y/n): ")
    
    if confirm.lower() != "y":
        logger.info("Process stopped.")
        input("Press enter to exit...")
        return
    
    # Backup before it being updated by copying to ./backup_icons
    if not os.path.exists("backup_icons"):
        os.makedirs("backup_icons")
        
    for i in range(len(target_files)):
        
        #skip nan
        if pd.isna(target_files[i]) or pd.isna(files_output[i]):
            continue
        
        try:
            # Check is it exists or not before copy
            if not os.path.exists(f"{files_output[i]}.png"):
                logger.error(f"{files_output[i]}.png not found. Skipping...")
                continue
            
            shutil.copyfile(f"{files_output[i]}.png", f"backup_icons/{files_output[i]}.png")
            logger.info(f"Backup {files_output[i]}.png")
        except FileNotFoundError as e:
            logger.error(f"Backup Failed: File not found: {files_output[i]}.png")
            pass
    
    #Overwrite target files
    for i in range(len(target_files)):
        
        #skip nan
        if pd.isna(target_files[i]) or pd.isna(files_output[i]):
            continue
        
        try:
            # Check is it exists or not before copy
            if not os.path.exists(f"raw_icons/.output_resized/{target_files[i]}.png"):
                logger.error(f"raw_icons/.output_resized/{target_files[i]}.png not found. Skipping...")
                continue
            
            shutil.copyfile(f"raw_icons/.output_resized/{target_files[i]}.png", f"{files_output[i]}.png")
            
            logger.info(f"Updated {files_output[i]}.png, gathered from raw_icons/.output_resized/{target_files[i]}.png")
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.error("Traceback: %s", e, exc_info=True)
            input("Press enter to exit...")
            return
    
    # Check is .output_resized empty or not
    input("Press enter to exit...")
    
    # Get all files in .output_resized folder
    files = os.listdir("raw_icons/.output_resized")

try:
    main()
except Exception as e:
    logger.error(f"Error: {e}")
    logger.error("Traceback: %s", e, exc_info=True)
    input("Press enter to exit...")