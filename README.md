[ Languages: **English** | [日本語](README.ja.md) (Japanese) ]

# 🚀 Easy JNLP Runner

A Python script to launch Java Web Start (`.jnlp`) files in modern Linux, macOS, and Windows environments. It was created to solve compatibility issues with Java Web Start (`javaws`) and legacy Java applets in environments where they are no longer supported.

It is particularly suitable for running applications that use old, unsigned JARs, such as the remote consoles of HPE KVM switches (Avocent OEM), by bypassing security restrictions.

## ✨ Features

* **Auto Setup**: Parses `.jnlp` files and automatically downloads and extracts necessary JAR files and native libraries.
* **Multi-OS Support**: Supports Linux, macOS, and Windows. It automatically detects the OS and loads the appropriate native libraries.
* **Robust Compatibility Measures**:
    * **Linux**: Includes automatic settings to avoid GUI freezes occurring in the latest Ubuntu 24.04 (Wayland).
    * **macOS**: Properly extracts and loads Mac native libraries (`.jnilib`, etc.) from the JNLP.
    * **Windows**: Runs smoothly in standard Python + Java environments with minimal path configuration.
* **Clean Execution**: Working files are managed in a temporary directory and automatically deleted upon exit.

## 💡 Why use this over Java Web Start?

*   **Bypassing Signature Checks (Primary Reason)**
    OpenWebStart and Java Web Start have strict security policies that often block old, unsigned KVM applications. This tool downloads the JARs locally and executes them as a **"local command executed by the user's intent"**, effectively bypassing signature checks and sandbox restrictions.

## 🛡️ Security Considerations

*   **Sandbox Bypass**: This tool intentionally bypasses Java's sandbox and signature checks to ensure compatibility with legacy hardware. The application will run with the same privileges as the user executing the script.
*   **Trustworthiness**: Only execute `.jnlp` files from trusted sources (e.g., your own KVM switches). Running a JNLP file from an untrusted source may allow malicious code to access your local file system.

## 📋 Requirements

### Confirmed KVM Switches

| Manufacturer | Model | Version (App / Boot) | Build |
| :--- | :--- | :--- | :--- |
| HPE | 0x2x16 G3 KVM Console Switch | 02.02.00.00 / 03.40.00.00 | 4508 |

### Linux (Ubuntu, Debian, etc.)
* **OS**: Confirmed on Ubuntu 24.04 (Noble).
* **Java**: **Java 8 Runtime (OpenJDK 8) Required**
    * Installation example: `sudo apt install openjdk-8-jre`

### macOS
* **OS**: macOS Monterey or later (Intel / Apple Silicon)
    * **Apple Silicon Support**: Runs natively (arm64) with an ARM-native JRE. However, if the JNLP application requires legacy Intel-only native libraries (common in old KVM consoles), you must use an x86_64 JRE via **Rosetta 2** for compatibility.
* **Java**: **Java 8 or 11 (OpenJDK)**
    * Confirmed: OpenJDK 11 (Eclipse Temurin 11)
    * Homebrew installation: `brew install --cask temurin` (Latest LTS) or `brew install --cask temurin8`

## 🚀 Usage

1. Download `session_launch.jnlp` (or `video.jnlp`, etc.) from the KVM switch Web UI.
2. Run the script with the downloaded `.jnlp` file as an argument.

### Launch on Linux
```bash
# Disable smart card and apply UI freeze fixes (Force X11 + Disable ATK)
python3 easy-jnlp-runner.py --no-smartcard --fix-ui session_launch.jnlp
```

### Launch on macOS
```bash
# Basic launch
python3 easy-jnlp-runner.py session_launch.jnlp
```
The `--fix-ui` option is not needed on macOS (automatically ignored).

### ⚙️ Options

| Option | Description |
| :--- | :--- |
| `jnlp_file` | Path to the `.jnlp` file (Default: `session_launch.jnlp`). |
| `--fix-ui` | **[Linux Only]** Applies UI freeze fixes. Forces X11 backend in Wayland and temporarily disables `AtkWrapper` (Accessibility) to prevent deadlocks. |
| `--no-smartcard` | **[Important]** Excludes smart card reader libraries (`avctJPCSC`). Avoids hangs waiting for driver loading. |
| `--java <path>` | Path to the Java executable. If not specified, auto-detected from PATH or predefined paths. |
| `--use-opengl` | Changes rendering pipeline to OpenGL. Try this if rendering is glitchy. |
| `--debug` | Debug mode. Keeps temporary files and checks native library dependencies (`ldd`, etc.). |
| `--diagnose` | Diagnosis mode. Forces a thread dump and exits after 15 seconds. |

## 🛠️ Testing with Sample JAR

You can test the script using the `sample_jar` provided in the repository. Since no binaries are included, you need to compile them first.

### 1. Build Sample (Requires JDK)
```bash
cd sample_jar
./compile.sh  # Linux / macOS
compile.bat   # Windows
# Note: hello.jar and hello.class will be generated.
```

### 2. Prepare Local Server
JNLP files usually load JAR files over the network. Expose the `sample_jar` directory as an HTTP server for testing. (Note: The included `hello.jnlp` is configured to fetch files from `http://localhost:8000`)

```bash
# Terminal A (Run inside sample_jar)
python3 -m http.server 8000
```

### 3. Run Script
Open another terminal and run the following command from the repository root.

```bash
# Terminal B (Run in root directory)
python3 easy-jnlp-runner.py sample_jar/hello.jnlp
```

If successful, `hello.jar` will be downloaded to a temporary directory, and a Java dialog box ("hello from easy-jnlp-runner!") will appear.

## ❓ Troubleshooting

### Q. [Linux] The screen doesn't appear or freezes gray after launch
**A.** Might be an issue with GNOME, Wayland, or smart card drivers. Try:
`python3 easy-jnlp-runner.py --no-smartcard --fix-ui`

### Q. [Linux] Other Java apps behave strangely after running the script
**A.** The script temporarily modifies `~/.accessibility.properties`. It's usually restored automatically, but may persist if the script is forced to quit. Delete the file or restore from backup (`.bak`) if it remains.

### Q. [macOS] "java" command not found
**A.** Java 8 is not installed or not in PATH. Install via `brew install --cask temurin8` or specify the path:
`--java /Library/Internet\ Plug-Ins/JavaAppletPlugin.plugin/Contents/Home/bin/java`

### Q. "Access Denied"
**A.** The authentication token in the JNLP file has expired. Download a new JNLP file from the KVM Web UI and run it immediately.

## 📄 License

[MIT License](LICENSE)

## 👤 Author
Masahiko OHKUBO (https://github.com/mah-jp)
