"""Teste geral no robô: confere, em sequência, o que ainda não foi visto funcionando numa controladora.

Uso: no VS Code, Terminal > Executar Tarefa > Teste geral no robô
     (robô carregado, no USB e no chão, com espaço em volta; IDE EST fechada).
Em cada passo o teste manda um programa para o robô, diz o que deve acontecer e pergunta se aconteceu
(s = sim, n = não, p = pular). No fim grava resultado_teste_geral.txt nesta pasta.

    python ferramentas/teste_geral.py --sem-robo     só confere se os programas do teste compilam
"""
import datetime, os, sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RAIZ)

import robo
from estc import compilar

SEM_ROBO = '--sem-robo' in sys.argv
RESULTADOS = []                     # (passo, resultado, observação)
PAGINA = 'https://andreyviolante.github.io/est-robot/programar/'


def titulo(texto):
    print(f'\n{"=" * 70}\n{texto}\n{"=" * 70}')


def perguntar(texto, opcoes=('s', 'n', 'p')):
    if SEM_ROBO:
        return 'p'
    while True:
        r = input(f'{texto} ({"/".join(opcoes)}) ').strip().lower()
        if r in opcoes:
            return r
        print(f'  Responda com {", ".join(opcoes)}.')


def anotar(passo, resposta, obs=''):
    resultado = {'s': 'FUNCIONOU', 'n': 'NÃO FUNCIONOU', 'p': 'pulado'}.get(resposta, resposta)
    RESULTADOS.append((passo, resultado, obs))
    print(f'  -> {passo}: {resultado}' + (f' ({obs})' if obs else ''))


def programa(escrever):
    """Monta um programa com os comandos do robo.py e devolve os bytes."""
    robo.novo_programa()
    escrever()
    return compilar(robo.programa())


def enviar(nome, escrever, executar=True):
    """Compila e manda para o robô. Se o robô não for achado, deixa reconectar e tentar de novo."""
    dados = programa(escrever)
    if SEM_ROBO:
        print(f'  [compila] {nome}: {len(dados)} bytes')
        return True
    from est_protocol import upload
    while True:
        try:
            upload(dados, prog_path=f'/vscode/{nome}', verbose=False, executar=executar)
            return True
        except RuntimeError as e:
            print(f'  ERRO: {e}')
            if perguntar('  Reconectou o robô e quer tentar de novo?', ('s', 'n')) == 'n':
                return False


# ---------------------------------------------------------------- passos

def preparar():
    titulo('Preparação')
    from enviar import AVISO_IDE, ide_est_aberta
    if ide_est_aberta():
        print(AVISO_IDE)
        input('Feche a IDE EST e aperte Enter para continuar...')
    from est_protocol import NIVEL_FRACO, find_robot, firmware, info_robo, memoria_bruta, portas_ligadas
    while True:
        try:
            find_robot()
            break
        except RuntimeError as e:
            print(f'ERRO: {e}')
            input('Ligue o robô, ponha o cabo e aperte Enter para tentar de novo...')
    versao = firmware() or '?'
    try:
        nivel, texto = info_robo()
        bateria = f'{nivel} de 4 (resposta "{texto}")'
    except RuntimeError as e:
        nivel, bateria = None, f'sem resposta ({e})'
    portas = portas_ligadas()
    memoria = memoria_bruta()
    print(f'Robô encontrado. Firmware: {versao}')
    print(f'Bateria: {bateria}')
    print(f'Portas com algo ligado: {portas}')
    anotar('Firmware', versao)
    anotar('Portas ligadas', str(portas))
    anotar('Memória (resposta 03, antes)', memoria.hex(' ') if memoria else 'sem resposta')
    if nivel is not None and nivel <= NIVEL_FRACO:
        print('\nATENÇÃO: bateria fraca. Carregue o robô antes de testar: com bateria fraca os resultados enganam.')
    return nivel, bateria


def passo_bateria(bateria):
    titulo('1. Bateria')
    print(f'O robô disse que a bateria está em {bateria}.')
    r = perguntar('Isso combina com a bateria que aparece na tela do robô? (p se a tela não mostra)')
    anotar('1. Bateria (0C)', r, bateria)


