@echo off
REM Vaak launcher for Windows:  vaak.cmd examples/01_namaste.vak
REM Run from the repository root; sets UTF-8 output for Devanagari.
setlocal
set PYTHONIOENCODING=utf-8
python -m vaak %*
