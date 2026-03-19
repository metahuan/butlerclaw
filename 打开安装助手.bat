@echo off
chcp 65001 >nul
title OpenClaw 龙虾管家
set PYCMD=python
python --version >nul 2>&1 || set PYCMD=py
%PYCMD% "%~dp0openclaw_assistant.py"
if errorlevel 1 pause
