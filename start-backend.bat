@echo off
cd /d "%~dp0backend"
call conda activate ai-interview-agent
uvicorn app.main:app --reload
