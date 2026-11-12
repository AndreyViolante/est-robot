"""Monta o pacote para Windows com o Python dentro: dist/est-robot-windows.zip.

Quem baixa vê só o que usa (desde a 0.1.7; os alunos se perdiam no meio de dezenas de arquivos):

    Abrir o EST-LAB.cmd   dois cliques: abre o VS Code nesta pasta, já com o meu_programa.py
    LEIA-ME.txt           os passos, em poucas linhas
    meu_programa.py, calibracao.py, exemplos/, .vscode/
    sistema/              o resto do projeto e, em sistema/python/, o Python "embeddable" oficial do
                          python.org com o pywinusb. O VS Code esconde esta pasta.

As tarefas do VS Code chamam sistema/ferramentas/rodar.cmd, que usa esse Python. Nada precisa de
administrador nem de internet. O "Atualizar o projeto" (atualizar.py) conhece esse jeito de pasta.

Uso:
    python ferramentas/empacotar.py            arquivos do último commit (o que fica no GitHub depois do push)
    python ferramentas/empacotar.py --pasta    arquivos da pasta como estão agora, mesmo sem commit
    ... --testar                               depois de montar, descompacta numa pasta temporária e confere

Para trocar a versão do Python: mude PYTHON_VERSAO e PYTHON_SHA256. O SHA-256 está no arquivo
.sigstore ao lado do zip em python.org/ftp/python/<versão>/ (messageDigest, em base64).
"""
import hashlib, io, json, os, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile
from pathlib import Path

from atualizar import ABRIR, DO_ALUNO, DO_PROFESSOR, SISTEMA, TAREFAS_VSCODE, para_o_aluno

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / 'dist'
BAIXADOS = DIST / 'baixados'          # cópia dos downloads, para não baixar de novo a cada pacote
PACOTE = DIST / 'est-robot-windows.zip'

PYTHON_VERSAO = '3.13.17'
PYTHON_URL = f'https://www.python.org/ftp/python/{PYTHON_VERSAO}/python-{PYTHON_VERSAO}-embed-amd64.zip'
PYTHON_SHA256 = '9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38'

PYWINUSB_VERSAO = '0.4.2'
PYWINUSB_URL = ('https://files.pythonhosted.org/packages/38/b4/ecce4a3a0dac3b1bf5776943530cf4f36406fc9b3f4f3c31c8dcab2249eb/'
                f'pywinusb-{PYWINUSB_VERSAO}.zip')
PYWINUSB_SHA256 = 'e2f5e89f7b74239ca4843721a9bda0fc99014750630c189a176ec0e1b35e86df'

# Arquivo que diz ao Python embeddable onde procurar os módulos. ".." é a pasta do projeto, para o
# robo.py, estc.py etc. serem achados de qualquer script (esse Python não põe a pasta do script no
# caminho); "import site" acrescenta python/Lib/site-packages, onde fica o pywinusb.
_maior, _menor = PYTHON_VERSAO.split('.')[:2]
PTH_NOME = f'python{_maior}{_menor}._pth'
PTH = f"""python{_maior}{_menor}.zip
.
# a pasta do projeto (robo.py, estc.py, enviar.py...)
..
import site
"""

# dois cliques: abre o VS Code nesta pasta, já com o meu_programa.py (procura o VS Code onde ele costuma ficar)
ABRIR_CMD = r"""@echo off
rem Abre o EST-LAB no VS Code: esta pasta e o meu_programa.py.
setlocal
set "PASTA=%~dp0"
set "PASTA=%PASTA:~0,-1%"
set "CODE="
for %%C in ("%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe" "%ProgramFiles%\Microsoft VS Code\Code.exe") do if exist %%C set "CODE=%%~C"
if defined CODE (
    start "" "%CODE%" "%PASTA%" "%PASTA%\meu_programa.py"
    exit /b 0
)
where code >nul 2>nul
if not errorlevel 1 (
    call code "%PASTA%" "%PASTA%\meu_programa.py"
    exit /b 0
)
echo.
echo  O VS Code nao foi encontrado neste computador.
echo.
echo  Vou abrir a pagina dele: baixe, instale e depois de dois cliques
echo  de novo em "Abrir o EST-LAB".
echo.
pause
start "" https://code.visualstudio.com/
"""

