@ECHO OFF

:: Basic Options
SET env=.\.venv\Scripts\
SET entry-point=.\main.pyw
SET name=auto-ed
SET out-path=.\out
SET build-path=.\build

:: Build Configuration
SET toolchain=pyinstaller.exe
SET build-options=^
 -noconfirm^
 --clean^
 --name %name%^
 --workpath %build-path%^
 --distpath %out-path%^
 --onefile^
 --noconsole

:: Additional options
SET options=^
 --collect-binaries glfw^
 --icon .\resources\icon-color.ico

SET exec= %env%%toolchain%
SET args=%entry-point% %build-options% %options%

:: Build command
ECHO Build %main%
@ECHO ON
%exec% %args%
@ECHO OFF
ECHO Build %main% complete

:: Copy resources
ECHO Copy Resources
@ECHO ON
xcopy  .\resources\ %out-path%\resources\ /E /Y
xcopy .version %out-path%\ /Y
@ECHO OFF
ECHO Copy Resources complete