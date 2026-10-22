@echo off
rem Roda um arquivo Python do projeto, na pasta do projeto. As tarefas do VS Code (.vscode\tasks.json)
rem chamam este arquivo. Usa o Python que vem no pacote para Windows (pasta python\ do projeto) quando
rem ele existe; se nao existe, usa o Python instalado no computador.
setlocal
rem volta para a pasta do projeto: um "AutoRun" do cmd no registro pode ter mudado de pasta
cd /d "%~dp0.."
set "PY=%~dp0..\python\python.exe"
if not exist "%PY%" set "PY=python"
rem O "goto" fica na mesma linha porque o "Atualizar o projeto" pode trocar este arquivo enquanto ele roda.
"%PY%" %* & goto fim

:fim
if errorlevel 9009 if "%PY%"=="python" (
    echo.
    echo O Python nao foi encontrado neste computador.
    echo Use o pacote com o Python dentro ou rode o instalar.bat: veja o INSTALAR.md.
)
exit /b %errorlevel%