LEIA_ME_ALUNO = """EST-LAB: programar o robo EST em Python, com comandos em portugues

COMO COMECAR
1. Instale o VS Code (code.visualstudio.com), se o computador ainda nao tiver.
2. De dois cliques em "Abrir o EST-LAB".
   Se o Windows perguntar se pode executar, clique em "Executar".
3. O VS Code abre com o meu_programa.py. Se ele perguntar "Do you trust the authors?",
   clique em "Yes, I trust the authors".
4. Ligue o robo no cabo USB e aperte Ctrl+Shift+B: o robo acende a luz, apita e
   escreve "Funcionou!" na tela.

O QUE TEM AQUI
  meu_programa.py   o primeiro programa. Escreva os seus aqui ou em arquivos novos .py
  exemplos          programas de exemplo
  calibracao.py     as medidas do robo (o professor ajusta uma vez)
  sistema           o EST-LAB e o Python. Nao precisa abrir nem mexer.

Sem instalar nada, pelo navegador: andreyviolante.github.io/est-robot/programar
Ajuda: github.com/AndreyViolante/est-robot
"""

LEIA_ME = f"""Python {PYTHON_VERSAO} para Windows 64 bits (pacote "embeddable" oficial do python.org)
com o pywinusb {PYWINUSB_VERSAO} em Lib/site-packages.

Não precisa instalar: as tarefas do VS Code usam este Python pelo sistema/ferramentas/rodar.cmd.
Para um Python mais novo, baixe o pacote do EST-LAB de novo.
"""


def git(*args):
    r = subprocess.run(['git', '-C', str(RAIZ), *args], capture_output=True)
    if r.returncode:
        raise SystemExit(f'ERRO: git {" ".join(args)}: {r.stderr.decode(errors="replace").strip()}')
    return r.stdout


def arquivos_do_commit():
    """{caminho: bytes} do último commit, com as quebras de linha que o GitHub também usa."""
    if git('status', '--porcelain').strip():
        print('Atenção: há mudanças sem commit; elas NÃO vão no pacote (use --pasta para incluir).')
    try:
        if int(git('rev-list', '--count', '@{u}..HEAD').strip() or 0):
            print('Atenção: o último commit ainda não foi para o GitHub (git push). Sem o push, o')
            print('"Atualizar o projeto" dos professores baixa uma versão mais velha que a do pacote.')
    except SystemExit:
        pass                                    # ramo sem upstream: não dá para conferir
    dados = git('-c', 'core.autocrlf=false', 'archive', '--format=zip', 'HEAD')
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        return {i.filename: z.read(i) for i in z.infolist() if not i.is_dir()}


def arquivos_da_pasta():
    """{caminho: bytes} da pasta como está, menos o que o .gitignore ignora."""
    nomes = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode('utf-8').split('\0')
    novos = set(git('ls-files', '-z', '--others', '--exclude-standard').decode('utf-8').split('\0'))
    arquivos = {}
    for nome in sorted(n for n in nomes if n):
        caminho = RAIZ / nome
        if caminho.is_file():                   # apagado na pasta mas ainda no git: fica de fora
            arquivos[nome] = caminho.read_bytes()
    sem_commit = sorted(n for n in novos if n in arquivos)
    if sem_commit:
        print(f'Vão no pacote {len(sem_commit)} arquivos que ainda não estão no git: ' + ', '.join(sem_commit))
    return arquivos


def baixar(url, sha256):
    """Baixa (ou reaproveita de dist/baixados/) e confere o SHA-256."""
    destino = BAIXADOS / url.rsplit('/', 1)[1]
    if destino.exists() and hashlib.sha256(destino.read_bytes()).hexdigest() == sha256:
        return destino.read_bytes()
    print(f'Baixando {url} ...')
    with urllib.request.urlopen(url, timeout=120) as r:
        dados = r.read()
    if hashlib.sha256(dados).hexdigest() != sha256:
        raise SystemExit(f'ERRO: o arquivo baixado de {url} não confere com o SHA-256 esperado. Nada foi gravado.')
    BAIXADOS.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(dados)
    return dados


