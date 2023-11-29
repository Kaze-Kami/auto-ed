@ECHO OFF

:: Basic Options
SET env=.\.venv\Scripts\
SET python=%env%Python.exe

SET entry-point=.\main.pyw
SET name=auto-ed

SET build-path=.\build
SET out-path=.\out
SET zip-name=auto-ed.zip

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
:deps
ECHO ----------------------------------------------
ECHO Install dependencies
@ECHO ON
%install_deps% %deps%
@ECHO OFF
ECHO Install dependencies complete

:: Build command
:build
ECHO ----------------------------------------------
ECHO Build %name%
@ECHO ON
%build% %build_args%
@ECHO OFF
ECHO Build %name% complete

:: Copy resources
:copy
ECHO ----------------------------------------------
ECHO Copy resources
@ECHO ON
xcopy  .\resources\ %out-path%\resources\ /E /Y
xcopy .version %out-path%\ /Y
@ECHO OFF
ECHO Copy resources complete

:: Release zip
:zip
ECHO ----------------------------------------------
ECHO Create release zip
@ECHO ON
7z a %out-path%\%zip-name% .\%out-path%\* -r -xr!%zip-name%
@ECHO OFF
ECHO Create release zip complete