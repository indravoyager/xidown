import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Iterable, List, Union

try:
    from xidown.core.version import APP_NAME, APP_VER
    from xidown.core.constants import FAVICON_PATH
    APP_VER = APP_VER.replace("v.", "v")  # v.X.X -> vX.X
except ImportError:
    APP_NAME = "xidown"
    APP_VER = "v0.0.0-null"  # v0 with '-null' suffix
    FAVICON_PATH = None

# Base directories
ROOT_DIR = Path(__file__).absolute().parent
ASSETS_DIR = ROOT_DIR / "assets"
DIST_DIR = ROOT_DIR / "dist"
RELEASES_DIR = ROOT_DIR / "releases"
ICON_PATH = ROOT_DIR / FAVICON_PATH \
    if FAVICON_PATH                 \
    else ASSETS_DIR / "favicon.ico"

# These are the important part for this app builder
# Only change if and only if needed or project migration
APP_ENTRY_POINT = ROOT_DIR / APP_NAME / "app.py"

EXEC_PATH = sys.executable
REQUIRED_DEPS = {
    "nuitka",
    "ordered-set"
}
# Extra files to be included to the release folder before zipping
EXTRA_FILES = {
    ROOT_DIR / "README.md",
    ROOT_DIR / "LICENSE"
}

def normalize_arch(machine: str) -> str:
    """
    Normalize `platform.machine()` value to one of 'x64', 'x86', or 'arm64';
    based on current system.
    """
    machine = machine.lower()
    if machine in ["amd64", "x86_64"]:
        return "x64"
    elif machine in ["i386", "i686", "x86"]:
        return "x86"
    elif machine.startswith(("arm", "aarch")):
        return "arm64"
    return machine

def check_dependencies(deps: Iterable[str]) -> List[str]:
    deps = set(deps)
    if not deps: return []

    cmd = [EXEC_PATH, "-m", "pip", "freeze"]
    available_deps = set()

    try:
        with subprocess.Popen(
            cmd,
            bufsize=1,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        ) as proc:
            assert proc.stdout is not None

            for line in proc.stdout:
                package = line.partition("==")[0].strip()
                if package in deps:
                    print(f"[Build] Dependency installed: {package}")
                    available_deps.add(package)

            returncode = proc.wait()

        if returncode != 0:
            print(
                f"[Build] Warning: pip freeze exited with code {returncode}",
                file=sys.stderr,
            )
            return []

    except (OSError, FileNotFoundError) as exc:
        print(
            f"[Build] Warning: Failed to check Python dependencies: {exc}",
            file=sys.stderr,
        )
        return []  # no fatal error, just pass an empty list

    return list(available_deps)

def install_dependencies(deps: Iterable[str]):
    deps = set(deps)
    try:
        # Ensure nuitka is installed
        from nuitka.Version import getNuitkaVersion  # pyright: ignore[reportMissingImports]
        print(f"[Build] Nuitka version: {getNuitkaVersion()}")
    except ImportError:
        print("[Build] Nuitka not found. Installing via pip...", file=sys.stderr)
        try:
            subprocess.check_call([EXEC_PATH, "-m", "pip", "install", *deps])
        except subprocess.CalledProcessError as e:
            print(f"[Build] Failed to install {', '.join(deps)}: {e}", file=sys.stderr)
            sys.exit(e.returncode)

