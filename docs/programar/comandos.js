'use strict';
/* Os comandos que o autocompletar do editor de Python sugere: [nome, modelo, o que faz].
   O « » marca o que fica selecionado para o aluno trocar (como no teclado de programação). Um modelo que começa
   com "with " é um bloco: depois de um "with" já escrito, entra sem ele.
   São os nomes do robo.py (o verificar_gabaritos.py confere que todos existem e que nenhum ficou de fora), menos
   novo_programa e programa (do enviar.py), e ajustes e medir_laco (não funcionaram no robô). */
(function (raiz) {
  const ROBO = [
    // andar e virar
    ['andar', 'andar(rotacoes=«1»)', 'anda para frente'],
    ['re', 're(rotacoes=«1»)', 'anda de ré'],
    ['andar_cm', 'andar_cm(«20»)', 'anda em centímetros (negativo = ré)'],
    ['virar_direita', 'virar_direita(«90»)', 'vira tantos graus para a direita'],
    ['virar_esquerda', 'virar_esquerda(«90»)', 'vira tantos graus para a esquerda'],
    ['girar_direita', 'girar_direita(rotacoes=«1»)', 'gira no lugar, rodas em sentidos opostos'],
    ['girar_esquerda', 'girar_esquerda(rotacoes=«1»)', 'gira no lugar, rodas em sentidos opostos'],
    ['mover', 'mover(«50», 20, rotacoes=1)', 'cada roda com uma potência'],
    ['motores', 'motores(«30», 30)', 'liga os dois motores e deixa ligados'],
    ['parar', 'parar()', 'desliga os dois motores'],
    ['motor', "motor('«A»', 50, graus=180)", 'gira um motor sozinho'],
    ['ligar_motor', "ligar_motor('«A»', 50)", 'liga um motor e deixa ligado'],
    ['desligar_motor', "desligar_motor('«A»')", 'desliga um motor'],
    ['configurar', 'configurar(roda_cm=«5.6»)', 'ajusta o robô só neste programa'],
    ['esperar', 'esperar(«1»)', 'espera alguns segundos'],
    // sensores
    ['luz_refletida', 'luz_refletida(«1»)', 'luz do sensor: 0 escuro, 100 claro'],
    ['cor_vista', 'cor_vista(«1»)', 'a cor que o sensor vê'],
    ['distancia', 'distancia(«4»)', 'distância em cm (ultrassônico)'],
    ['tocado', 'tocado(«1»)', 'sensor de toque: 1 apertado, 0 solto'],
    ['limite', 'limite(«1»)', 'o meio entre o preto e o branco'],
    ['calibrar_na_largada', 'calibrar_na_largada(«1»)', 'mede o preto e o branco na pista'],
    ['limite_medido', 'limite_medido(«1»)', 'o limite que a calibração mediu'],
    ['media', 'media(«luz_refletida(1)»)', 'média de várias leituras do sensor'],
    ['confirmado', 'confirmado(lambda: «luz_refletida(1) < 30»)', 'verdadeiro em várias leituras seguidas'],
    ['giroscopio', 'giroscopio(«1»)', 'ângulo do robô em graus'],
    ['velocidade_do_giro', 'velocidade_do_giro(«1»)', 'graus por segundo que o robô gira'],
    ['zerar_giroscopio', 'zerar_giroscopio(«1»)', 'volta o ângulo para 0'],
    ['graus_do_motor', "graus_do_motor('«B»')", 'quantos graus o motor girou'],
    ['rotacoes_do_motor', "rotacoes_do_motor('«B»')", 'quantas voltas o motor deu'],
    ['potencia_do_motor', "potencia_do_motor('«B»')", 'a potência do motor agora'],
    ['zerar_motor', "zerar_motor('«B»')", 'volta a contagem do motor para 0'],
    ['botao_apertado', 'botao_apertado()', 'o botão da controladora apertado (0 = nenhum)'],
    ['cronometro', 'cronometro()', 'segundos desde o começo'],
    ['zerar_cronometro', 'zerar_cronometro()', 'o cronômetro volta para 0'],
    // esperar até
    ['esperar_toque', 'esperar_toque(«1»)', 'espera apertar o sensor de toque'],
    ['esperar_distancia', "esperar_distancia(«4», '<', 20)", 'espera a distância passar de um valor'],
    ['esperar_luz', "esperar_luz(«1», '<', 30)", 'espera a luz passar de um valor'],
    ['esperar_cor', 'esperar_cor(«1», VERDE)', 'espera o sensor ver a cor'],
    ['esperar_botao', 'esperar_botao()', 'espera apertar um botão da controladora'],
    // tela, som e luz
    ['mostrar', "mostrar(«'Oi'»)", 'escreve na tela do robô'],
    ['painel', 'painel(«luz=luz_refletida(1)»)', 'até 3 valores na tela, com o nome'],
    ['tocar', 'tocar(«440», 0.5)', 'toca um som (frequência, segundos)'],
    ['melodia', "melodia(«'do re mi'»)", 'toca notas separadas por espaço'],
    ['bip', 'bip()', 'um bip curto'],
    ['luz', "luz('«azul»')", "acende a luz: 'azul', 'roxo' ou 'vermelho'"],
    ['apagar_luz', 'apagar_luz()', 'apaga a luz do robô'],
    // variáveis, contas e mensagens
    ['guardar', "guardar('«x»', 0)", 'guarda um número numa variável do robô'],
    ['ler', "ler('«x»')", 'lê uma variável do robô'],
    ['ajustando', "ajustando('«kp»', 1, 0.1)", 'um número que se ajusta com os botões'],
    ['aleatorio', 'aleatorio(«1», 10)', 'um número sorteado'],
    ['arredondar', 'arredondar(«x»)', 'arredonda para o inteiro mais perto'],
    ['enviar_mensagem', "enviar_mensagem('«titulo»', 1)", 'manda uma mensagem pelo Bluetooth'],
    ['mensagem_recebida', "mensagem_recebida('«titulo»')", 'o último número que chegou com o título'],
    ['ligar_bluetooth', 'ligar_bluetooth()', 'liga o Bluetooth do robô'],
    ['desligar_bluetooth', 'desligar_bluetooth()', 'desliga o Bluetooth do robô'],
    // blocos "with"
    ['para_sempre', 'with para_sempre():\n    «»', 'repete para sempre'],
    ['repetir', 'with repetir(«4»):\n    ', 'repete um número de vezes'],
    ['repetir_ate', 'with repetir_ate(lambda: «distancia(4) < 20»):\n    ', 'repete até a condição acontecer'],
    ['repetir_ate_luz', "with repetir_ate_luz(«1», '<', 30):\n    ", 'repete até a luz passar de um valor'],
    ['repetir_ate_cor', 'with repetir_ate_cor(«1», VERDE):\n    ', 'repete até o sensor ver a cor'],
    ['se', 'with se(«distancia(4) < 20»):\n    ', 'faz se a comparação for verdadeira'],
    ['se_ver_cor', 'with se_ver_cor(«1», VERDE):\n    ', 'faz se o sensor ver a cor'],
    ['se_tocado', 'with se_tocado(«1»):\n    ', 'faz se o toque estiver apertado'],
    ['se_distancia', "with se_distancia(«4», '<', 20):\n    ", 'faz se a distância passar de um valor'],
    ['se_luz', "with se_luz(«1», '<', 30):\n    ", 'faz se a luz passar de um valor'],
    ['senao', 'with senao():\n    «»', 'o contrário do "with se" de cima'],
    ['ao_mesmo_tempo', "with ao_mesmo_tempo():\n    with tarefa():\n        «andar_cm(20)»\n    with tarefa():\n        tocar(440, 1)",
     'partes do programa ao mesmo tempo'],
    ['tarefa', 'with tarefa():\n    «»', 'uma parte do "ao_mesmo_tempo"'],
  ];
  const NOMES = [
    ['PRETO', 'cor'], ['AZUL', 'cor'], ['VERDE', 'cor'], ['AMARELO', 'cor'], ['VERMELHO', 'cor'], ['BRANCO', 'cor'],
    ['MARROM', 'cor'], ['BOTAO_CIMA', 'botão'], ['BOTAO_BAIXO', 'botão'], ['BOTAO_ESQUERDA', 'botão'],
    ['BOTAO_DIREITA', 'botão'], ['BOTAO_CENTRO', 'botão'],
  ].map(([nome, texto]) => [nome, nome, texto]);
  const PYTHON = [
    ['if', 'if «luz_refletida(1) < 50»:\n    ', 'se a comparação for verdadeira'],
    ['elif', 'elif «luz_refletida(1) < 50»:\n    ', 'senão, se'],
    ['else', 'else:\n    «»', 'senão'],
    ['while', 'while «True»:\n    ', 'repete enquanto for verdadeiro'],
    ['for', 'for _ in range(«4»):\n    ', 'repete um número de vezes'],
    ['def', 'def «nome»():\n    ', 'um bloco seu, com nome'],
    ['from', 'from robo import *', 'a primeira linha do programa'],
    ['abs', 'abs(«x»)', 'o número sem o sinal'],
    ['min', 'min(«a», b)', 'o menor'],
    ['max', 'max(«a», b)', 'o maior'],
  ];
  raiz.ESTComandos = {ROBO, NOMES, PYTHON, TODOS: [...ROBO, ...NOMES, ...PYTHON]};
})(typeof window !== 'undefined' ? window : globalThis);
