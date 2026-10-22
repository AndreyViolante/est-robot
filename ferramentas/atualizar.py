"""Atualiza o projeto com a versão mais nova do GitHub, sem mexer nos arquivos do professor.

Baixa o projeto oficial e troca os arquivos dele pelos novos. Nunca apaga nada e nunca troca:
  - calibracao.py, meu_programa.py e minha_pid.py (as medidas do robô e os programas do professor);
  - os .py que não existem no projeto oficial (os programas dos alunos);
  - a pasta python/ (o Python do pacote para Windows).
A versão antiga de cada arquivo trocado fica guardada num zip em copias_de_seguranca/.

Uso: no VS Code, Terminal > Executar Tarefa > Atualizar o projeto.
Sem internet no computador: baixe o ZIP do projeto em outro (no GitHub, Code > Download ZIP) e rode
    ferramentas\\rodar.cmd ferramentas\\atualizar.py caminho\\do\\est-robot-master.zip
"""
import http.client, io, os, ssl, sys, time, urllib.error, urllib.request, zipfile
from pathlib import Path, PurePosixPath

URL = 'https://github.com/AndreyViolante/est-robot/archive/refs/heads/master.zip'
RAIZ = Path(__file__).resolve().parent.parent
# podem vir no projeto oficial, mas cada professor muda os seus: nunca são trocados
DO_PROFESSOR = ['calibracao.py', 'meu_programa.py', 'minha_pid.py']
COPIAS = 'copias_de_seguranca'
NAO_MEXER = {'.git', 'python', 'dist', COPIAS}           # pastas que a atualização nunca toca
NAO_PROCURAR = NAO_MEXER | {'__pycache__', '_investigacao', '_legado', '.venv', 'venv'}

SEM_INTERNET = """Não foi possível baixar a versão nova: o computador está sem internet
(ou a rede bloqueou o GitHub). Confira a conexão e rode a tarefa de novo. Nada foi mudado.

Sem internet nenhuma neste computador? Em outro, baixe o ZIP do projeto no GitHub
(Code > Download ZIP), traga num pendrive e rode aqui, no terminal do VS Code:
    ferramentas\\rodar.cmd ferramentas\\atualizar.py caminho\\do\\est-robot-master.zip"""


def baixar():
    print('Baixando a versão mais nova do projeto (github.com/AndreyViolante/est-robot)...')
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'est-robot'}),
                                    timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f'O GitHub respondeu com erro ({e.code} {e.reason}). Tente de novo mais tarde. Nada foi mudado.')
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        if isinstance(getattr(e, 'reason', e), ssl.SSLError):
            sys.exit('A conexão segura com o GitHub falhou: a rede da escola pode estar bloqueando.\n'
                     f'({e})\n\n' + SEM_INTERNET)
        sys.exit(SEM_INTERNET)


