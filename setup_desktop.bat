@echo off
echo ====================================
echo ZebEduApplication Desktop Setup
echo ====================================
echo.

REM Create app folder on desktop
set DESKTOP=%USERPROFILE%\Desktop
set APPFOLDER=%DESKTOP%\ZebEduApp

echo Creating folder on Desktop...
mkdir "%APPFOLDER%" 2>nul
mkdir "%APPFOLDER%\instance" 2>nul

echo Copying application...
copy "dist\ZebEduApplication.exe" "%APPFOLDER%\" /Y

echo Copying database...
xcopy "instance" "%APPFOLDER%\instance\" /E /I /Y

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo Your application is ready at:
echo %APPFOLDER%\ZebEduApplication.exe
echo.
echo Double-click it to run!
echo.
pause