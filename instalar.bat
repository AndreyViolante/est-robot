@echo off
cd /d "%~dp0"
echo ============================================
echo   est-robot: preparando este computador
echo ============================================
echo.

rem pacote para Windows: o Python ja vem na pasta python, com o pywinusb
if exist "python\python.exe" goto python_do_pacote

python --version >nul 2>nul
if errorlevel 1 goto sem_python
python --version

echo.
echo Instalando o pywinusb (comunicacao USB com o robo)...
python -m pip install --upgrade --disable-pip-version-check pywinusb
if not errorlevel 1 goto conferir_pywinusb
echo.
echo Tentando de novo so para este usuario (sem precisar de administrador)...
python -m pip install --user --upgrade --disable-pip-version-check pywinusb
if errorlevel 1 goto erro_pip

:conferir_pywinusb
python -c "import pywinusb.hid" >nul 2>nul
if errorlevel 1 goto erro_pip
goto pronto

:python_do_pacote
echo Este e o pacote com o Python dentro (pasta python): nao precisa instalar nada.
python\python.exe -c "import pywinusb.hid" >nul 2>nul
if errorlevel 1 goto pacote_incompleto
python\python.exe --version

:pronto
echo.
echo ============================================
echo   Tudo pronto!
echo ============================================
echo   1. Abra esta pasta no VS Code (Arquivo - Abrir Pasta).
echo   2. Abra o meu_programa.py e aperte Ctrl+Shift+B: luz, som e "Funcionou!" na tela.
echo.
choice /M "Quer testar a conexao com o robo agora (precisa do cabo USB ligado)"
if errorlevel 2 goto fim
call ferramentas\rodar.cmd ferramentas\testar_robo.py
goto fim

:sem_python
echo O Python nao foi encontrado.
echo.
echo   Jeito mais facil, sem instalar nada e sem administrador: baixe o pacote
echo   est-robot-windows.zip, que ja vem com o Python dentro (veja o INSTALAR.md).
echo.
echo   Ou instale o Python:
echo   1. Baixe em https://www.python.org/downloads/
echo   2. Na instalacao, MARQUE a opcao "Add python.exe to PATH".
echo   3. Depois rode este instalar.bat de novo.
goto fim

:pacote_incompleto
echo A pasta python deste pacote esta incompleta (falta o pywinusb).
echo Baixe o est-robot-windows.zip de novo e descompacte tudo.
goto fim

:erro_pip
echo.
echo Nao foi possivel instalar o pywinusb. Confira a internet e tente de novo.
echo Se o computador for da escola e nao deixar instalar, use o pacote est-robot-windows.zip,
echo que ja vem com o Python e o pywinusb dentro (veja o INSTALAR.md).

:fim
echo.
pause
