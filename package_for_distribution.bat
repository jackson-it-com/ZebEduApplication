@echo off
echo ====================================
echo ZebEduApplication Packaging
echo ====================================
echo.

echo Step 1: Adding schools to database...
python add_sample_schools.py

echo.
echo Step 2: Cleaning old builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del ZebEduApplication.spec 2>nul

echo.
echo Step 3: Building executable...
pyinstaller --onefile --windowed --name ZebEduApplication --add-data "templates;templates" --add-data "static;static" --add-data "instance;instance" --add-data "add_sample_schools.py;." --hidden-import=flask --hidden-import=flask_sqlalchemy --hidden-import=flask_login --hidden-import=flask_mail --hidden-import=werkzeug --hidden-import=jinja2 --hidden-import=email_validator --hidden-import=webview launcher.py

echo.
echo Step 4: Copying database to dist...
mkdir dist\instance 2>nul
copy instance\zebedu.db dist\instance\ /Y

echo.
echo ====================================
echo Build Complete!
echo ====================================
echo.
echo Your application is ready at:
echo dist\ZebEduApplication.exe
echo.
pause