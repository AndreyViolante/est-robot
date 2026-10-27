"""Monta o pacote para Windows com o Python dentro: dist/est-robot-windows.zip.

O pacote tem o projeto e, na pasta python/, o Python "embeddable" oficial do python.org já com o
pywinusb. O professor só descompacta, abre a pasta no VS Code e usa: as tarefas chamam
ferramentas/rodar.cmd, que usa esse Python. Nada precisa de administrador nem de internet.

Uso:
    python ferramentas/empacotar.py            arquivos do último commit (o que fica no GitHub depois do push)
    python ferramentas/empacotar.py --pasta    arquivos da pasta como estão agora, mesmo sem commit
    ... --testar                               depois de montar, descompacta numa pasta temporária e confere

Para trocar a versão do Python: mude PYTHON_VERSAO e PYTHON_SHA256. O SHA-256 está no arquivo
.sigstore ao lado do zip em python.org/ftp/python/<versão>/ (messageDigest, em base64).
"""
import hashlib, io, os, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile
from pathlib import Path

from atualizar import CONFIG_VSCODE, com_python_do_pacote

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

LEIA_ME = f"""Python {PYTHON_VERSAO} para Windows 64 bits (pacote "embeddable" oficial do python.org)
com o pywinusb {PYWINUSB_VERSAO} em Lib/site-packages.

Não precisa instalar: as tarefas do VS Code usam este Python pelo ferramentas/rodar.cmd.
Para um Python mais novo, baixe o pacote do est-robot de novo.
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
    if CONFIG_VSCODE in projeto:                # o VS Code também usa o Python do pacote
        projeto[CONFIG_VSCODE] = com_python_do_pacote(projeto[CONFIG_VSCODE])
    python = arquivos_do_python()

    DIST.mkdir(exist_ok=True)
    temporario = PACOTE.with_suffix('.tmp')
    agora = time.localtime()[:6]
    with zipfile.ZipFile(temporario, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for nome, dados in sorted(projeto.items()) + sorted(python.items()):
            z.writestr(zipfile.ZipInfo(nome, agora), dados, zipfile.ZIP_DEFLATED)
    os.replace(temporario, PACOTE)
    mb = PACOTE.stat().st_size / 1e6
    print(f'[OK] {PACOTE.relative_to(RAIZ)}: {mb:.1f} MB, {len(projeto)} arquivos do projeto '
          f'+ Python {PYTHON_VERSAO} + pywinusb {PYWINUSB_VERSAO}')


def testar():
    """Descompacta o pacote numa pasta temporária (com espaço e acento no nome, como as de verdade)
    e confere que o Python de lá funciona sozinho."""
    pasta = Path(tempfile.mkdtemp(prefix='est-robot teste ação '))
    try:
        with zipfile.ZipFile(PACOTE) as z:
            z.extractall(pasta)
        py = str(pasta / 'python' / 'python.exe')
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        testes = [
            ('o Python do pacote acha o pywinusb', [py, '-c', 'import pywinusb.hid']),
            ('o rodar.cmd escolhe o Python do pacote',
             [str(pasta / 'ferramentas' / 'rodar.cmd'), '-c', 'import sys; print(sys.executable)']),
            ('o VS Code aponta para o Python do pacote',
             [py, '-c', 'import json, os; c = json.load(open(".vscode/settings.json", encoding="utf-8")); '
                        'assert os.path.isfile(c["python.defaultInterpreterPath"].replace("${workspaceFolder}/", ""))']),
            ('compila o meu_programa.py', [py, 'enviar.py', 'meu_programa.py', '--so-compilar']),
            ('confere os gabaritos', [py, 'verificar_gabaritos.py']),
        ]
        tudo_ok = True
        for titulo, comando in testes:
            r = subprocess.run(comando, cwd=pasta, env=env, capture_output=True, text=True,
                               encoding='utf-8', errors='replace')
            ok = r.returncode == 0
            if 'rodar.cmd' in titulo:
                ok &= r.stdout.strip().lower() == py.lower()
            if 'gabaritos' in titulo:
                ok &= 'linguagem em portugues: OK' in r.stdout
                resumo = [l for l in r.stdout.splitlines() if 'gabaritos identicos' in l or 'linguagem em' in l]
                titulo += ' (' + '; '.join(resumo) + ')'
            print(f'  {"OK   " if ok else "FALHA"} {titulo}')
            if not ok:
                print('\n'.join('        ' + l for l in (r.stdout + r.stderr).strip().splitlines()[-15:]))
            tudo_ok &= ok
        return tudo_ok
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def main():
    if sys.platform != 'win32' and '--testar' in sys.argv:
        raise SystemExit('ERRO: o --testar só funciona no Windows')
    montar(da_pasta='--pasta' in sys.argv)
    if '--testar' in sys.argv:
        print('Testando o pacote numa pasta temporária...')
        if not testar():
            raise SystemExit('ERRO: o pacote não passou no teste')
        print('[OK] pacote testado')


if __name__ == '__main__':
    main()
