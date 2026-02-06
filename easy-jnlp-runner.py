#!/usr/bin/env python3

# easy-jnlp-runner.py (Ver.20260206)
# Ref: https://github.com/mah-jp/easy-jnlp-runner
# License: MIT

import os
import sys
import subprocess
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
import tempfile
import argparse
import platform
import shutil
from typing import List, Dict, Tuple, Optional
from contextlib import contextmanager

# --- Configuration & Constants ---
SCRIPT_VERSION = '20260206'
DEFAULT_JNLP_FILE = 'session_launch.jnlp'

def print_banner(java_path: str):
    sys_conf = get_system_config()
    print(f'Easy JNLP Runner v{SCRIPT_VERSION}')
    print(f"Detected OS: {sys_conf['os_type']}")
    print(f"Using Java: {java_path}")
    print('-' * 30)

def get_system_config() -> Dict:
    """Get OS-specific configuration."""
    system = platform.system()
    config = {
        'os_type': system,
        'default_java': 'java', # Fallback
        'jnlp_os_includes': [],
        'lib_path_env': 'LD_LIBRARY_PATH',
        'linux_hacks': False
    }

    if system == 'Linux': # Linux
        # First priority: 'java' in PATH
        java_in_path = shutil.which('java')
        if java_in_path:
            config['default_java'] = java_in_path
        else:
            # Fallback for Ubuntu/Debian default OpenJDK 8 path
            config['default_java'] = '/usr/lib/jvm/java-8-openjdk-amd64/bin/java'
            
        config['jnlp_os_includes'] = ['Linux']
        config['lib_path_env'] = 'LD_LIBRARY_PATH'
        config['linux_hacks'] = True
    elif system == 'Darwin': # macOS
        # Try to find Java 8 via /usr/libexec/java_home
        try:
            cmd = ['/usr/libexec/java_home', '-v', '1.8']
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            config['default_java'] = f'{output}/bin/java'
        except:
            config['default_java'] = 'java' # Hope it's in PATH
            
        config['jnlp_os_includes'] = ['Mac', 'Darwin'] 
        config['lib_path_env'] = 'DYLD_LIBRARY_PATH'
        config['linux_hacks'] = False
    elif system == 'Windows': # Windows
        java_in_path = shutil.which('java')
        if java_in_path:
            config['default_java'] = java_in_path
        else:
            # Common path for 64-bit Java on Windows
            prog_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            config['default_java'] = os.path.join(prog_files, 'Java', 'jre1.8.0_202', 'bin', 'java.exe')

        config['jnlp_os_includes'] = ['Windows']
        config['lib_path_env'] = 'PATH'
        config['linux_hacks'] = False
    
    return config

# Environment variables for GUI compatibility (Linux only)
LINUX_ENV_OPTIONS = {
    '_JAVA_OPTIONS': '-Dsun.java2d.xrender=false -Djava.net.preferIPv4Stack=true',
    '_JAVA_AWT_WM_NONREPARENTING': '1'
}

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    sys_conf = get_system_config()
    parser = argparse.ArgumentParser(description=f"Easy JNLP Runner ({sys_conf['os_type']})")
    parser.add_argument('jnlp_file', nargs='?', default=DEFAULT_JNLP_FILE, help='Path to the .jnlp file (default: session_launch.jnlp)')
    parser.add_argument('--java', default=sys_conf['default_java'], help=f"Path to the Java executable (default: {sys_conf['default_java']})")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (keep temp files, check dependencies)')
    parser.add_argument('--no-smartcard', action='store_true', help='Disable smart card support (skips avctJPCSC libraries)')
    parser.add_argument('--use-opengl', action='store_true', help='Enable OpenGL rendering pipeline (may fix UI freeze)')
    parser.add_argument('--fix-ui', action='store_true', help='Try to fix UI freeze (Linux: force X11 backend, enable XRender)')
    parser.add_argument('--diagnose', action='store_true', help='Run in diagnosis mode (collect system info and thread dump)')
    return parser.parse_args()

