@echo off
setlocal
if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" call "%USERPROFILE%\miniconda3\Scripts\activate.bat"
call conda activate lerobot
if errorlevel 1 (
  echo lerobot conda environment activation failed.
  echo Run this file from Miniconda Prompt after: conda activate lerobot
  pause
  exit /b 1
)
cd /d "%~dp0"
python carepack_so101_profiled_studio.py
if errorlevel 1 pause
endlocal
