"""Atualiza o projeto com a última versão publicada no GitHub, sem mexer nos arquivos do professor.

Baixa a última versão publicada (página Releases do GitHub), mostra o que mudou e troca os arquivos
do projeto pelos novos. Nunca apaga nada e nunca troca:
  - calibracao.py e meu_programa.py (as medidas do robô e o programa do professor);
    o calibracao.py só ganha os campos novos, com o valor padrão, e as medidas ficam como estão;
  - os .py que não existem no projeto oficial (os programas dos alunos);
  - a pasta python/ (o Python do pacote para Windows).
A versão antiga de cada arquivo trocado fica guardada num zip em copias_de_seguranca/.

Uso: no VS Code, Terminal > Executar Tarefa > Atualizar o projeto.
    ferramentas\\rodar.cmd ferramentas\\atualizar.py --desfazer   volta os arquivos da última atualização
                                                                  (tarefa "Voltar para a versão anterior")
    ferramentas\\rodar.cmd ferramentas\\atualizar.py --master     o último commit, para quem testa as
                                                                  novidades antes de sair a versão
Sem internet no computador: baixe o zip da versão em outro (no GitHub, Releases > Source code (zip)) e rode
    ferramentas\\rodar.cmd ferramentas\\atualizar.py caminho\\do\\est-robot.zip
"""
import ast, http.client, io, json, os, re, ssl, sys, time, urllib.error, urllib.request, zipfile
from pathlib import Path, PurePosixPath

REPO = 'AndreyViolante/est-robot'
API_ULTIMA = f'https://api.github.com/repos/{REPO}/releases/latest'
PAGINA_ULTIMA = f'https://github.com/{REPO}/releases/latest'
ZIP_DA_VERSAO = 'https://github.com/' + REPO + '/archive/refs/tags/{tag}.zip'
URL_MASTER = f'https://github.com/{REPO}/archive/refs/heads/master.zip'
RAIZ = Path(__file__).resolve().parent.parent
# podem vir no projeto oficial, mas cada professor muda os seus: nunca são trocados
DO_PROFESSOR = ['calibracao.py', 'meu_programa.py']
COPIAS = 'copias_de_seguranca'
NAO_MEXER = {'.git', 'python', 'dist', COPIAS}           # pastas que a atualização nunca toca
NAO_PROCURAR = NAO_MEXER | {'__pycache__', '_investigacao', '_legado', '.venv', 'venv'}

SEM_INTERNET = """Não foi possível baixar a versão nova: o computador está sem internet
(ou a rede bloqueou o GitHub). Confira a conexão e rode a tarefa de novo. Nada foi mudado.

Sem internet nenhuma neste computador? Em outro, baixe o zip da última versão no GitHub
(Releases > Source code (zip)), traga num pendrive e rode aqui, no terminal do VS Code:
    ferramentas\\rodar.cmd ferramentas\\atualizar.py caminho\\do\\est-robot.zip"""


def _abrir(url, timeout):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'est-robot'}),
                                  timeout=timeout)


def ultima_versao(timeout=15):
    """Nome da última versão publicada (ex.: 'v0.2.0'), ou None se não der para saber."""
    try:
        with _abrir(API_ULTIMA, timeout) as r:
            return json.load(r).get('tag_name') or None
    except Exception:
        pass
    try:            # sem a API (limite de acessos): /releases/latest redireciona para /releases/tag/<nome>
        with _abrir(PAGINA_ULTIMA, timeout) as r:
            final = r.geturl()
        if '/releases/tag/' in final:
            return final.rstrip('/').rsplit('/', 1)[-1]
    except Exception:
        pass
    return None


VERSAO_TXT = f'https://github.com/{REPO}/releases/latest/download/versao.txt'


def ultima_versao_contando(timeout=2):
    """Como ultima_versao, mas lendo o versao.txt anexado à última versão: o GitHub conta os downloads
    dele, e como cada instalação pergunta no máximo uma vez por dia, a conta diária é o número de
    instalações em uso (só um número, sem nome nem nada de quem perguntou)."""
    try:
        with _abrir(VERSAO_TXT, timeout) as r:
            texto = r.read(64).decode('ascii', 'replace').strip()
        if re.fullmatch(r'v?\d+\.\d+\.\d+', texto):
            return texto
    except Exception:
        pass
    return ultima_versao(timeout)


def numeros(versao):
    """'v0.10.2' -> (0, 10, 2), para comparar versões."""
    return tuple(int(n) for n in re.findall(r'\d+', str(versao))[:3])


def versao_instalada():
    try:
        return (RAIZ / 'VERSAO').read_text(encoding='utf-8').strip() or None
    except OSError:
        return None


def baixar(url):
    try:
        with _abrir(url, 60) as r:
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
        commit = z.comment.decode('ascii', 'replace')[:7]   # o GitHub grava o commit no comentário do zip
    except zipfile.BadZipFile:
        sys.exit('O arquivo baixado veio com defeito (internet instável?). Rode a tarefa de novo. Nada foi mudado.')
    if 'robo.py' not in arquivos or 'enviar.py' not in arquivos:
        sys.exit('O arquivo não parece ser o projeto est-robot. Nada foi mudado.')
    return arquivos, commit


def novidades_desde(texto, instalada):
    """As seções "## x.y.z" do NOVIDADES.md mais novas que a versão instalada."""
    secoes = re.split(r'(?m)^## ', texto)[1:]
    return ['## ' + s.strip() for s in secoes
            if not instalada or numeros(s.split()[0]) > numeros(instalada)]


