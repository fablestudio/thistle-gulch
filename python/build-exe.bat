del /q dist || echo ERROR && exit /b 1
poetry run pyinstaller build_scripts/thistle-gulch.spec --clean || echo ERROR && exit /b 1
