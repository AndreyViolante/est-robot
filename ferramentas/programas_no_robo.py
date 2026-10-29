"""Programas gravados no robô: lista, roda, apaga e mostra a bateria.
Uso:
  python ferramentas/programas_no_robo.py                       lista e pergunta o que fazer
  python ferramentas/programas_no_robo.py --listar              só lista
  python ferramentas/programas_no_robo.py --rodar               lista e pergunta qual programa rodar
  python ferramentas/programas_no_robo.py --rodar meu_programa  roda vscode/meu_programa sem enviar de novo
  python ferramentas/programas_no_robo.py --apagar meu_programa apaga vscode/meu_programa (pede confirmação)
  python ferramentas/programas_no_robo.py --baixar              lista e pergunta qual programa baixar (pasta do_robo)
  python ferramentas/programas_no_robo.py --copiar              grava no robô ligado um programa da pasta do_robo
  python ferramentas/programas_no_robo.py --bateria             só mostra a bateria
No VS Code: Terminal > Executar Tarefa > "Programas no robô", "Rodar programa do robô", "Baixar programa do robô",
"Copiar programa para outro robô" ou "Bateria do robô".

Baixar e copiar: o programa sai do robô exatamente como foi gravado (também os feitos na IDE EST). Para passar o
programa de um robô para os outros da turma, baixe de um e use "Copiar programa para outro robô" em cada um.
Um programa baixado (.dbf) também roda no simulador: python simular.py do_robo/nome.dbf

Os programas que o VS Code grava ficam na pasta vscode do robô. Arquivo de outra pasta (gravado pela
IDE EST) só é apagado se você digitar o caminho completo dele, como aparece na lista.
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

PASTA = '/vscode/'
NOMES_NIVEL = ['muito fraca', 'fraca', 'média', 'boa', 'cheia']
BAIXADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'do_robo')


def _nome(caminho):
    """'/vscode/meu_programa.dbf' -> 'meu_programa' (o nome que o aluno conhece)."""
    nome = caminho[len(PASTA):]
    return nome[:-4] if nome.endswith('.dbf') else nome


def mostrar_bateria(est_protocol):
    try:
        nivel, texto = est_protocol.info_robo()
    except RuntimeError as e:
        print(f'Bateria: não deu para saber ({e}).')
        return
    if '--bruto' in sys.argv:
        print(f'(resposta: nível {nivel}, texto {texto!r})')
    if not 0 <= nivel <= 4:
        print(f'Bateria: o robô respondeu {nivel}, que não é um nível conhecido (0 a 4).')
        return
    print(f'Bateria: {NOMES_NIVEL[nivel]} ({nivel} de 4 tracinhos)')
    if nivel <= est_protocol.NIVEL_FRACO:
        print('  Carregue o robô! Com a bateria fraca os motores ficam fracos e os sensores leem errado,\n'
              '  e o programa parece que está com defeito sem estar.')


def mostrar_lista(arquivos):
    """Mostra os arquivos e devolve os da pasta vscode, na ordem dos números mostrados."""
    nossos = [a for a in arquivos if a[0].startswith(PASTA)]
    outros = [a for a in arquivos if not a[0].startswith(PASTA)]
    print()
    if nossos:
        print(f'Programas gravados pelo VS Code (pasta vscode do robô): {len(nossos)}')
        largura = max(len(_nome(c)) for c, _ in nossos)
        for i, (caminho, tamanho) in enumerate(nossos, 1):
            print(f'  {i:2}. {_nome(caminho):{largura}}   (tamanho {tamanho})')
    else:
        print('Nenhum programa gravado pelo VS Code (a pasta vscode do robô está vazia).')
    if outros:
        print()
        print(f'Arquivos de outras pastas (gravados pela IDE EST ou que já vêm no robô): {len(outros)}')
        for caminho, tamanho in outros:
            print(f'      {caminho}   (tamanho {tamanho})')
    print()
    return nossos


def confirmar(caminho):
    pergunta = (f'Apagar o programa {_nome(caminho)} (vscode) do robô?' if caminho.startswith(PASTA)
                else f'Apagar {caminho} do robô? Ele não foi gravado pelo VS Code.')
    try:
        resposta = input(f'{pergunta} Não tem como desfazer. Digite s e aperte Enter para apagar: ')
    except EOFError:
        return False
    return resposta.strip().lower() in ('s', 'sim')


def apagar(est_protocol, caminho):
    """Apaga depois de confirmar e confere na lista. True se apagou."""
    if not confirmar(caminho):
        print('Nada foi apagado.')
        return False
    try:
        ok = est_protocol.apagar_arquivo(caminho)
    except (RuntimeError, ValueError) as e:
        print(f'ERRO: {e}')
        return False
    if not ok:
        print(f'O robô disse que não conseguiu apagar {caminho}.')
        return False
    try:
        sobrou = any(c == caminho for c, _ in est_protocol.listar_arquivos())
    except RuntimeError:
        print(f'O robô disse que apagou {caminho} (não deu para conferir na lista).')
        return True
    if sobrou:
        print(f'O robô disse que apagou {caminho}, mas ele continua na lista.')
        return False
    print(f'Apagado: {caminho}')
    return True


def rodar(est_protocol, caminho):
    """Manda o robô executar um programa que já está gravado nele. True se mandou."""
    try:
        est_protocol.rodar_programa(caminho)
    except (RuntimeError, ValueError) as e:
        print(f'ERRO: {e}')
        return False
    nome = _nome(caminho) if caminho.startswith(PASTA) else caminho
    print(f'Mandei o robô rodar {nome}. Se ele não começou, inicie pelo menu do robô (pasta '
          f'{caminho.split("/")[1]}) e conte para o professor: este comando ainda não foi conferido em todos os robôs.')
    return True


def baixar(est_protocol, caminho):
    """Baixa um arquivo do robô para a pasta do_robo. Devolve o caminho do arquivo gravado (ou None)."""
    try:
        dados = est_protocol.baixar_arquivo(caminho)
    except (RuntimeError, ValueError) as e:
        print(f'ERRO: {e}')
        return None
    os.makedirs(BAIXADOS, exist_ok=True)
    pasta, arquivo = caminho.strip('/').split('/')
    nome = arquivo if pasta == 'vscode' else f'{pasta}_{arquivo}'
    destino = os.path.normpath(os.path.join(BAIXADOS, nome if nome.endswith('.dbf') else nome + '.dbf'))
    with open(destino, 'wb') as f:
        f.write(dados)
    print(f'Baixado: {caminho} ({len(dados)} bytes) -> {destino}')
    print('Para gravar em outro robô: ligue o outro robô e use "Copiar programa para outro robô".')
    print(f'Para ver no simulador: python simular.py "{destino}"')
    return destino


def copiar(est_protocol):
    """Grava no robô ligado um programa baixado (pasta do_robo), sem executar."""
    baixados = sorted(f for f in os.listdir(BAIXADOS) if f.endswith('.dbf')) if os.path.isdir(BAIXADOS) else []
    if not baixados:
        sys.exit('A pasta do_robo está vazia: baixe um programa primeiro (tarefa "Baixar programa do robô").')
    print('Programas baixados (pasta do_robo):')
    for i, f in enumerate(baixados, 1):
        print(f'  {i:2}. {f[:-4]}')
    try:
        texto = input('Digite o número do programa para gravar NESTE robô (Enter para sair): ').strip()
    except EOFError:
        return
    if not texto.isdigit() or not 1 <= int(texto) <= len(baixados):
        print('Nada foi gravado.')
        return
    arquivo = baixados[int(texto) - 1]
    with open(os.path.join(BAIXADOS, arquivo), 'rb') as f:
        dados = f.read()
    nome = arquivo[:-4][:20]
    try:
        est_protocol.upload(dados, prog_path=f'{PASTA}{nome}', verbose=False, executar=False)
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')
    print(f'Gravado neste robô como vscode/{nome} (sem executar): inicie pelo menu do robô.')


def escolher(nossos, arquivos, texto):
    """O que o usuário digitou -> caminho de um arquivo da lista, ou None.
    Número ou nome = programa da pasta vscode; outra pasta só com o caminho completo."""
    texto = texto.strip()
    if texto.isdigit():
        n = int(texto)
        return nossos[n - 1][0] if 1 <= n <= len(nossos) else None
    if texto.startswith('/'):
        return texto if any(c == texto for c, _ in arquivos) else None
    for caminho, _ in nossos:
        if texto in (_nome(caminho), caminho[len(PASTA):]):
            return caminho
    return None


def main():
    try:
        import pywinusb.hid  # noqa: F401
    except ImportError:
        sys.exit('ERRO: falta instalar o pywinusb. Rode o instalar.bat ou: pip install pywinusb')

    import est_protocol
    from enviar import AVISO_IDE, ide_est_aberta

    if ide_est_aberta():
        print(f'{AVISO_IDE}\n')
    try:
        est_protocol.find_robot()
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')

    mostrar_bateria(est_protocol)
    if '--bateria' in sys.argv:
        return
    if '--copiar' in sys.argv:
        return copiar(est_protocol)

    try:
        arquivos = est_protocol.listar_arquivos()
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')
    nossos = mostrar_lista(arquivos)

    if '--apagar' in sys.argv:
        i = sys.argv.index('--apagar')
        if i + 1 >= len(sys.argv):
            sys.exit('ERRO: diga o nome do programa depois de --apagar')
        caminho = escolher(nossos, arquivos, sys.argv[i + 1])
        if caminho is None:
            sys.exit(f'ERRO: "{sys.argv[i + 1]}" não está na lista acima. Arquivo de outra pasta: use o '
                     'caminho completo, como aparece na lista.')
        sys.exit(0 if apagar(est_protocol, caminho) else 1)
    if '--listar' in sys.argv:
        return
    acao = 'rodar' if '--rodar' in sys.argv else 'baixar' if '--baixar' in sys.argv else None
    if acao:
        i = sys.argv.index(f'--{acao}')
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
            caminho = escolher(nossos, arquivos, sys.argv[i + 1])
            if caminho is None:
                sys.exit(f'ERRO: "{sys.argv[i + 1]}" não está na lista acima.')
            feito = rodar(est_protocol, caminho) if acao == 'rodar' else baixar(est_protocol, caminho)
            sys.exit(0 if feito else 1)

    while arquivos:
        if acao:
            print(f'Digite o número do programa para {"o robô rodar" if acao == "rodar" else "baixar"} '
                  '(arquivo de outra pasta: o caminho completo).')
        else:
            print('Digite o número de um programa para apagar; r e o número para o robô rodar (ex.: r 2);')
            print('b e o número para baixar. Arquivo de outra pasta: o caminho completo, como aparece na lista.')
        print('Para sair, só aperte Enter.')
        try:
            texto = input('> ')
        except EOFError:
            return
        if not texto.strip():
            return
        pedido = acao
        if texto.strip().lower()[:2] in ('r ', 'b '):
            pedido = 'rodar' if texto.strip().lower().startswith('r') else 'baixar'
            texto = texto.strip()[2:]
        caminho = escolher(nossos, arquivos, texto)
        if caminho is None:
            print(f'"{texto.strip()}" não está na lista.\n')
            continue
        if pedido == 'rodar':
            rodar(est_protocol, caminho)
            return
        if pedido == 'baixar':
            baixar(est_protocol, caminho)
            return
        if apagar(est_protocol, caminho):
            try:
                arquivos = est_protocol.listar_arquivos()
            except RuntimeError as e:
                sys.exit(f'ERRO: {e}')
            nossos = mostrar_lista(arquivos)
        else:
            print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nNada mais foi feito.')