def campos_novos_da_calibracao(local, novo):
    """Linhas do calibracao.py novo com os campos que o do professor ainda não tem."""
    try:
        nomes_locais = {alvo.id for no in ast.parse(local).body if isinstance(no, ast.Assign)
                        for alvo in no.targets if isinstance(alvo, ast.Name)}
        arvore_nova = ast.parse(novo)
    except SyntaxError:
        return [], []
    linhas, campos = novo.splitlines(), []
    trechos = []
    for no in arvore_nova.body:
        if isinstance(no, ast.Assign):
            nomes = [a.id for a in no.targets if isinstance(a, ast.Name)]
            if nomes and not any(n in nomes_locais for n in nomes):
                campos += nomes
                trechos += linhas[no.lineno - 1:no.end_lineno]
    return campos, trechos


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


def desfazer():
    """Volta os arquivos guardados pela última atualização."""
    copias = sorted((RAIZ / COPIAS).glob('antes-de-atualizar-*.zip'))
    if not copias:
        sys.exit('Não há atualização para desfazer (a pasta copias_de_seguranca não tem cópias). Nada foi mudado.')
    ultima = copias[-1]
    with zipfile.ZipFile(ultima) as z:
        nomes = [i.filename for i in z.infolist() if not i.is_dir()]
        for nome in nomes:
            gravar(nome, z.read(nome))
    ultima.rename(ultima.with_name(ultima.name.replace('antes-de-atualizar', 'desfeita')))
    mostrar('Voltaram para como estavam antes da atualização', nomes)
    print(f'\nPronto! Versão agora: {versao_instalada() or "desconhecida"}. '
          'Rodando de novo, volta mais uma atualização (se houver cópia).')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if (RAIZ / '.git').exists() and '--mesmo-com-git' not in sys.argv:
        sys.exit('Esta pasta é uma cópia do git (de quem desenvolve o projeto): atualize com "git pull".')
    if '--desfazer' in sys.argv:
        return desfazer()

    instalada = versao_instalada()
    if args:
        print(f'Lendo {args[0]} (sem baixar)...')
        try:
            dados = Path(args[0]).read_bytes()
        except OSError:
            sys.exit(f'Não achei o arquivo {args[0]}. Confira o caminho (ex.: D:\\est-robot.zip). Nada foi mudado.')
    elif '--master' in sys.argv:
        print('Baixando o último commit do projeto (pode ter coisas ainda não testadas)...')
        dados = baixar(URL_MASTER)
    else:
        print('Procurando a última versão publicada (github.com/AndreyViolante/est-robot/releases)...')
        nome = ultima_versao()
        if nome is None:
            sys.exit(SEM_INTERNET)
        nova = nome.lstrip('vV')
        if instalada and numeros(instalada) >= numeros(nova) and '--forcar' not in sys.argv:
            print(f'\nVocê já tem a versão mais nova ({instalada}). Nada foi mudado.')
            return
        print(f'Versão instalada: {instalada or "desconhecida"}  ->  nova: {nova}')
        dados = baixar(ZIP_DA_VERSAO.format(tag=nome))
    oficial, commit = ler_projeto(dados)

    if 'NOVIDADES.md' in oficial:
        secoes = novidades_desde(oficial['NOVIDADES.md'].decode('utf-8', 'replace'), instalada)
        if secoes:
            print('\nO que mudou:\n')
            print('\n\n'.join(secoes))

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

    # calibracao.py: só acrescenta os campos que a versão nova trouxe, com o valor padrão
    campos, trechos = [], []
    if 'calibracao.py' in oficial and (RAIZ / 'calibracao.py').exists():
        local = (RAIZ / 'calibracao.py').read_text(encoding='utf-8')
        campos, trechos = campos_novos_da_calibracao(local, oficial['calibracao.py'].decode('utf-8', 'replace'))

    copia = guardar_copia(trocar + (['calibracao.py'] if campos else [])) if trocar or campos else None
    falhas = {}
    for nome in trocar + novos:
        try:
            gravar(nome, oficial[nome])
        except OSError as e:
            falhas[nome] = e.strerror or str(e)
    if campos:
        aviso = (f'\n\n# Acrescentado pela atualização (valor padrão; ajuste para o seu robô):\n'
                 + '\n'.join(trechos) + '\n')
        try:
            with open(RAIZ / 'calibracao.py', 'a', encoding='utf-8', newline='\n') as f:
                f.write(aviso)
        except OSError as e:
            falhas['calibracao.py'] = e.strerror or str(e)

    mostrar('Atualizados', [n for n in trocar if n not in falhas])
    mostrar('Novos', [n for n in novos if n not in falhas])
    if campos and 'calibracao.py' not in falhas:
        print(f'\nNo seu calibracao.py entraram campos novos, com o valor padrão: {", ".join(campos)}.'
              '\nAs suas medidas não mudaram.')
    print('\nSeus, não foram mexidos:')
    print('  ' + (', '.join(mantidos) or '(nenhum)'))
    if seus:
        print(f'  e {len(seus)} programa(s) que não são do projeto oficial: '
              + ', '.join(n.replace('/', os.sep) for n in seus[:10]) + (' ...' if len(seus) > 10 else ''))
    if copia:
        print(f'\nA versão antiga dos arquivos trocados ficou guardada em {copia.relative_to(RAIZ)}'
              '\n(para voltar: Terminal > Executar Tarefa > Voltar para a versão anterior)')
    if falhas:
        mostrar('NÃO deu para gravar (feche o programa que está usando o arquivo e rode de novo)',
                [f'{n} ({motivo})' for n, motivo in falhas.items()])
        sys.exit(1)
    if trocar or novos or campos:
        print(f'\nPronto! Projeto atualizado para a versão {versao_instalada() or commit} '
              f'({em_dia} arquivos já estavam em dia).')
    else:
        print(f'\nO projeto já estava em dia ({em_dia} arquivos conferidos). Nada foi mudado.')


if __name__ == '__main__':
    main()
