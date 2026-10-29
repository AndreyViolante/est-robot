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
    campos = {'esquerda': 'BOTAO_ESQUERDA', 'centro / ok': 'BOTAO_CENTRO', 'direita': 'BOTAO_DIREITA',
              'cima': 'BOTAO_CIMA', 'baixo': 'BOTAO_BAIXO'}
    diferentes = [f'{campos[k]} = {v}' for k, v in numeros.items()
                  if v.isdigit() and int(v) != getattr(robo, campos[k])]
    if diferentes:
        print('\nOs números deste robô são outros: escreva no calibracao.py (o ajustando e o ajustes usam):')
        print('\n'.join('    ' + linha for linha in diferentes))
        anotar('Para o calibracao.py', '; '.join(diferentes))
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
    for nome, campo in (('cima', 'BOTAO_CIMA'), ('baixo', 'BOTAO_BAIXO'), ('esquerda', 'BOTAO_ESQUERDA'),
                        ('direita', 'BOTAO_DIREITA'), ('centro / ok', 'BOTAO_CENTRO')):
        if numeros.get(nome, '').isdigit():
            setattr(robo, campo, int(numeros[nome]))
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


def passo_ajustes():
    titulo('5b. ajustes(): vários números pelos botões')
    def escrever():
        robo.mostrar('Ajustes')
        with robo.ajustes(kp=(10, 1), vel=(20, 5)):
            with robo.para_sempre():
                robo.mostrar(robo.ler('vel'), linha=2)
                robo.esperar(0.3)
    if not enviar('teste_ajustes', escrever):
        return anotar('5b. ajustes', 'p', 'não enviou')
    print('A linha 3 mostra "kp: 10". O botão da direita troca para "vel: 20" (e a linha 2 mostra o vel).')
    print('Com "vel" escolhido, aperte cima e baixo; depois o da esquerda volta para o "kp".')
    anotar('5b. ajustes', perguntar('Direita/esquerda trocam o número, e cima/baixo mudam só o escolhido?'))


def passo_medir_laco():
    titulo('5c. medir_laco(): voltas por segundo do seguidor')
    if not SEM_ROBO:
        input('Ponha o robô no chão com espaço (ele anda devagar por 5 segundos) e aperte Enter...')
    def escrever():
        with robo.medir_laco(5):
            erro = robo.luz_refletida(1) - robo.luz_refletida(2)
            robo.motores(15 + erro * 0.1, 15 - erro * 0.1)
    if not enviar('teste_medir_laco', escrever):
        return anotar('5c. medir_laco', 'p', 'não enviou')
    v = 'p' if SEM_ROBO else input('Depois de 5 s ele para e mostra "Voltas/s:". Que número apareceu? (p se nada) ').strip()
    anotar('5c. medir_laco', 'p' if v in ('', 'p') else 's', f'voltas por segundo: {v}')


def passo_calibrar():
    titulo('5d. calibrar_na_largada(): medir o preto e o branco na pista')
    if not SEM_ROBO:
        input('Ponha o robô parado em cima de uma linha preta, com S1 de um lado e S2 do outro, e aperte Enter...')
    def escrever():
        robo.calibrar_na_largada(1, 2)
        robo.esperar(8)
    if not enviar('teste_calibrar', escrever):
        return anotar('5d. calibrar_na_largada', 'p', 'não enviou')
    print('O robô gira um pouco para um lado, para o outro, volta ao meio, apita e mostra lim1 e lim2.')
    v = 'p' if SEM_ROBO else input('Que números apareceram? (ex.: 55 60, ou p) ').strip()
    r = perguntar('Ele voltou mais ou menos ao meio, e os limites ficaram entre o preto e o branco do calibracao.py?')
    anotar('5d. calibrar_na_largada', r, f'limites na tela: {v}')


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


