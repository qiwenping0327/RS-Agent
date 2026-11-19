@echo off
echo === RsAgent Development Mode ===
echo Activating conda environment...
call D:\miniconda3\condabin\conda.bat activate pilotdeck
cd /d D:\PilotDeck\ui
echo Starting dev server at http://localhost:5173
npm run dev
pause