def parse_jnlp(jnlp_file: str) -> Tuple[str, str, List[str], List[str], List[str]]:
    """
    Parse the JNLP file to extract codebase, main class, arguments, and resources.
    Returns: (base_url, main_class, app_args, jar_files, native_jar_files)
    """
    if not os.path.exists(jnlp_file):
        print(f"Error: '{jnlp_file}' not found.")
        print("Hint: Place the 'session_launch.jnlp' file in the current directory or specify it as an argument.")
        sys.exit(1)

    try:
        tree = ET.parse(jnlp_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f'Error parsing JNLP file: {e}')
        sys.exit(1)

    base_url = root.get('codebase')
    
    # Get Main Class
    app_desc = root.find('application-desc')
    if app_desc is None:
        print('Error: <application-desc> not found in JNLP.')
        sys.exit(1)
    main_class = app_desc.get('main-class')

    # Get Arguments
    app_args = [arg.text for arg in app_desc.findall('argument') if arg.text]

    # Get JARs
    jars = []
    native_jars = []

    # 1. Common resources
    for res in root.findall('resources'):
        if 'os' not in res.attrib and 'arch' not in res.attrib:
            for jar in res.findall('jar'):
                href = jar.get('href')
                if href:
                    jars.append(href)

    # 2. OS specific resources
    sys_conf = get_system_config()
    target_keywords = sys_conf['jnlp_os_includes']
    
    print(f'DEBUG: Searching resources for OS keywords: {target_keywords}')

    for res in root.findall('resources'):
        os_attr = res.get('os')
        arch_attr = res.get('arch')
        
        # Check if this resource block matches our OS
        is_os_match = False
        if os_attr:
            for key in target_keywords:
                # Handle "Mac\ OS\ X" unescaping style if present, or simple substring matches
                # Also handle direct match
                norm_os = os_attr.replace('\\ ', ' ')
                if key.lower() in norm_os.lower(): 
                   is_os_match = True
                   break
        
        # If OS matches, check Architecture (simplified check)
        if is_os_match:
            # Assume 64bit for modern usage.
            # If arch is missing, accept it. If present, check standard known 64bit strings including ARM.
            if not arch_attr or any(x in arch_attr for x in ['amd64', 'x86_64', 'x64', 'aarch64', 'arm64']):
                for nativelib in res.findall('nativelib'):
                    href = nativelib.get('href')
                    if href and href not in jars:
                        jars.append(href)
                        native_jars.append(href)

    return base_url, main_class, app_args, jars, native_jars