def passo_rodar_baixar_copiar():
    titulo('7b. Rodar, baixar e copiar um programa gravado')
    def escrever():
        robo.bip()
        robo.mostrar('Rodou!')
        robo.esperar(3)
    if SEM_ROBO:
        programa(escrever)
        return anotar('7b. Rodar, baixar e copiar', 'p', 'sem robô')
    from est_protocol import apagar_arquivo, baixar_arquivo, listar_arquivos, rodar_programa, upload
    alvo, copia = '/vscode/teste_rodar.dbf', '/vscode/teste_copia.dbf'
    dados = programa(escrever)
    if not enviar('teste_rodar', escrever, executar=False):
        return anotar('7b. Rodar programa gravado', 'p', 'não enviou')
    print('O programa foi gravado sem rodar. Agora o computador pede ao robô para rodar o que está gravado.')
    try:
        rodar_programa(alvo)
        anotar('7b. Rodar programa gravado', perguntar('O robô apitou e mostrou "Rodou!"?'))
        baixado = baixar_arquivo(alvo)
        igual = baixado == dados
        anotar('7c. Baixar programa', 's' if igual else 'n', f'{len(baixado)} bytes, igual ao enviado: {igual}')
        upload(baixado, prog_path=copia[:-4], verbose=False, executar=False)          # o que a cópia faz
        apareceu = copia in [n for n, _ in listar_arquivos()]
        anotar('7d. Copiar programa', 's' if apareceu else 'n', f'a cópia apareceu na lista: {apareceu}')
        for caminho in (alvo, copia):
            apagar_arquivo(caminho)
    except RuntimeError as e:
        anotar('7b. Rodar, baixar e copiar', 'n', str(e))


def passo_blocos_novos():
    titulo('9. Rotação do motor, cronômetro e giroscópio')
    esquerdo = robo._config['esquerdo']
    def escrever():
        robo.zerar_motor(esquerdo)
        robo.zerar_cronometro()
        with robo.para_sempre():
            robo.painel(graus=robo.graus_do_motor(esquerdo), tempo=robo.cronometro(),
                        sorteio=robo.aleatorio(1, 6))
            robo.esperar(0.2)
    if not enviar('teste_motor_tempo', escrever):
        return anotar('9. Rotação do motor e cronômetro', 'p', 'não enviou')
    print(f'Na tela: "graus" (motor {esquerdo}), "tempo" (segundos) e "sorteio" (1 a 6).')
    print(f'Levante o robô e gire a roda do motor {esquerdo} uma volta para frente, com a mão.')
    anotar('9. Rotação do motor', perguntar('O "graus" foi para perto de 360 (ou -360) com uma volta da roda?'))
    anotar('9. Cronômetro', perguntar('O "tempo" sobe um por segundo?'))
    anotar('9. Aleatório', perguntar('O "sorteio" muda entre 1 e 6?'))
    porta = 'p' if SEM_ROBO else input('Em que porta está o giroscópio? (1 a 4, ou p se não tem) ').strip().lower()
    if porta not in ('1', '2', '3', '4'):
        if not SEM_ROBO:
            return anotar('9. Giroscópio', 'p', 'sem giroscópio')
        porta = '2'
    def escrever_giro():
        robo.zerar_giroscopio(int(porta))
        with robo.para_sempre():
            robo.painel(giro=robo.giroscopio(int(porta)), vel=robo.velocidade_do_giro(int(porta)))
            robo.esperar(0.2)
    if not enviar('teste_giroscopio', escrever_giro):
        return anotar('9. Giroscópio', 'p', 'não enviou')
    print('Gire o robô um quarto de volta para a direita, com a mão, em cima da mesa.')
    anotar('9. Giroscópio', perguntar('O "giro" foi para perto de 90 (ou -90)?'), f'porta {porta}')


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
    passo_ajustes()
    passo_medir_laco()
    passo_calibrar()
    passo_toque()
    passo_programas()
    passo_rodar_baixar_copiar()
    passo_navegador()
    passo_blocos_novos()
    if not SEM_ROBO:
        gravar_relatorio(bateria)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nTeste interrompido.')
        if RESULTADOS and not SEM_ROBO:
            gravar_relatorio('?')
