from PIL import Image
import os

def resize_icon():
    # Setup path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_path = os.path.join(base_dir, "assets", "favicon.ico")
    
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path)
            # Create a list of sizes for multi-resolution ICO
            icon_sizes = [(16,16), (24, 24), (32,32), (48,48), (64,64), (128,128), (256,256)]
            
            # Save the image as a multi-size ICO
            img.save(icon_path, format="ICO", sizes=icon_sizes)
            print("Favicon successfully resized to multiple sizes for better scaling!")
        except Exception as e:
            print(f"Error processing favicon: {e}")
    else:
        print("Favicon not found at:", icon_path)

if __name__ == "__main__":
    resize_icon()
