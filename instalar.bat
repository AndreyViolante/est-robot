@echo off
cd /d "%~dp0"
echo ============================================
echo   est-robot: preparando este computador
echo ============================================
echo.

python --version >nul 2>nul
if errorlevel 1 goto sem_python
python --version

echo.
echo Instalando o pywinusb (comunicacao USB com o robo)...
python -m pip install --upgrade --disable-pip-version-check pywinusb
if errorlevel 1 goto erro_pip

python -c "import pywinusb.hid" >nul 2>nul
if errorlevel 1 goto erro_pip

echo.
echo ============================================
echo   Tudo pronto!
echo ============================================
echo   1. Abra esta pasta no VS Code (Arquivo - Abrir Pasta).
echo   2. Abra o meu_programa.py e aperte Ctrl+Shift+B: luz, som e "Funcionou!" na tela.
echo.
choice /M "Quer testar a conexao com o robo agora (precisa do cabo USB ligado)"
if errorlevel 2 goto fim
python ferramentas\testar_robo.py
goto fim

:sem_python
echo O Python nao foi encontrado.
echo.
echo   1. Baixe em https://www.python.org/downloads/
echo   2. Na instalacao, MARQUE a opcao "Add python.exe to PATH".
echo   3. Depois rode este instalar.bat de novo.
goto fim

:erro_pip
echo.
echo Nao foi possivel instalar o pywinusb. Confira a internet e tente de novo.
echo Se o computador for da escola, pode ser preciso pedir permissao ao responsavel pela rede.

:fim
echo.
pause