def ler_projeto(dados):
    """{caminho com '/': bytes} do zip do projeto, sem a pasta de cima (est-robot-master/)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(dados))
        nomes = [i for i in z.infolist() if not i.is_dir()]
        topo = {i.filename.split('/')[0] for i in nomes}
        tirar = len(topo) == 1 and not any(i.filename == 'robo.py' for i in nomes)
        arquivos = {}
        for i in nomes:
            partes = PurePosixPath(i.filename).parts[1 if tirar else 0:]
            if not partes or i.filename.startswith('/') or any(p in ('', '.', '..') or ':' in p for p in partes):
                continue                                  # caminho estranho: não grava fora da pasta
            arquivos['/'.join(partes)] = z.read(i)
        versao = z.comment.decode('ascii', 'replace')[:7]   # o GitHub grava o commit no comentário do zip
    except zipfile.BadZipFile:
        sys.exit('O arquivo baixado veio com defeito (internet instável?). Rode a tarefa de novo. Nada foi mudado.')
    if 'robo.py' not in arquivos or 'enviar.py' not in arquivos:
        sys.exit('O arquivo não parece ser o projeto est-robot. Nada foi mudado.')
    return arquivos, versao


def iguais(atual, novo, nome):
    if atual == novo:
        return True
    if nome.endswith(('.bat', '.cmd')):           # nesses a quebra de linha do Windows importa
        return False
    return atual.replace(b'\r\n', b'\n') == novo.replace(b'\r\n', b'\n')


def programas_do_professor(oficial):
    """Os .py da pasta que não estão no projeto oficial (programas dos alunos)."""
    achados = []
    for pasta, subpastas, arquivos in os.walk(RAIZ):
        subpastas[:] = sorted(s for s in subpastas if s not in NAO_PROCURAR)
        for arq in sorted(arquivos):
            nome = Path(pasta, arq).relative_to(RAIZ).as_posix()
            if arq.endswith('.py') and nome not in oficial and nome not in DO_PROFESSOR:
                achados.append(nome)
    return achados


def guardar_copia(nomes):
    """Zip com a versão antiga dos arquivos que vão ser trocados."""
    pasta = RAIZ / COPIAS
    pasta.mkdir(exist_ok=True)
    copia = pasta / time.strftime('antes-de-atualizar-%Y-%m-%d_%H-%M-%S.zip')
    with zipfile.ZipFile(copia, 'w', zipfile.ZIP_DEFLATED) as z:
        for nome in nomes:
            z.write(RAIZ / nome, nome)
    return copia


def gravar(nome, dados):
    destino = RAIZ / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + '.atualizando')
    temporario.write_bytes(dados)
    os.replace(temporario, destino)


def mostrar(titulo, nomes, limite=20):
    if nomes:
        print(f'\n{titulo} ({len(nomes)}):')
        for nome in nomes[:limite]:
            print('  ' + nome.replace('/', os.sep))
        if len(nomes) > limite:
            print(f'  ... e mais {len(nomes) - limite}')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if (RAIZ / '.git').exists() and '--mesmo-com-git' not in sys.argv:
        sys.exit('Esta pasta é uma cópia do git (de quem desenvolve o projeto): atualize com "git pull".')
    if args:
        print(f'Lendo {args[0]} (sem baixar)...')
        try:
            dados = Path(args[0]).read_bytes()
        except OSError:
            sys.exit(f'Não achei o arquivo {args[0]}. Confira o caminho (ex.: D:\\est-robot-master.zip). Nada foi mudado.')
    else:
        dados = baixar()
    oficial, versao = ler_projeto(dados)
    if versao and all(c in '0123456789abcdef' for c in versao):
        print(f'Versão do GitHub: {versao}')

    trocar, novos, em_dia = [], [], 0
    for nome, novo in sorted(oficial.items()):
        destino = RAIZ / nome
        if nome.split('/')[0] in NAO_MEXER or (nome in DO_PROFESSOR and destino.exists()):
            continue
        if destino.is_dir():
            print(f'(pulei {nome}: na sua pasta isso é uma pasta, não um arquivo)')
        elif not destino.exists():
            novos.append(nome)
        elif iguais(destino.read_bytes(), novo, nome):
            em_dia += 1
        else:
            trocar.append(nome)
    mantidos = [n for n in DO_PROFESSOR if (RAIZ / n).exists()]
    seus = programas_do_professor(oficial)

    copia = guardar_copia(trocar) if trocar else None
    falhas = {}
    for nome in trocar + novos:
        try:
            gravar(nome, oficial[nome])
        except OSError as e:
            falhas[nome] = e.strerror or str(e)

    mostrar('Atualizados', [n for n in trocar if n not in falhas])
    mostrar('Novos', [n for n in novos if n not in falhas])
    print('\nSeus, não foram mexidos:')
    print('  ' + (', '.join(mantidos) or '(nenhum)'))
    if seus:
        print(f'  e {len(seus)} programa(s) que não são do projeto oficial: '
              + ', '.join(n.replace('/', os.sep) for n in seus[:10]) + (' ...' if len(seus) > 10 else ''))
    if copia:
        print(f'\nA versão antiga dos arquivos trocados ficou guardada em {copia.relative_to(RAIZ)}')
    if falhas:
        mostrar('NÃO deu para gravar (feche o programa que está usando o arquivo e rode de novo)',
                [f'{n} ({motivo})' for n, motivo in falhas.items()])
        sys.exit(1)
    if trocar or novos:
        print(f'\nPronto! Projeto atualizado ({em_dia} arquivos já estavam em dia).')
    else:
        print(f'\nO projeto já estava na versão mais nova ({em_dia} arquivos conferidos). Nada foi mudado.')


if __name__ == '__main__':
    main()
