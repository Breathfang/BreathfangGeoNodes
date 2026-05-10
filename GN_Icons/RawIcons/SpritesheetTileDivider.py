from PIL import Image
import logging
from logging.handlers import RotatingFileHandler
import os

# Logger
log_file = os.path.join(".", "_ImageDivider.log")

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


def divide_image(image_path, rows, cols, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    img = Image.open(image_path)
    img_width, img_height = img.size

    # Check is it divided completely or not
    if img_width % cols != 0 or img_height % rows != 0:
        logger.warning("⚠ WARNING: Image division is not evenly divided by rows and columns.")
        
        print("Some tiles may have different sizes about 0-1 pixel.")
        print("Do you want to continue? (y/n)")
        
        if input() != "y":
            logger.exception("Process stopped by user due to image division is not evenly divided by rows and columns.")
            return
    else:
        logger.info("This process will now divide the image into tiles.")
    
    
    tile_width = img_width // cols
    tile_height = img_height // rows

    count = 0
    for i in range(rows):
        for j in range(cols):
            left = j * tile_width
            upper = i * tile_height
            right = (j + 1) * tile_width
            lower = (i + 1) * tile_height
            
            # crop tile
            tile = img.crop((left, upper, right, lower))
            
            # check is it all transparent or not
            if tile.getbbox():
                tile.save(f"{output_folder}/tile_{count}.png")
                logger.info(f"Tile {count} saved.")
            else:
                logger.info(f"Tile {count} is transparent. Skipping...")
            
            count += 1

    logger.info(f"Done! Created {count} tiles.")

def resize_image(image_path, new_width, new_height, output_path):
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            
        logger.info(f"Resizing {image_path} to {new_width}x{new_height}...")
        img = Image.open(image_path)
        filename = os.path.basename(image_path)
        img = img.resize((new_width, new_height))
        img.save(f"{output_path}/{filename}")
    except FileNotFoundError as e:
        logger.error(f"File not found: {image_path}")
        logger.error("Traceback: %s", e, exc_info=True)
        return
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error("Traceback: %s", e, exc_info=True)
        return

# Main
try:
    # Check is spritesheet.png exists or not
    if not os.path.exists("spritesheet.png"):
        logger.error("spritesheet.png not found.")
        logger.error("Process stopped due to spritesheet.png not found.")
        input("Press enter to exit...")
    
    # Get spritesheet size
    img = Image.open("spritesheet.png")
    width, height = img.size
    logger.info(f"Image size: {width}x{height}")
    
    #set divisor
    u, v = 8, 8
    
    divide_image("spritesheet.png", u, v, ".output")
    logger.info("Now resizing tiles into separated folder...")
    
    # Get all files in .output folder
    files = os.listdir(".output")
    logger.info(f"Found {len(files)} files in .output folder.")
    target_size = (int(width/(u*4)), int(height/(v*4)))
    logger.info(f"Target resized size in separated folder: {target_size[0]}x{target_size[1]}")
    
    for i in files:
        resize_image(f".output/{i}", target_size[0], target_size[1], f".output_resized")
    
    logger.info("Done!")
    
    input("Press enter to exit...")
except Exception as e:
    logger.error(f"Error: {e}")
    logger.error("Process stopped due to error.")
    logger.error("Traceback: %s", e, exc_info=True)
    input("Press enter to exit...")