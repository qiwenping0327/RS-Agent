@echo off
echo === RsAgent Production Mode ===
echo Activating conda environment...
call D:\miniconda3\condabin\conda.bat activate pilotdeck
cd /d D:\PilotDeck\ui
echo Starting server at http://localhost:3001
npm run start
pause