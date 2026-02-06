@echo off
echo Compiling the Java code...
javac --release 8 hello.java
if %ERRORLEVEL% EQU 0 (
    jar cf hello.jar hello.class
    echo Done. hello.jar and hello.class created.
) else (
    echo Compilation failed. Please ensure JDK is installed and in PATH.
)
