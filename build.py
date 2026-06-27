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
        
    try:
        from xidown.core.version import APP_VER
        version = APP_VER.replace("v.", "v") # e.g. "v0.2517"
    except ImportError:
        version = "v0.0.0"

    # Naming convention: xidown-[version]-[os]-[arch][-portable].zip
    # We add "-portable" for Windows to distinguish it from the setup.exe
    if os_name == "windows":
        zip_name = f"xidown-{version}-{os_name}-{arch}-portable.zip"
    else:
        zip_name = f"xidown-{version}-{os_name}-{arch}.zip"
        
    zip_path = os.path.join(releases_dir, zip_name)
    
    print(f"[Build] Packaging application for {os_name} ({arch})...")
    
    # Nuitka outputs to dist/app.dist/ for standalone mode
    # The folder name is based on the entry point filename: app.py -> app.dist
    nuitka_output = os.path.join(dist_dir, "app.dist")
    
    # Fallback: check other possible output names
    if not os.path.exists(nuitka_output):
        # On macOS with app bundle, it might just be .app
        if os_name == "macos" and os.path.exists(os.path.join(dist_dir, "xidown.app")):
            nuitka_output = os.path.join(dist_dir, "xidown.app")
        else:
            for item in os.listdir(dist_dir):
                if (item.endswith(".dist") or item.endswith(".app")) and os.path.isdir(os.path.join(dist_dir, item)):
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
    if os_name == "macos" and nuitka_output.endswith(".app"):
        # If Nuitka output is directly the .app bundle
        shutil.copytree(nuitka_output, os.path.join(app_folder_path, "xidown.app"))
        print(f"[Build] Copied {nuitka_output} bundle into release folder.")
    else:
        # For Windows/Linux or if output is a .dist folder, copy all contents
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
        
        # Create portable.txt ONLY for the zip package (portable version)
        portable_txt_path = os.path.join(app_folder_path, "portable.txt")
        try:
            with open(portable_txt_path, "w") as f:
                f.write("This file tells xidown to run in portable mode and save data in this folder.")
        except: pass
        
        safe_zip_directory(app_folder_path, zip_path)
        
        # Remove portable.txt so the Inno Setup installer (which runs next) doesn't include it
        if os.path.exists(portable_txt_path):
            try: os.remove(portable_txt_path)
            except: pass
            
        print(f"[Build] Packaged successfully to: {zip_path}")
        print(f"[Build] Package size: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
        
        # 4.5 Build Inno Setup installer if on Windows
        if os_name == "windows":
            build_inno_setup(app_folder_path, releases_dir, project_root, arch)
            
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

def build_inno_setup(app_folder_path, releases_dir, project_root, arch):
    try:
        from xidown.core.version import APP_VER
        version = APP_VER.replace("v.", "").replace("v", "")
    except ImportError:
        version = "0.0.0"
        
    iss_content = f"""
[Setup]
AppName=xidown
AppVersion={version}
AppPublisher=indravoyager
DefaultDirName={{localappdata}}\\Programs\\xidown
DefaultGroupName=xidown
OutputDir={releases_dir}
OutputBaseFilename=xidown-v{version}-windows-{arch}-setup
Compression=lzma2
SolidCompression=yes
SetupIconFile={app_folder_path}\\assets\\favicon.ico
WizardImageFile={app_folder_path}\\assets\\installer_side.bmp
UninstallDisplayIcon={{app}}\\xidown.exe
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{app_folder_path}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\xidown"; Filename: "{{app}}\\xidown.exe"
Name: "{{autodesktop}}\\xidown"; Filename: "{{app}}\\xidown.exe"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\xidown.exe"; Description: "{{cm:LaunchProgram,xidown}}"; Flags: nowait postinstall skipifsilent
"""
    iss_path = os.path.join(project_root, "xidown.iss")
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(iss_content)
        
    print(f"[Build] Created Inno Setup script at {iss_path}")
    
    # Check if ISCC is available (Windows only)
    iscc_paths = [
        r"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
        r"C:\\Program Files\\Inno Setup 6\\ISCC.exe"
    ]
    iscc_exe = None
    for p in iscc_paths:
        if os.path.exists(p):
            iscc_exe = p
            break
            
    if iscc_exe:
        print("[Build] Found Inno Setup compiler. Compiling installer...")
        try:
            subprocess.check_call([iscc_exe, iss_path])
            print("[Build] Installer compilation completed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"[Build] Installer compilation failed: {e}")
    else:
        print("[Build] Inno Setup compiler not found. Skipping installer creation.")

def zip_directory(folder_path, zip_path):
    # Using shutil.make_archive handles permissions and symlinks much better than standard zipfile module
    # We create the archive in the directory above with the desired base name
    base_name = os.path.splitext(zip_path)[0]
    shutil.make_archive(base_name, 'zip', os.path.dirname(folder_path), os.path.basename(folder_path))
    
    # shutil creates a zip with the folder name as the root directory inside the zip.
    # Since our folder is "xidown_pkg_temp", let's rename the folder temporarily to "xidown" before zipping
    pass # Re-implemented below for clarity

def safe_zip_directory(folder_path, zip_path):
    parent_dir = os.path.dirname(folder_path)
    temp_rename = os.path.join(parent_dir, "xidown")
    
    # Rename folder to 'xidown' so the zip structure has 'xidown/' at the root
    if os.path.exists(temp_rename):
        shutil.rmtree(temp_rename)
    os.rename(folder_path, temp_rename)
    
    base_name = os.path.splitext(zip_path)[0]
    shutil.make_archive(base_name, 'zip', parent_dir, "xidown")
    
    # Rename it back so cleanup doesn't fail
    os.rename(temp_rename, folder_path)

if __name__ == "__main__":
    run_build()