def arquivos_do_python():
    """{caminho no pacote: bytes} da pasta python/: o Python embeddable + o pywinusb."""
    arquivos = {}
    with zipfile.ZipFile(io.BytesIO(baixar(PYTHON_URL, PYTHON_SHA256))) as z:
        for i in z.infolist():
            if not i.is_dir():
                arquivos['python/' + i.filename] = z.read(i)
    if 'python/' + PTH_NOME not in arquivos:
        raise SystemExit(f'ERRO: o Python {PYTHON_VERSAO} não tem o {PTH_NOME} esperado')
    arquivos['python/' + PTH_NOME] = PTH.replace('\n', '\r\n').encode('ascii')
    arquivos['python/LEIA-ME.txt'] = LEIA_ME.replace('\n', '\r\n').encode('utf-8')

    # o pywinusb é só Python (usa ctypes): basta copiar a pasta do pacote dele para site-packages
    origem = f'pywinusb-{PYWINUSB_VERSAO}/'
    with zipfile.ZipFile(io.BytesIO(baixar(PYWINUSB_URL, PYWINUSB_SHA256))) as z:
        for i in z.infolist():
            if i.filename.startswith(origem + 'pywinusb/') and not i.is_dir():
                arquivos['python/Lib/site-packages/' + i.filename[len(origem):]] = z.read(i)
        arquivos['python/Lib/site-packages/pywinusb/LICENSE.txt'] = z.read(origem + 'LICENSE.txt')
    return arquivos


def no_pacote(projeto, python):
    """{caminho no zip: bytes}: na pasta de cima só o que o aluno usa; o resto do projeto e o Python em sistema/."""
    arquivos = {}
    for nome, dados in projeto.items():
        if nome in DO_PROFESSOR or nome.startswith(DO_ALUNO):
            arquivos[nome] = para_o_aluno(nome, dados) if nome.startswith('.vscode/') else dados
        else:
            arquivos[f'{SISTEMA}/{nome}'] = dados
    for nome, dados in python.items():
        arquivos[f'{SISTEMA}/{nome}'] = dados
    arquivos[ABRIR] = ABRIR_CMD.replace('\n', '\r\n').encode('ascii')
    arquivos['LEIA-ME.txt'] = LEIA_ME_ALUNO.replace('\n', '\r\n').encode('utf-8-sig')
    return arquivos


