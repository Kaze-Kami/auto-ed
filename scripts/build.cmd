@ECHO OFF

:: Basic Options
SET env=.\.venv\Scripts\
SET python=%env%Python.exe

SET entry-point=.\main.pyw
SET name=auto-ed

SET build-path=.\build
SET out-path=.\out

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

SET build=%env%%toolchain%
SET build_args=%entry-point% %build-options% %options%

SET deps=deps.txt
SET install_deps=%python% -m pip install -r

:: Install dependencies
ECHO ----------------------------------------------
ECHO Install dependencies
@ECHO ON
%install_deps% %deps%
@ECHO OFF

:: Build command
ECHO ----------------------------------------------
ECHO Build %name%
@ECHO ON
%build% %build_args%
@ECHO OFF
ECHO Build %name% complete

:: Copy resources
ECHO ----------------------------------------------
ECHO Copy Resources
@ECHO ON
xcopy  .\resources\ %out-path%\resources\ /E /Y
xcopy .version %out-path%\ /Y
@ECHO OFF
ECHO Copy Resources complete