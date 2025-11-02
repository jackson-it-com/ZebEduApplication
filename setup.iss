[Setup]
AppName=ZebEduApplication
AppVersion=1.0
DefaultDirName={pf}\ZebEduApplication
DefaultGroupName=ZebEduApplication
OutputDir=Installer
OutputBaseFilename=ZebEduInstaller
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\launcher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ZebEduApplication"; Filename: "{app}\launcher.exe"

[Run]
Filename: "{app}\launcher.exe"; Description: "Launch ZebEduApplication"; Flags: nowait postinstall skipifsilent
