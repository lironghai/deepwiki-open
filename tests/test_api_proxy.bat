@echo off
REM Test script for Codemap API proxy (Windows)

echo ==========================================
echo Codemap API Proxy Test
echo ==========================================

REM Check if backend is running
echo.
echo [1/3] Checking backend service (port 8001)...
curl -s http://localhost:8001/lang/config >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend is running on port 8001
) else (
    echo [FAIL] Backend is NOT running!
    echo   Please start it with: python -m uvicorn api.api:app --host 0.0.0.0 --port 8001
    exit /b 1
)

REM Check if frontend is running
echo.
echo [2/3] Checking frontend service (port 3000)...
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Frontend is running on port 3000
) else (
    echo [FAIL] Frontend is NOT running!
    echo   Please start it with: npm run dev
    exit /b 1
)

REM Test the Codemap chat endpoint through proxy
echo.
echo [3/3] Testing Codemap chat endpoint...
curl -s -X POST http://localhost:3000/api/chat/codemap ^
  -H "Content-Type: application/json" ^
  -d "{\"repo_url\":\"https://github.com/test/repo\",\"type\":\"github\",\"question\":\"What is this project about?\",\"provider\":\"openai\",\"model\":\"gpt-4\",\"language\":\"en\"}" > response.tmp

findstr /C:"answer" /C:"error" response.tmp >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Codemap chat endpoint is responding
    type response.tmp | findstr /B /C:"{" | findstr /E /C:"}"
) else (
    echo [FAIL] Unexpected response from endpoint
    type response.tmp
    del response.tmp
    exit /b 1
)

del response.tmp

echo.
echo ==========================================
echo All tests passed! [OK]
echo ==========================================
echo.
echo You can now use Codemap Integration in the chat interface!

pause