def download_jars(base_url: str, jars: List[str], dest_dir: str) -> List[str]:
    """Download JAR files to the destination directory."""
    print(f'--- Downloading JARs to {dest_dir} ---')
    local_paths = []

    for jar in jars:
        url = f'{base_url}/{jar}'
        dest = os.path.join(dest_dir, jar)
        
        # Create subdirectories if href contains them (e.g. lib/app.jar)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        
        local_paths.append(dest)
        
        print(f'Downloading {jar}...')
        try:
            # Use a browser User-Agent to avoid throttling (Disabled)
            headers = {}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', -1))
                downloaded = 0
                block_size = 8192
                
                with open(dest, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        downloaded += len(buffer)
                        
                        # Progress update
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            downloaded_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            sys.stdout.write(f'\rProgress: {percent}% ({downloaded_mb:.2f} / {total_mb:.2f} MB)')
                        else:
                            downloaded_mb = downloaded / (1024 * 1024)
                            sys.stdout.write(f'\rProgress: {downloaded_mb:.2f} MB downloaded')
                        sys.stdout.flush()
            print() # Newline after completion

        except Exception as e:
            print(f'\nError downloading {jar}: {e}')
            sys.exit(1)
    return local_paths

def extract_natives(native_jars: List[str], work_dir: str):
    """Extract native libraries from JARs."""
    print('--- Extracting Native Libraries ---')
    for jar in native_jars:
        jar_path = os.path.join(work_dir, jar)
        if os.path.exists(jar_path):
            try:
                with zipfile.ZipFile(jar_path, 'r') as zip_ref:
                    print(f'Extracting {jar}...')
                    zip_ref.extractall(work_dir)
            except Exception as e:
                print(f'Error extracting {jar}: {e}')

class AccessibilityConfig:
    """Context manager to temporarily disable Java Accessibility Bridge."""
    def __init__(self):
        self.enabled = platform.system() == 'Linux' # Only run on Linux
        if self.enabled:
            self.home_dir = os.path.expanduser('~')
            self.prop_file = os.path.join(self.home_dir, '.accessibility.properties')
            self.backup_file = self.prop_file + '.bak'
            self.created = False
            self.modified = False

    def __enter__(self):
        if not self.enabled:
            return self

        # 1. Backup existing file if needed
        if os.path.exists(self.prop_file):
            try:
                os.rename(self.prop_file, self.backup_file)
                self.modified = True
            except OSError:
                pass # Can't move? ignore.
        
        # 2. Write empty config or specific disable
        try:
            with open(self.prop_file, 'w') as f:
                # Disabling assistive_technologies prevents AtkWrapper loading
                f.write('assistive_technologies=\n')
                f.write('screen_reader_present=false\n')
            self.created = True
            print('INFO: Temporarily disabled Java Accessibility Bridge.')
        except IOError:
            print('WARN: Could not write .accessibility.properties')

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.enabled:
            return

        # 1. Remove temporary file
        if self.created:
            try:
                os.remove(self.prop_file)
            except OSError:
                pass

        # 2. Restore backup
        if self.modified and os.path.exists(self.backup_file):
            try:
                os.rename(self.backup_file, self.prop_file)
            except OSError:
                pass

def run_client(java_path: str, work_dir: str, classpath: List[str], main_class: str, args: List[str], parsed_args: argparse.Namespace):
    """Construct logic to run the Java client."""
    
    sys_conf = get_system_config()
    
    cp_str = os.pathsep.join(classpath) # Use OS specific separator
    java_cmd = [
        java_path,
        f'-Djava.library.path={work_dir}',
        '-cp', cp_str,
        main_class
    ] + args

    if sys_conf['os_type'] == 'Darwin':
        # macOS specific: Add -Xdock:name for cleaner UI
        java_cmd.insert(1, '-Xdock:name=Easy JNLP Runner')

    print('\n--- Launching JNLP Client ---')
    # print('Command:', ' '.join(java_cmd)) # Verbose debug

    # Setup Environment
    env = os.environ.copy()
    lib_env = sys_conf['lib_path_env']
    env[lib_env] = work_dir + os.pathsep + env.get(lib_env, '')
    
    # Merge custom options (Linux only by default)
    if sys_conf['linux_hacks']:
        env.update(LINUX_ENV_OPTIONS)

    # 1. Apply OpenGL override if requested
    if parsed_args.use_opengl:
         current_opts = env.get('_JAVA_OPTIONS', '')
         env['_JAVA_OPTIONS'] = current_opts + ' -Dsun.java2d.opengl=true'

    # 2. Apply UI Fixes if requested (Mostly for Linux)
    if parsed_args.fix_ui:
        if sys_conf['os_type'] == 'Linux':
            print('INFO: Applying UI freeze fixes (GDK_BACKEND=x11, XRender=true)...')
            env['GDK_BACKEND'] = 'x11'
            # Remove xrender=false from _JAVA_OPTIONS and add xrender=true
            current_opts = env.get('_JAVA_OPTIONS', '')
            if '-Dsun.java2d.xrender=false' in current_opts:
                new_opts = current_opts.replace('-Dsun.java2d.xrender=false', '')
            else:
                new_opts = current_opts
                
            env['_JAVA_OPTIONS'] = new_opts + ' -Dsun.java2d.xrender=true'
            # Disable Accessibility Bridge (GNOME specific fix)
            env['NO_AT_BRIDGE'] = '1'
        else:
             print(f"INFO: --fix-ui is primarily for Linux. Ignoring specific hacks for {sys_conf['os_type']}.")

    print('--- Environment Variables ---')
    print(f"{lib_env}: {env.get(lib_env)}")
    print(f"_JAVA_OPTIONS: {env.get('_JAVA_OPTIONS')}")
    if parsed_args.fix_ui and sys_conf['os_type'] == 'Linux':
        print(f"GDK_BACKEND: {env.get('GDK_BACKEND')}")
        print(f"NO_AT_BRIDGE: {env.get('NO_AT_BRIDGE')}")
    
    if sys_conf['linux_hacks']:
        for key in LINUX_ENV_OPTIONS:
            if key != '_JAVA_OPTIONS':
                 print(f'{key}: {env.get(key)}')
    print('-----------------------------')

    if parsed_args.diagnose:
        print('\n*** DIAGNOSIS MODE ENABLED ***')
        print('Waiting 15 seconds for application to hang, then capturing Thread Dump...')
        
        try:
            # Run asynchronously
            proc = subprocess.Popen(
                java_cmd, 
                env=env, 
                stdout=sys.stdout, 
                stderr=sys.stderr
            )
            
            # Wait for hang reproduction
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                print('\n\n*** TIMEOUT REACHED: ATTEMPTING THREAD DUMP ***\n')
                print('---------------- THREAD DUMP START ----------------')
                
                if platform.system() == 'Windows':
                    # On Windows, SIGQUIT (3) doesn't exist. 
                    # send_signal(signal.CTRL_BREAK_EVENT) could work if started with creationflags,
                    # but for simplicity, we just notify.
                    print('INFO: Thread dump via signal is not supported on Windows.')
                    print('Try pressing Ctrl+Break in the terminal if possible.')
                else:
                    # Send SIGQUIT (kill -3) to Java process to print stack traces to stdout
                    try:
                        proc.send_signal(3) # signal.SIGQUIT
                    except Exception as e:
                        print(f'Error sending signal: {e}')
                
                # Wait a bit for dump to write out
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # If still running after dump, kill it
                    print('\n*** Terminating process... ***')
                    proc.terminate()
                print('---------------- THREAD DUMP END ----------------')

        except Exception as e:
            print(f'Diagnosis failed: {e}')

    else:
        # Normal synchronous run
        try:
            subprocess.run(java_cmd, env=env)
        except KeyboardInterrupt:
            print('\nProcess interrupted by user.')
        except FileNotFoundError:
            print(f"\nError: Java executable not found at '{java_path}'.")
            print('Please check the path or install Java 8 OpenJDK.')

@contextmanager
def create_work_dir(debug_mode: bool):
    """Context manager to create a temporary or persistent working directory."""
    if debug_mode:
        path = tempfile.mkdtemp(prefix='jnlp_runner_DEBUG_')
        print(f'DEBUG MODE ON: Using persistent directory: {path}')
        yield path
        print(f'\n[DEBUG] Files kept in: {path}')
    else:
        with tempfile.TemporaryDirectory(prefix='jnlp_runner_') as path:
            print(f'Using temporary directory: {path}')
            yield path

def fetch_jnlp(url: str) -> str:
    """Download JNLP file from URL to a temporary file."""
    print(f'Downloading JNLP from: {url}')
    try:
        headers = {}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            content = response.read() # Read as bytes
            
        # Create temp file
        fd, path = tempfile.mkstemp(suffix='.jnlp')
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            
        return path
    except Exception as e:
        print(f'Error fetching JNLP: {e}')
        sys.exit(1)

def main():
    args = parse_args()
    print_banner(args.java)
    
    jnlp_path = args.jnlp_file
    is_temp_jnlp = False

    # Check if input is a URL
    if jnlp_path.startswith(('http://', 'https://')):
        jnlp_path = fetch_jnlp(jnlp_path)
        is_temp_jnlp = True

    print(f'Processing JNLP: {jnlp_path}')
    try:
        base_url, main_class, app_args, jars, native_jars = parse_jnlp(jnlp_path)
    except SystemExit:
        # Cleanup if parse failed and it was a temp file
        if is_temp_jnlp and os.path.exists(jnlp_path) and not args.debug:
            os.remove(jnlp_path)
        raise

    # ... rest of logic ...
    
    print(f'BASE_URL: {base_url}')
    print(f'MAIN_CLASS: {main_class}')
    print(f'JARS: {len(jars)} files')
    
    # Filter Smart Card libraries if requested
    if args.no_smartcard:
        print('INFO: Excluding Smart Card libraries (avctJPCSC) as requested.')
        jars = [j for j in jars if 'avctJPCSC' not in j]
        native_jars = [j for j in native_jars if 'avctJPCSC' not in j]

    # Create temp dir and run
    with AccessibilityConfig():
        with create_work_dir(args.debug) as work_dir:
            # 1. Download
            local_jars = download_jars(base_url, jars, work_dir)
            
            # 2. Extract Natives
            extract_natives(native_jars, work_dir)
            
            # 3. Launch
            # 3. Launch
            run_client(
                java_path=args.java,
                work_dir=work_dir,
                classpath=local_jars,
                main_class=main_class,
                args=app_args,
                parsed_args=args
            )
            
    # Cleanup temp JNLP if needed
    if is_temp_jnlp and os.path.exists(jnlp_path):
        if args.debug:
            print(f'[DEBUG] Kept temp JNLP at: {jnlp_path}')
        else:
            os.remove(jnlp_path)

if __name__ == '__main__':
    main()
