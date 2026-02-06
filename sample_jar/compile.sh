#!/bin/bash

# Compile the Java code
javac --release 8 hello.java
jar cf hello.jar hello.class