def passo_botoes():
    titulo('2. Botões da controladora: qual número é cada botão')
    if not enviar('teste_botoes', lambda: _mostrar_botoes()):
        anotar('2. Botões (números)', 'p', 'não enviou')
        return {}
    print('Na tela do robô aparece "Botao:" e um número embaixo.')
    print('Aperte e SEGURE cada botão abaixo e digite o número que aparece.')
    print('Digite "x" se o robô não tem esse botão, ou "sai" se apertar o botão faz o programa parar.')
    numeros = {}
    for nome in ('cima', 'baixo', 'esquerda', 'direita', 'centro / ok'):
        v = 'p' if SEM_ROBO else input(f'  Botão {nome}: ').strip().lower()
        numeros[nome] = v
    solto = perguntar('Sem apertar nada, aparece 0?')
    validos = [v for v in numeros.values() if v.isdigit() and v != '0']
    ok = 's' if solto == 's' and validos and len(set(validos)) == len(validos) else ('p' if SEM_ROBO else 'n')
    anotar('2. Botões (números)', ok, ', '.join(f'{k}={v}' for k, v in numeros.items()) + f'; solto=0: {solto}')
    return numeros


def _mostrar_botoes():
    with robo.para_sempre():
        robo.mostrar('Botao:')
        robo.mostrar(robo.botao_apertado(), linha=2)
        robo.esperar(0.1)


def passo_esperar_botao():
    titulo('3. esperar_botao()')
    def escrever():
        robo.mostrar('Aperte e solte')
        robo.mostrar('um botao', linha=2)
        robo.esperar_botao()
        robo.bip()
        robo.mostrar('OK!')
        robo.esperar(2)
    if not enviar('teste_esperar_botao', escrever):
        return anotar('3. esperar_botao', 'p', 'não enviou')
    print('Aperte um botão (não o de sair), segure um pouco e solte.')
    anotar('3. esperar_botao', perguntar('O bip veio só DEPOIS de soltar, e apareceu "OK!"?'))


def passo_ao_mesmo_tempo():
    titulo('4. ao_mesmo_tempo(): andar e tocar juntos')
    if not SEM_ROBO:
        input('Ponha o robô no chão, com espaço na frente, e aperte Enter...')
    def escrever():
        robo.mostrar('Ao mesmo tempo')
        with robo.ao_mesmo_tempo():
            with robo.tarefa():
                robo.andar(segundos=2, potencia=30)
            with robo.tarefa():
                robo.melodia('do re mi fa sol', 0.3)
        robo.mostrar('Fim')
        robo.esperar(2)
    if not enviar('teste_ao_mesmo_tempo', escrever):
        return anotar('4. ao_mesmo_tempo', 'p', 'não enviou')
    anotar('4. ao_mesmo_tempo', perguntar('Andou e tocou AO MESMO TEMPO, e "Fim" apareceu depois dos dois?'))


def passo_ajustando(numeros):
    titulo('5. ajustando(): mudar um número com os botões')
    cima, baixo = numeros.get('cima', ''), numeros.get('baixo', '')
    if cima.isdigit() and baixo.isdigit() and cima != baixo:
        robo.BOTAO_CIMA, robo.BOTAO_BAIXO = int(cima), int(baixo)
    print(f'Usando botão de cima = {robo.BOTAO_CIMA} e de baixo = {robo.BOTAO_BAIXO}.')
    def escrever():
        robo.mostrar('Ajuste o kp:')
        with robo.ajustando('kp', 10, 1):
            with robo.para_sempre():                 # o programa lê o kp: a linha 2 deve acompanhar a 3
                robo.mostrar(robo.ler('kp'), linha=2)
                robo.esperar(0.3)
    if not enviar('teste_ajustando', escrever):
        return anotar('5. ajustando', 'p', 'não enviou')
    print('A linha 3 da tela mostra "kp:" e o número 10, e a linha 2 também 10.')
    print('Aperte o botão de cima algumas vezes e depois o de baixo.')
    r = perguntar('O número sobe com o de cima e desce com o de baixo, um por aperto, e a linha 2 acompanha?')
    anotar('5. ajustando', r, f'cima={robo.BOTAO_CIMA}, baixo={robo.BOTAO_BAIXO}')
    print('(Para parar esse programa, use o botão do robô; o próximo passo também o substitui.)')


