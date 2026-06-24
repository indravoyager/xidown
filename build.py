import os
import sys
import shutil
import platform
import zipfile
import subprocess

def install_dependencies():
    # Ensure pyinstaller is installed
    try:
        import PyInstaller
        print(f"[Build] PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[Build] PyInstaller not found. Installing via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        except Exception as e:
            print(f"[Build] Failed to install PyInstaller: {e}")
            sys.exit(1)

def run_build():
    # Install dependencies first
    install_dependencies()

    # Determine paths and separator
    import customtkinter
    ctk_dir = os.path.dirname(customtkinter.__file__)
    
    # Path separator: ';' on Windows, ':' on Unix-like (Linux/macOS)
    sep = ";" if platform.system() == "Windows" else ":"
    
    # Base directories
    project_root = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(project_root, "assets")
    
    # Build command
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--name=xidown",
        "--onefile",
        "--windowed",
        f"--add-data={assets_dir}{sep}assets",
        f"--add-data={ctk_dir}{sep}customtkinter",
    ]
    
    # Add icon if available
    icon_path = os.path.join(assets_dir, "favicon.ico")
    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")
    else:
        print("[Build] Warning: favicon.ico not found, compiling without custom icon.")

    # Entry point
    entry_point = os.path.join(project_root, "xidown", "app.py")
    cmd.append(entry_point)
    
    print(f"[Build] Running compilation command:\n{' '.join(cmd)}")
    
    # Run PyInstaller
    try:
        subprocess.check_call(cmd)
        print("[Build] PyInstaller compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[Build] PyInstaller compilation failed with exit code: {e.returncode}")
        sys.exit(1)

    # Package the output into a zip file in a 'releases' folder
    package_release(project_root)

def package_release(project_root):
    dist_dir = os.path.join(project_root, "dist")
    releases_dir = os.path.join(project_root, "releases")
    os.makedirs(releases_dir, exist_ok=True)
    
    # Identify OS and Architecture
    os_system = platform.system().lower()
    if os_system == "darwin":
        os_name = "macos"
    else:
        os_name = os_system
        
    raw_arch = platform.machine().lower()
    if raw_arch in ["amd64", "x86_64"]:
        arch = "x64"
    elif raw_arch in ["i386", "i686", "x86"]:
        arch = "x86"
    elif "arm" in raw_arch or "aarch" in raw_arch:
        arch = "arm64"
    else:
        arch = raw_arch
        
    zip_name = f"xidown-{os_name}-{arch}.zip"
    zip_path = os.path.join(releases_dir, zip_name)
    
    print(f"[Build] Packaging application for {os_name} ({arch})...")
    
    # Target executable name
    exec_name = "xidown.exe" if os_system == "windows" else "xidown"
    exec_path = os.path.join(dist_dir, exec_name)
    
    if not os.path.exists(exec_path):
        # On macOS with --windowed, PyInstaller might generate dist/xidown.app folder instead of onefile executable
        mac_app_path = os.path.join(dist_dir, "xidown.app")
        if os_name == "macos" and os.path.exists(mac_app_path):
            print(f"[Build] macOS App Bundle found at: {mac_app_path}")
            # Zip the .app directory
            zip_directory(mac_app_path, zip_path)
            print(f"[Build] Packaged successfully to: {zip_path}")
            return
        else:
            print(f"[Build] Error: Compiled executable not found at: {exec_path}")
            sys.exit(1)
            
    # Zip the single executable
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(exec_path, exec_name)
            
            # Optional: Add README if it exists
            readme_path = os.path.join(project_root, "README.md")
            if os.path.exists(readme_path):
                zipf.write(readme_path, "README.md")
                
        print(f"[Build] Packaged successfully to: {zip_path}")
        print(f"[Build] Package size: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"[Build] Packaging failed: {e}")
        sys.exit(1)

def zip_directory(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Maintain relative path inside zip
                rel_path = os.path.relpath(file_path, os.path.dirname(folder_path))
                zipf.write(file_path, rel_path)

if __name__ == "__main__":
    run_build()