def run_build():
    # Check dependencies first
    available_deps = check_dependencies(REQUIRED_DEPS)
    missing_deps = REQUIRED_DEPS - set(available_deps)
    if missing_deps:
        # Install missing dependencies
        missing_deps_sorted = sorted(missing_deps)
        print(f"[Build] Missing dependencies: {', '.join(missing_deps_sorted)}")
        install_dependencies(missing_deps_sorted)

    # Determine paths
    ctk_dir: Path
    try:
        import customtkinter
        ctk_dir = Path(customtkinter.__file__).absolute().parent
    except ImportError:
        print(
            "[Build] Unable to import customtkinter, have you installed all dependencies?\n" +
            "[Build] Please run:  pip install -e .\n",
            file=sys.stderr
        )
        sys.exit(1)  # Fatal exit

    # Build command using Nuitka
    cmd: List[str] = [
        EXEC_PATH, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=tk-inter",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={APP_NAME}",
        f"--include-data-dir={ASSETS_DIR}=assets",
        f"--include-data-dir={ctk_dir}=customtkinter",
        "--assume-yes-for-downloads",
    ]

    curr_system = platform.system().lower()
    is_favicon_exist = ICON_PATH.is_file()
    # Early warn
    if not is_favicon_exist:
        print(
            "[Build] Warning: favicon.ico not found, compiling without custom icon.",
            file=sys.stderr
        )

    # Platform-specific options
    if curr_system == "windows":
        cmd.extend([
            "--windows-console-mode=disable",
            f"--windows-icon-from-ico={ICON_PATH}" if is_favicon_exist else ''
        ])
    elif curr_system == "darwin":
        cmd.extend([
            "--macos-create-app-bundle",
            f"--macos-app-icon={ICON_PATH}" if is_favicon_exist else ''
        ])

    # Filter from None values
    cmd = [c for c in cmd if c.strip() != '']

    # Entry point
    cmd.append(str(APP_ENTRY_POINT))

    # Run Nuitka
    print(f"[Build] Running Nuitka compilation command:\n{' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("[Build] Nuitka compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[Build] Nuitka compilation failed with exit code: {e.returncode}")
        sys.exit(1)

    # Package the output into a zip file in a 'releases' folder
    package_release(ROOT_DIR)

def package_release(project_root: Union[str, Path]):
    project_root = Path(project_root).absolute()
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Identify OS and Architecture
    os_system = platform.system().lower()
    arch = normalize_arch(platform.machine())

    if os_system == "darwin":
        os_name = "macos"
    else:
        os_name = os_system

    # Naming convention: xidown-[version]-[os]-[arch][-portable].zip
    # We add "-portable" for Windows to distinguish it from the setup.exe
    if os_name == "windows":
        zip_name = f"{APP_NAME}-{APP_VER}-{os_name}-{arch}-portable.zip"
    else:
        zip_name = f"{APP_NAME}-{APP_VER}-{os_name}-{arch}.zip"

    zip_path = RELEASES_DIR / zip_name

    print(f"[Build] Packaging application for {os_name} ({arch})...")

    # Nuitka outputs to dist/app.dist/ for standalone mode, but on macOS with --macos-create-app-bundle
    # it creates an .app bundle and might leave app.dist empty.
    nuitka_output = None

    if os_name == "macos":
        # Prefer the .app bundle on macOS
        for app_name in [f"{APP_NAME}.app", "app.app"]:
            possible_app = DIST_DIR / app_name
            if possible_app.is_dir():
                nuitka_output = possible_app
                break

    dist_dir_items = list(DIST_DIR.iterdir())
    if not nuitka_output:
        # Fallback to .dist folders
        std_dist = DIST_DIR / "app.dist"
        if std_dist.is_dir() and any(std_dist.iterdir()): # Must not be empty
            nuitka_output = std_dist
        else:
            for item in dist_dir_items:
                # Do not need to resolve the paths, see ROOT_DIR
                if (item.name.endswith(".dist") or item.name.endswith(".app")) and item.is_dir():
                    if not any(item.iterdir()): continue
                    nuitka_output = item
                    break

    if not nuitka_output or not nuitka_output.is_dir():
        print(
            f"[Build] Error: Nuitka valid output directory not found.\n" +
            f"[Build] Contents of 'dist/': {dist_dir_items if dist_dir_items else 'NOT FOUND'}",
            file=sys.stderr
        )
        sys.exit(2)

    print(f"[Build] Found Nuitka output at: {nuitka_output}")

    # Create a temporary directory for packaging
    app_folder_path = DIST_DIR / f"{APP_NAME}_pkg_temp"
    app_bundle_path = app_folder_path / f"{APP_NAME}.app"  # For MacOS
    if app_folder_path.is_dir():
        try: shutil.rmtree(app_folder_path)
        except Exception as e:
            print(
                f"[Build] Warning: Failed to remove old temporary directory: {e}",
                file=sys.stderr
            )
    app_folder_path.mkdir(exist_ok=True)

    # Copy the compiled output into our temporary release folder
    if os_name == "macos" and nuitka_output.name.endswith(".app"):
        # If Nuitka output is directly the .app bundle
        shutil.copytree(nuitka_output, app_bundle_path, symlinks=True)
        print(f"[Build] Copied {nuitka_output} bundle into release folder.")
    else:
        # For Windows/Linux or if output is a .dist folder, copy all contents
        for item in os.listdir(nuitka_output):
            s = nuitka_output / item
            d = app_folder_path / item
            if s.is_dir():
                shutil.copytree(s, d, symlinks=True)
            else:
                shutil.copy2(s, d, follow_symlinks=False)
        print("[Build] Copied all compiled files and folders into release folder.")

    # Copy extra files to the release folder before zipping
    for extra in EXTRA_FILES:
        # Immediate to continue if file is not exist
        if not extra.is_file(): continue

        # Copy file to the release folder
        try:
            shutil.copy(extra, app_folder_path / extra.name)
            print(f"[Build] Copied {extra.name} into release folder.")
        except Exception as e:
            print(f"[Build] Warning: Failed to copy {extra.name}: {e}", file=sys.stderr)

    has_cleanup: bool = False
    def cleanup() -> None:
        """Cleanup function, must be called after zipping operation completed or an error occurred."""
        nonlocal has_cleanup
        if has_cleanup or not app_folder_path.is_dir(): return

        try:
            has_cleanup = True
            # Clean up our temporary release folder
            shutil.rmtree(app_folder_path)
        except Exception as e:
            print(
                f"[Build] Warning: Failed to clean up temporary release folder: {e}",
                file=sys.stderr
            )

    # Zip the entire folder
    try:
        print(f"[Build] Zipping folder: {app_folder_path} to {zip_path}...")

        # Create portable.txt ONLY for the zip package (portable version)
        portable_txt_path = app_folder_path / "portable.txt"
        try:
            with open(portable_txt_path, "w", encoding="utf-8") as f:
                f.write("This file tells xidown to run in portable mode and save data in this folder.")
        except OSError:
            print("[Build] Warning: Failed to create portable identifier file", file=sys.stderr)
            pass

        created_zip = safe_zip_directory(app_folder_path, zip_path)
        created_zip_path = Path(created_zip)
        if not created_zip_path.is_file():
            raise FileNotFoundError(f"[Build] Expected archive not found: {created_zip}")

        # If the created archive file not inside releases folder, move it
        if RELEASES_DIR not in created_zip_path.parents:
            shutil.move(created_zip_path, RELEASES_DIR / created_zip_path.name)

        # Remove portable.txt so the Inno Setup installer (which runs next) doesn't include it
        if portable_txt_path.is_file():
            try: portable_txt_path.unlink()
            except: pass

        print(f"[Build] Packaged successfully to: {created_zip}")
        print(f"[Build] Package size: {created_zip_path.stat().st_size / (1024*1024):.2f} MB")

        # Build Inno Setup installer if on Windows
        if os_name == "windows":
            build_inno_setup(app_folder_path, RELEASES_DIR, project_root, arch)

    except Exception as e:
        print(f"[Build] Packaging failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cleanup()

def build_inno_setup(
    app_folder_path: Union[str, Path],
    releases_dir: Union[str, Path],
    project_root: Union[str, Path],
    arch: str
):
    app_folder_path = Path(app_folder_path)
    releases_dir = Path(releases_dir)
    project_root = Path(project_root)

    iss_content = f"""
[Setup]
AppName=xidown
AppVersion={APP_VER}
AppPublisher=indravoyager
DefaultDirName={{localappdata}}\\Programs\\{APP_NAME}
DefaultGroupName={APP_NAME}
OutputDir={releases_dir}
OutputBaseFilename={APP_NAME}-v{APP_VER}-windows-{arch}-setup
Compression=lzma2
SolidCompression=yes
SetupIconFile={app_folder_path}\\assets\\favicon.ico
WizardImageFile={app_folder_path}\\assets\\installer_side.bmp
UninstallDisplayIcon={{app}}\\{APP_NAME}.exe
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{app_folder_path}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"
Name: "{{autodesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{APP_NAME}.exe"; Description: "{{cm:LaunchProgram,{APP_NAME}}}"; Flags: nowait postinstall skipifsilent
"""
    iss_path = project_root / "{APP_NAME}.iss"
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(iss_content)

    print(f"[Build] Created Inno Setup script at {iss_path}")

    # Check if ISCC is available (Windows only)
    iscc_paths = [
        r"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
        r"C:\\Program Files\\Inno Setup 6\\ISCC.exe"
    ]
    iscc_exe: Union[str, None] = None
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
            print(f"[Build] Installer compilation failed: {e}", file=sys.stderr)
    else:
        print("[Build] Inno Setup compiler not found. Skipping installer creation.", file=sys.stderr)

def zip_directory(folder_path: Union[str, Path], zip_path: Union[str, Path]):
    folder_path = Path(folder_path)
    zip_path = Path(zip_path)
    base_name = zip_path.stem

    # Using shutil.make_archive handles permissions and symlinks much better than standard zipfile module
    # We create the archive in the directory above with the desired base name
    shutil.make_archive(base_name, 'zip', folder_path.parent, folder_path.name)

    # shutil creates a zip with the folder name as the root directory inside the zip.
    # Since our folder is "xidown_pkg_temp", let's rename the folder temporarily to "xidown" before zipping
    pass # Re-implemented below for clarity

def safe_zip_directory(folder_path: Union[str, Path], zip_path: Union[str, Path]) -> str:
    folder_path = Path(folder_path).resolve()
    zip_path = Path(zip_path).resolve()

    if not folder_path.is_dir():
        raise NotADirectoryError(folder_path)

    archive_root = folder_path.parent / APP_NAME

    folder_path.rename(archive_root)
    print(f"[Build] Renamed '{folder_path}' -> '{archive_root}'")

    try:
        archive = shutil.make_archive(
            str(zip_path.with_suffix("")),
            "zip",
            archive_root.parent,
            archive_root.name,
        )
        print(f"[Build] Created ZIP archive: {archive}")
        return archive
    finally:
        archive_root.rename(folder_path)
        print(f"[Build] Renamed '{archive_root}' -> '{folder_path}'")

if __name__ == "__main__":
    run_build()