def passo_toque():
    titulo('6. Sensor de toque (se o robô tiver)')
    porta = 'p' if SEM_ROBO else input('Em que porta está o sensor de toque? (1 a 4, ou p se não tem) ').strip().lower()
    if porta not in ('1', '2', '3', '4'):
        if not SEM_ROBO:
            return anotar('6. Sensor de toque', 'p', 'sem sensor de toque')
        porta = '4'
    def escrever():
        with robo.para_sempre():
            robo.mostrar('Toque:')
            robo.mostrar(robo.tocado(int(porta)), linha=2)
            robo.esperar(0.1)
    if not enviar('teste_toque', escrever):
        return anotar('6. Sensor de toque', 'p', 'não enviou')
    anotar('6. Sensor de toque', perguntar('Mostra 1 apertado e 0 solto?'), f'porta {porta}')


def passo_programas():
    titulo('7. Programas no robô: listar e apagar (automático)')
    if SEM_ROBO:
        programa(lambda: robo.bip())
        return anotar('7. Listar e apagar', 'p', 'sem robô')
    from est_protocol import apagar_arquivo, listar_arquivos, memoria_bruta
    alvo = '/vscode/teste_apagar.dbf'
    try:
        antes = listar_arquivos()
        print(f'O robô tem {len(antes)} arquivo(s). Da pasta vscode: '
              + ', '.join(n for n, _ in antes if n.startswith('/vscode/')))
        enviar('teste_apagar', lambda: robo.bip(), executar=False)
        memoria = memoria_bruta()           # comparada com a de antes, ajuda a decifrar a resposta 03
        anotar('Memória (resposta 03, com 1 programa a mais)', memoria.hex(' ') if memoria else 'sem resposta')
        depois = [n for n, _ in listar_arquivos()]
        apareceu = alvo in depois
        apagou = apagar_arquivo(alvo) if apareceu else False
        sumiu = alvo not in [n for n, _ in listar_arquivos()]
    except RuntimeError as e:
        return anotar('7. Listar e apagar', 'n', str(e))
    obs = f'listou {len(antes)}; programa de teste apareceu: {apareceu}; robô disse que apagou: {apagou}; sumiu da lista: {sumiu}'
    anotar('7. Listar e apagar', 's' if apareceu and apagou and sumiu else 'n', obs)


def passo_navegador():
    titulo('8. Enviar pelo navegador')
    print(f'Abra {PAGINA} no Chrome ou no Edge, espere aparecer "Python pronto"')
    print('e clique em "Enviar ao robô" (na primeira vez o navegador pergunta qual é o robô).')
    anotar('8. Envio pelo navegador', perguntar('O robô acendeu a luz, apitou e mostrou "Funcionou!"?'))


def gravar_relatorio(bateria):
    versao = open(os.path.join(RAIZ, 'VERSAO'), encoding='utf-8').read().strip()
    linhas = [f'Teste geral do EST-ROBOT {versao} em {datetime.datetime.now():%d/%m/%Y %H:%M}', f'Bateria: {bateria}', '']
    linhas += [f'{p}: {r}' + (f' | {o}' if o else '') for p, r, o in RESULTADOS]
    arquivo = os.path.join(RAIZ, 'resultado_teste_geral.txt')
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')
    titulo('Resumo')
    print('\n'.join(linhas))
    print(f'\nGravado em {os.path.normpath(arquivo)}: mande este arquivo (ou cole o resumo) para corrigir o que falhou.')


def main():
    if SEM_ROBO:
        print('Modo --sem-robo: só confere se os programas do teste compilam.')
        nivel, bateria = None, '(sem robô)'
    else:
        nivel, bateria = preparar()
    passo_bateria(bateria)
    numeros = passo_botoes()
    passo_esperar_botao()
    passo_ao_mesmo_tempo()
    passo_ajustando(numeros)
    passo_toque()
    passo_programas()
    passo_navegador()
    if not SEM_ROBO:
        gravar_relatorio(bateria)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nTeste interrompido.')
        if RESULTADOS and not SEM_ROBO:
            gravar_relatorio('?')
