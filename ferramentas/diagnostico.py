"""Diagnóstico para pedir ajuda: junta num texto curto a versão do projeto, o Python, o robô (firmware,
bateria, portas, programas gravados) e a calibração, e copia para colar no WhatsApp.

Uso: no VS Code, Terminal > Executar Tarefa > Diagnóstico (para pedir ajuda)
     python ferramentas/diagnostico.py --nao-copiar     só mostra, sem copiar

Não entra nada pessoal: nem nome do computador, nem usuário, nem pastas.
"""
import ast, os, platform, subprocess, sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RAIZ)



def projeto():
    try:
        versao = open(os.path.join(RAIZ, 'VERSAO'), encoding='utf-8').read().strip()
    except OSError:
        versao = '?'
    if os.path.isdir(os.path.join(RAIZ, '.git')):
        jeito = 'cópia do git'
    elif os.path.isfile(os.path.join(RAIZ, 'python', 'python.exe')):
        jeito = 'pacote com o Python dentro'
    else:
        jeito = 'Python do computador'
    return f'EST-ROBOT {versao} ({jeito})'


def python():
    do_pacote = os.path.normcase(os.path.abspath(sys.executable)).startswith(
        os.path.normcase(os.path.abspath(os.path.join(RAIZ, 'python'))))
    try:
        import pywinusb.hid  # noqa: F401
        usb = 'pywinusb ok'
    except ImportError:
        usb = 'FALTA o pywinusb'
    return f'Python {platform.python_version()} ({"do pacote" if do_pacote else "do computador"}), {usb}'


def calibracao():
    """Os valores do calibracao.py (só números, textos e True/False)."""
    try:
        arvore = ast.parse(open(os.path.join(RAIZ, 'calibracao.py'), encoding='utf-8').read())
    except (OSError, SyntaxError) as e:
        return f'não deu para ler o calibracao.py ({type(e).__name__})'
    valores = []
    for no in arvore.body:
        if isinstance(no, ast.Assign):
            try:
                valor = ast.literal_eval(no.value)
            except ValueError:
                continue
            valores += [f'{alvo.id}={valor!r}' for alvo in no.targets if isinstance(alvo, ast.Name)]
    return ', '.join(valores) or '(vazio)'


def robo_no_usb():
    """Linhas sobre o robô. Cada pergunta é feita à parte: se uma falhar, as outras ainda aparecem."""
    from enviar import ide_est_aberta
    linhas = [f'IDE EST aberta: {"SIM (feche para enviar)" if ide_est_aberta() else "não"}']
    try:
        from est_protocol import find_robot
        find_robot()
    except RuntimeError as e:
        return linhas + [f'Robô no USB: não ({e})']
    import est_protocol as p
    linhas.append('Robô no USB: sim')

    def pergunta(titulo, funcao):
        try:
            resposta = funcao()
        except (RuntimeError, OSError, ValueError) as e:
            resposta = f'erro ({e})'
        linhas.append(f'{titulo}: {"sem resposta" if resposta is None else resposta}')

    pergunta('Firmware', p.firmware)

    def bateria():
        nivel, _ = p.info_robo()
        return f'{nivel} de 4' + (' (FRACA: carregue)' if nivel <= p.NIVEL_FRACO else '')
    pergunta('Bateria', bateria)

    def portas():
        ligadas = p.portas_ligadas()
        if ligadas is None:
            return None
        from enviar import TIPOS
        return ', '.join(f'{porta} {TIPOS.get(tipo, f"tipo {tipo}")}' for porta, tipo in ligadas.items()) or 'nada ligado'
    pergunta('Portas', portas)

    def programas():
        arquivos = p.listar_arquivos()
        return f'{len(arquivos)} ({sum(n.startswith("/vscode/") for n, _ in arquivos)} na pasta vscode)'
    pergunta('Programas gravados', programas)

    def memoria():
        bruta = p.memoria_bruta()
        return None if bruta is None else bruta.hex(' ')
    pergunta('Memória (resposta 03)', memoria)
    return linhas


def copiar(texto):
    """Copia para a área de transferência do Windows. False se não der."""
    if sys.platform != 'win32':
        return False
    try:
        subprocess.run(['clip'], input=texto.encode('utf-16'), check=True)     # com BOM: o clip lê acentos
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def main():
    print('Juntando as informações (com o robô no USB, leva uns segundos)...\n')
    linhas = [
        '*Diagnóstico EST-ROBOT*',
        projeto(),
        f'{platform.system()} {platform.release()} ({platform.version()})',
        python(),
    ]
    if sys.platform == 'win32':
        linhas += robo_no_usb()
    linhas.append(f'Calibração: {calibracao()}')
    texto = '\n'.join(linhas)
    print(texto)
    if '--nao-copiar' not in sys.argv and copiar(texto):
        print('\nCopiado! Cole no WhatsApp (Ctrl+V) junto com o que aconteceu e o erro que apareceu.')
    else:
        print('\nSelecione o texto acima, copie e mande junto com o que aconteceu e o erro que apareceu.')


if __name__ == '__main__':
    main()
