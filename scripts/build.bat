@echo off
REM Lấy IPv4 hiện tại của máy tính
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "ip=%%a"
    goto :run
)

:run
REM Loại bỏ khoảng trắng đầu dòng
set "ip=%ip:~1%"
REM Chạy gunicorn với host là IPv4 vừa lấy và port 3198
gunicorn --bind %ip%:3198 app:app
