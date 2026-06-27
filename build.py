import os
import sys
import shutil
import platform
import zipfile
import subprocess

def install_dependencies():
    # Ensure nuitka is installed
    try:
        from nuitka.Version import getNuitkaVersion
        print(f"[Build] Nuitka version: {getNuitkaVersion()}")
    except ImportError:
        print("[Build] Nuitka not found. Installing via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka", "ordered-set"])
        except Exception as e:
            print(f"[Build] Failed to install Nuitka: {e}")
            sys.exit(1)

def run_build():
    # Install dependencies first
    install_dependencies()

    # Determine paths
    import customtkinter
    ctk_dir = os.path.dirname(customtkinter.__file__)
    
    # Base directories
    project_root = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(project_root, "assets")
    
    # Build command using Nuitka
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=tk-inter",
        f"--output-dir={os.path.join(project_root, 'dist')}",
        "--output-filename=xidown",
        f"--include-data-dir={assets_dir}=assets",
        f"--include-data-dir={ctk_dir}=customtkinter",
        "--assume-yes-for-downloads",
    ]
    
    # Platform-specific options
    if platform.system() == "Windows":
        cmd.append("--windows-console-mode=disable")
        # Add icon if available
        icon_path = os.path.join(assets_dir, "favicon.ico")
        if os.path.exists(icon_path):
            cmd.append(f"--windows-icon-from-ico={icon_path}")
        else:
            print("[Build] Warning: favicon.ico not found, compiling without custom icon.")
    elif platform.system() == "Darwin":
        cmd.append("--macos-create-app-bundle")
        icon_path = os.path.join(assets_dir, "favicon.ico")
        if os.path.exists(icon_path):
            cmd.append(f"--macos-app-icon={icon_path}")

    # Entry point
    entry_point = os.path.join(project_root, "xidown", "app.py")
    cmd.append(entry_point)
    
    print(f"[Build] Running Nuitka compilation command:\n{' '.join(cmd)}")
    
    # Run Nuitka
    try:
        subprocess.check_call(cmd)
        print("[Build] Nuitka compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[Build] Nuitka compilation failed with exit code: {e.returncode}")
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
    
    # Nuitka outputs to dist/app.dist/ for standalone mode
    # The folder name is based on the entry point filename: app.py -> app.dist
    nuitka_output = os.path.join(dist_dir, "app.dist")
    
    # Fallback: check other possible output names
    if not os.path.exists(nuitka_output):
        # Try finding any .dist folder
        for item in os.listdir(dist_dir):
            if item.endswith(".dist") and os.path.isdir(os.path.join(dist_dir, item)):
                nuitka_output = os.path.join(dist_dir, item)
                break
    
    if not os.path.exists(nuitka_output):
        print(f"[Build] Error: Nuitka output directory not found. Expected: {nuitka_output}")
        print(f"[Build] Contents of dist/: {os.listdir(dist_dir) if os.path.exists(dist_dir) else 'NOT FOUND'}")
        sys.exit(1)
    
    print(f"[Build] Found Nuitka output at: {nuitka_output}")
    
    # Create a temporary directory for packaging
    app_folder_path = os.path.join(dist_dir, "xidown_pkg_temp")
    if os.path.exists(app_folder_path):
        try:
            shutil.rmtree(app_folder_path)
        except Exception:
            pass
    os.makedirs(app_folder_path, exist_ok=True)
    
    # 1. Copy the compiled output into our temporary release folder
    if os_name == "macos":
        app_bundle = os.path.join(dist_dir, "xidown.app")
        if os.path.exists(app_bundle):
            shutil.copytree(app_bundle, os.path.join(app_folder_path, "xidown.app"))
            print("[Build] Copied xidown.app bundle into release folder.")
        else:
            # Fallback to Nuitka output directory
            for item in os.listdir(nuitka_output):
                s = os.path.join(nuitka_output, item)
                d = os.path.join(app_folder_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            print("[Build] Copied Nuitka output into release folder.")
    else:
        # For Windows/Linux, copy all contents from Nuitka output
        for item in os.listdir(nuitka_output):
            s = os.path.join(nuitka_output, item)
            d = os.path.join(app_folder_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        print("[Build] Copied all compiled files and folders into release folder.")
            
    # 2. Copy README.md into the release folder before zipping
    readme_path = os.path.join(project_root, "README.md")
    if os.path.exists(readme_path):
        try:
            shutil.copy(readme_path, os.path.join(app_folder_path, "README.md"))
            print("[Build] Copied README.md into release folder.")
        except Exception as e:
            print(f"[Build] Warning: Failed to copy README.md: {e}")
            
    # 3. Copy LICENSE into the release folder before zipping
    license_path = os.path.join(project_root, "LICENSE")
    if os.path.exists(license_path):
        try:
            shutil.copy(license_path, os.path.join(app_folder_path, "LICENSE"))
            print("[Build] Copied LICENSE into release folder.")
        except Exception as e:
            print(f"[Build] Warning: Failed to copy LICENSE: {e}")
            
    # 4. Zip the entire folder
    try:
        print(f"[Build] Zipping folder: {app_folder_path} to {zip_path}...")
        zip_directory(app_folder_path, zip_path)
        print(f"[Build] Packaged successfully to: {zip_path}")
        print(f"[Build] Package size: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"[Build] Packaging failed: {e}")
        sys.exit(1)
    finally:
        # 5. Clean up our temporary release folder
        if os.path.exists(app_folder_path):
            try:
                shutil.rmtree(app_folder_path)
            except Exception as e:
                print(f"[Build] Warning: Failed to clean up temporary release folder: {e}")

def zip_directory(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Maintain relative path inside zip, prefixing with 'xidown/'
                rel_path = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, os.path.join("xidown", rel_path))

if __name__ == "__main__":
    run_build()