def montar(da_pasta):
    projeto = arquivos_da_pasta() if da_pasta else arquivos_do_commit()
    projeto = {n: d for n, d in projeto.items() if not n.startswith(('python/', 'dist/'))}
    for preciso in ('ferramentas/rodar.cmd', '.vscode/tasks.json', 'enviar.py', 'robo.py'):
        if preciso not in projeto:
            raise SystemExit(f'ERRO: falta {preciso} no {"projeto" if da_pasta else "último commit"}. '
                             'Faça o commit ou use --pasta.')
    if b'rodar.cmd' not in projeto['.vscode/tasks.json']:
        raise SystemExit('ERRO: as tarefas (.vscode/tasks.json) não usam o ferramentas/rodar.cmd: '
                         'o Python do pacote ficaria sem uso.')
    python = arquivos_do_python()
    arquivos = no_pacote(projeto, python)

    DIST.mkdir(exist_ok=True)
    temporario = PACOTE.with_suffix('.tmp')
    agora = time.localtime()[:6]
    with zipfile.ZipFile(temporario, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for nome, dados in sorted(arquivos.items()):
            z.writestr(zipfile.ZipInfo(nome, agora), dados, zipfile.ZIP_DEFLATED)
    os.replace(temporario, PACOTE)
    mb = PACOTE.stat().st_size / 1e6
    print(f'[OK] {PACOTE.relative_to(RAIZ)}: {mb:.1f} MB, {len(projeto)} arquivos do projeto '
          f'+ Python {PYTHON_VERSAO} + pywinusb {PYWINUSB_VERSAO}')
    return projeto


ESPERADO_EM_CIMA = {ABRIR, 'LEIA-ME.txt', 'meu_programa.py', 'calibracao.py', 'exemplos', SISTEMA, '.vscode'}


def zip_do_projeto(projeto, destino):
    """O projeto como o GitHub entrega (uma pasta de cima com tudo junto): para testar a atualização."""
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as z:
        for nome, dados in sorted(projeto.items()):
            z.writestr('est-robot-teste/' + nome, dados)


def testar(projeto):
    """Descompacta o pacote numa pasta temporária (com espaço e acento no nome, como as de verdade)
    e confere que ele funciona sozinho, do jeito que o aluno vê."""
    pasta = Path(tempfile.mkdtemp(prefix='est-robot teste ação '))
    try:
        with zipfile.ZipFile(PACOTE) as z:
            z.extractall(pasta)
        py = str(pasta / SISTEMA / 'python' / 'python.exe')
        rodar = str(pasta / SISTEMA / 'ferramentas' / 'rodar.cmd')
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        env.pop('PYTHONDONTWRITEBYTECODE', None)          # como no computador do aluno: o Python grava __pycache__
        projeto_zip = pasta.parent / (pasta.name + '-projeto.zip')
        zip_do_projeto(projeto, projeto_zip)

        tarefas = json.loads((pasta / TAREFAS_VSCODE).read_text(encoding='utf-8'))['tasks']
        faltam = sorted({c for t in tarefas for c in [*t.get('args', [])[:1], t.get('windows', {}).get('command', '')]
                         if c.startswith('${workspaceFolder}')
                         and not (pasta / c.replace('${workspaceFolder}', '').lstrip('/\\')).is_file()})
        testes = [
            ('na pasta de cima só o que o aluno usa', None, sorted(os.listdir(pasta)) == sorted(ESPERADO_EM_CIMA)),
            ('as tarefas do VS Code acham os arquivos em sistema/', None, not faltam),
            ('o Python do pacote acha o pywinusb', [py, '-c', 'import pywinusb.hid'], True),
            ('o rodar.cmd usa o Python do pacote, na pasta do aluno',
             [rodar, '-c', 'import os, sys; print(sys.executable); print(os.getcwd())'], True),
            ('o VS Code aponta para o Python do pacote',
             [py, '-c', 'import json, os; c = json.load(open(".vscode/settings.json", encoding="utf-8")); '
                        'assert os.path.isfile(c["python.defaultInterpreterPath"].replace("${workspaceFolder}/", "")); '
                        'assert c["files.exclude"]["sistema"]'], True),
            ('compila o meu_programa.py (com o calibracao.py da pasta do aluno)',
             [rodar, f'{SISTEMA}/enviar.py', 'meu_programa.py', '--so-compilar'], True),
            ('confere os gabaritos', [py, f'{SISTEMA}/verificar_gabaritos.py'], True),
            ('o "Atualizar o projeto" mantém a pasta do aluno limpa',
             [rodar, f'{SISTEMA}/ferramentas/atualizar.py', str(projeto_zip)], True),
        ]
        tudo_ok = True
        for titulo, comando, ok in testes:
            saida = ''
            if comando:
                r = subprocess.run(comando, cwd=pasta, env=env, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace')
                ok, saida = r.returncode == 0, r.stdout + r.stderr
                if 'rodar.cmd' in titulo:
                    linhas = r.stdout.strip().splitlines()
                    ok &= [l.lower() for l in linhas] == [py.lower(), str(pasta).lower()]
                if 'gabaritos' in titulo:
                    ok &= 'linguagem em portugues: OK' in r.stdout
                    resumo = [l for l in r.stdout.splitlines() if 'gabaritos identicos' in l or 'linguagem em' in l]
                    titulo += ' (' + '; '.join(resumo) + ')'
                if 'Atualizar' in titulo:
                    em_cima = sorted(os.listdir(pasta))
                    ok &= 'já estava em dia' in r.stdout and em_cima == sorted(ESPERADO_EM_CIMA)
                    saida += '\nna pasta de cima: ' + ', '.join(em_cima)
            elif 'tarefas' in titulo and faltam:
                saida = 'faltam: ' + ', '.join(faltam)
            elif 'cima' in titulo:
                saida = 'tem: ' + ', '.join(sorted(os.listdir(pasta)))
            print(f'  {"OK   " if ok else "FALHA"} {titulo}')
            if not ok:
                print('\n'.join('        ' + l for l in saida.strip().splitlines()[-15:]))
            tudo_ok &= ok
        return tudo_ok
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
        try:
            projeto_zip.unlink()
        except (OSError, UnboundLocalError):
            pass


def main():
    if sys.platform != 'win32' and '--testar' in sys.argv:
        raise SystemExit('ERRO: o --testar só funciona no Windows')
    projeto = montar(da_pasta='--pasta' in sys.argv)
    if '--testar' in sys.argv:
        print('Testando o pacote numa pasta temporária...')
        if not testar(projeto):
            raise SystemExit('ERRO: o pacote não passou no teste')
        print('[OK] pacote testado')


if __name__ == '__main__':
    main()
