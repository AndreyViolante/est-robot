# Novidades

Cada versão publicada fica em [Releases](https://github.com/AndreyViolante/est-robot/releases).
O "Atualizar o projeto" mostra daqui o que mudou desde a versão que você tem.

## 0.1.16 (24/11/2026)

- **Correção no autocompletar:** o Enter no fim de uma linha como `erro_anterior = erro` trocava `erro` por
  `erro_anterior` (e uma variável `luz` por `luz_refletida`). Agora, quando a palavra já é um nome do programa ou
  uma palavra do Python, a lista não abre sozinha e o Enter só pula a linha. Quem usou a 0.1.15 deve conferir as
  linhas que terminam com o nome de uma variável.
- O Enter apertado logo depois da última letra não se perde mais.

## 0.1.15 (24/11/2026)

- **Autocompletar no editor de Python** da página de programar: a partir da segunda letra aparecem os comandos
  do robô que combinam, com o que cada um faz (escrever `vir` mostra `virar_direita(90)` e `virar_esquerda(90)`).
  Enter ou Tab escolhe, e o número fica selecionado para trocar; os blocos `with` e o `if`, `while`, `for` e `def`
  já vêm com a linha de baixo recuada. Também sugere as variáveis e os blocos do próprio programa.
  **Ctrl+Espaço** abre a lista quando quiser; Esc fecha.
- **Bateria do robô na página de programar.** Com o robô no USB, a Conexão mostra a bateria de 0 a 4, como os
  tracinhos da IDE, lida ao abrir a página, ao ligar o robô e a cada envio. Com 0 ou 1, a linha fica laranja e
  o envio avisa para carregar o robô (bateria fraca deixa os motores fracos e os sensores lendo errado). Pelo
  Bluetooth, o nível aparece depois do envio.

## 0.1.14 (23/11/2026)

- O simulador não tem mais o modo **Dirigir** (andar com o robô pelas setas e o programa se escrever): a barra de
  cima ficou só com Executar, Reiniciar, Próxima linha, Velocidade e Opções.

## 0.1.13 (23/11/2026)

- **Gravar vídeo** no simulador, na barra embaixo da pista: grava a pista enquanto o robô anda e, ao apertar de
  novo, baixa o vídeo (mp4 no Chrome e no Edge, que abre no WhatsApp). Para sozinho em 3 minutos.

## 0.1.12 (23/11/2026)

- **Simulador com menos texto.** A dica da pista fica recolhida em **Dica** (abre sozinha enquanto você desenha
  a Minha pista), as notas do painel ficaram de uma linha só e, no rodapé, atalhos e avisos ficam recolhidos.
- **Esconder o painel**, no cartão do robô, tira a coluna da direita (tela do robô, programa e sensores): a pista
  ocupa a largura toda. **Mostrar o painel**, na barra de cima, traz de volta. A escolha fica guardada no navegador.

## 0.1.11 (23/11/2026)

- **Página de programar mais organizada.** Uma barra só no editor: as abas Python e Blocos, o nome, o menu
  **Arquivo** (exemplos, abrir, baixar, salvar para a IDE EST, versões do programa, link e progresso), o menu
  **Exibir** (tela cheia e modo projetor) e, à direita, **Simular** e **Enviar ao robô**. Nos blocos, os botões
  agora dizem o que fazem: **Trazer da aba Python** e **Copiar para a aba Python**.
- **Simulador mais organizado.** Em cima, o que se usa o tempo todo: Executar, Reiniciar, Próxima linha,
  Velocidade, Dirigir e o menu **Opções** (som, sensores com ruído, modo projetor, progresso e, para o
  professor, liberar ou zerar os desafios). **Pista ou desafio** virou um campo só, com as pistas para treinar,
  as arenas da OBR, as pistas feitas por você e os desafios. Embaixo da pista ficam **Seguir o robô** (era a
  "Lupa"), o rastro e o que o robô está fazendo; as ferramentas de desenhar ou montar a pista só aparecem nela.
- Aberto pela página de programar, o simulador não repete o topo: a barra diz o programa e o tamanho.
- Fotos do site novas, com a tela de agora.

## 0.1.10 (23/11/2026)

- **Tela cheia na página de programar.** O botão **Tela cheia**, na barra do editor, faz o Python ou os blocos
  ocuparem a tela inteira, sem o topo e sem o painel da direita. Os erros e o resultado do envio aparecem num
  canto, por cima, e somem no **Fechar**. A escolha fica guardada no navegador; para sair, o mesmo botão ou Esc.
  No celular, os blocos ocupam a tela e o Python deles fica no **Ver**.

## 0.1.9 (23/11/2026)

- **Robô do simulador com dois sensores de cor.** Por padrão, S1 e S2 de cor, a porta 3 vazia e o ultrassom na
  porta 4. Em **Medidas do robô**, a porta 3 pode virar giroscópio ou um terceiro sensor de cor. Pelo VS Code,
  as portas com preto no `calibracao.py` viram sensores de cor.
- **15 desafios e o desafio surpresa.** Entraram dois desafios de giroscópio: o quadrado, com um robô que
  derrapa nas viradas, e o triângulo, com um giroscópio que desvia sozinho. Depois do percurso da OBR vem a
  **surpresa**: uma arena sorteada e uma tarefa a mais. Com **Sensores com ruído**, o giroscópio também desvia um
  pouco. A **arena da OBR sorteada** tem um número, para a turma toda correr na mesma.
- **Linguagem:** `break` e `continue` com sensor, `a if c else b`, `abs`, `min`, `max` e `round` com leituras.
  `media(leitura, 5)` e `confirmado(lambda: ..., 3)` deixam as leituras mais confiáveis (ainda não conferidos
  no robô).
- **Blocos:** as funções viram **Meus blocos**, e entraram blocos para sair do repetir, valor absoluto,
  menor e maior, se/senão, média, confirmado, motores sozinhos, esperas e os de competição.
- **Link do programa** (menu **Arquivo**): leva também o desafio aberto no simulador e abre nos blocos se o
  programa foi feito em blocos. No cartão do desafio há o botão **Copiar link do programa**.
- **Salvar e carregar o progresso** num arquivo, no simulador e na página de programar: os desafios cumpridos,
  o programa e as versões passam de um computador para outro.
- **Imprimir a arena da OBR** em tamanho real: cada ladrilho em 4 folhas A4.
- **Modo projetor** nas duas páginas: letras, controles e blocos maiores para a turma ver de longe.
- A página de programar confere a resposta do robô a cada pacote e diz qual ficou sem resposta.
- O simulador usa as medidas do `calibracao.py` quando o programa vem do VS Code.
- Programa grande demais (mais de 255 partes de repetição e de decisão) dá uma mensagem em português dizendo
  como fazer caber.
- A página do projeto tem uma versão em inglês.

## 0.1.8 (17/11/2026)

- **Botões da controladora funcionando.** O `botao_apertado()` ficava sempre no zero porque lia os botões pela
  tabela antiga da IDE. Agora lê como a IDE de verdade, e os números foram conferidos no robô: esquerda 1, OK 2,
  direita 3, cima 4 e baixo 5. Com isso funcionam também o `esperar_botao()` e o `ajustando(...)`.
- **13 desafios no simulador.** Entrou "Cruzamentos sem verde", um passo antes do verde, e quatro desafios mais
  difíceis no fim da trilha: volta rápida no oval, chegada na faixa vermelha, beco sem saída e o percurso
  completo da OBR. Quem já tinha cumprido um desafio continua com ele liberado.
- **Tutorial para IAs** (`docs/tutorial-para-ia.md`): anexe numa conversa com o ChatGPT, o Claude ou o Gemini e a
  IA passa a escrever programas do EST-LAB sem inventar comandos.
- **Teste geral no robô mais fácil de responder.** Só aceita respostas que fazem sentido, `r` refaz o passo
  (manda o programa de novo) e a tarefa **Teste geral: refazer um passo** roda só o passo que você escolher.
- Quando o Windows mostra um "Dispositivo USB Desconhecido" no lugar do robô, o envio explica o que fazer
  (tirar o cabo, ligar o robô e pôr o cabo de novo).
- Mensagens em português para `int()`, `round()` e texto + leitura de sensor, que antes davam erro em inglês.
- O README mostra o que já foi conferido no robô (teste de 13/11/2026). O `ajustes(...)` e o `medir_laco(...)`
  falharam no robô e estão em investigação: por enquanto, use um `ajustando(...)`.

## 0.1.7 (12/11/2026)

- **Pacote para Windows mais simples.** A pasta extraída mostra só o que o aluno usa: `Abrir o EST-LAB`,
  `LEIA-ME.txt`, `meu_programa.py`, `calibracao.py` e `exemplos`. Dois cliques em **Abrir o EST-LAB** abrem o
  VS Code já com o primeiro programa. O resto do projeto e o Python ficam na pasta `sistema`, que o VS Code
  esconde. O botão de download do site baixa direto o arquivo certo. Quem já tem o projeto atualiza como
  sempre, e a pasta continua como estava.
- **Avisos antes de enviar**, com a linha e como arrumar: variável criada e nunca usada, `while True` que
  repete sem esperar nem ler sensor, e motor que fica ligado quando o programa termina. Não impedem o envio.
- Depois de compilar, aparece **quanto do espaço do robô** o programa usa.
- **Salvar para a IDE EST (.est)**, o caminho de volta do "Abrir programa da IDE": o arquivo abre na IDE com
  os mesmos blocos e dá os mesmos bytes. Na página de programar, fica no menu **Arquivo**.
- Simulador: a aba **Sensores** tem o gráfico da leitura de cada sensor enquanto o robô anda, e a coluna da
  direita virou abas (Programa, Sensores, Variáveis, Medidas).
- Página de programar: **Versões** guarda as últimas 30 versões do programa no navegador e deixa voltar para
  qualquer uma. Simular e Enviar ficam na barra do editor, e o que é de arquivo fica no menu **Arquivo**.
- A página do projeto mostra fotos de tela da ferramenta e o passo a passo para começar pelo navegador ou
  pelo VS Code.

## 0.1.6 (04/11/2026)

- Na aba **Blocos** da página de programar, o botão **Trazer do Python** faz o caminho de volta: o programa
  escrito na aba Python vira blocos. O que ainda não tem bloco vira um bloco cinza "Python", com a linha como
  está, e o programa continua fazendo o mesmo.
- Blocos novos para montar: decidir pelo sensor (se o sensor vê a cor, a luz, a distância ou o toque, com o
  "senão"), variáveis do Python e uma linha ou um valor em Python.

## 0.1.5 (03/11/2026)

- O projeto agora se chama **EST-LAB** (antes EST-ROBOT). O endereço, o pacote e os seus arquivos continuam
  os mesmos.
- **Celular e tablet Android:** a página de programar pode ir para a tela inicial (botão 📲 Instalar) e
  funciona sem internet. No aparelho ela começa nos blocos; na aba Python, uma barra acima do teclado tem os
  símbolos difíceis de achar e os comandos mais usados. O envio por Bluetooth pelo Chrome do Android está
  pronto, mas ainda não foi conferido no robô: a tarefa "Testar o Bluetooth do robô" confere pelo computador,
  só fazendo perguntas ao robô.
- Simulador: **🎮 Dirigir**, em que o aluno leva o robô pelas setas e o programa se escreve sozinho
  (`andar_cm`, `virar_direita`), e zoom com dois dedos ou com os botões + e −.
- **Arena da OBR** no simulador: percurso com linha em ladrilhos de 30 cm, como no manual 2026, com a
  pontuação da rodada. E o guia da OBR (`docs/guia-obr.md`): como organizar, testar e ajustar o programa.
- Para a competição: `calibrar_na_largada(1, 2)` mede o preto e o branco na própria pista,
  `with ajustes(kp=(0.4, 0.05)):` muda números pelos botões do robô, sem cabo, e `with medir_laco(5):` mostra
  quantas voltas por segundo o laço faz. Os números dos botões ficam no `calibracao.py`.
- **Abrir programa da IDE (.est):** o projeto feito na IDE EST vira Python, com os Meus Blocos como funções,
  e a página diz se a tradução é exata (os mesmos bytes que a IDE manda).
- Programas no robô: rodar um programa já gravado, baixar para a pasta `do_robo` (o simulador abre o
  arquivo baixado) e copiar para os outros robôs da turma.
- O envio avisa quando o sensor ligado na porta é de outro tipo que o do programa (sensores trocados).
- Comandos novos, que seguem a tabela da IDE mas ainda não foram vistos no robô: `graus_do_motor`,
  `giroscopio`, `cronometro` (e os `zerar_...`), `aleatorio`, `arredondar` e as mensagens pelo Bluetooth
  `enviar_mensagem` e `mensagem_recebida`.
- Página de programar: **Compartilhar link** (o programa vai dentro do próprio link) e modo sem internet.
- A tarefa "Teste geral no robô" confere também rodar, baixar e copiar programas, a rotação do motor, o
  cronômetro e o giroscópio.

## 0.1.4 (27/10/2026)

- Registro no Zenodo: cada versão publicada ganha um DOI permanente, para citar o EST-ROBOT em
  trabalhos acadêmicos, artigos e relatos de aula.

## 0.1.3 (27/10/2026)

- Atalhos no VS Code: digite `para_sempre`, `seguidor_2_sensores`, `desviar`, `mostrar_sensor`... e
  aperte Tab. O modelo aparece pronto para trocar os números (a lista está na cola de comandos).
- Enquanto você escreve, o VS Code mostra as opções de cada comando: as portas, as comparações
  (`'<'`, `'>'`...) e as cores da luz.
- Mais erros explicados em português: `=` no lugar de `==`, `else` sem `if`, texto + número, vírgula no
  número, `from robot import *`... Porta de sensor fora de 1 a 4 ou de motor fora de A a D agora avisa.
- Cola de comandos em PDF, frente e verso, para imprimir: `docs/cola-do-aluno.pdf`.
- Tarefa "Teste geral no robô": confere um por um os comandos ainda não vistos funcionando no robô e
  grava o resultado em `resultado_teste_geral.txt`.
- Tarefa "Diagnóstico (para pedir ajuda)": copia um resumo do computador e do robô para colar no
  WhatsApp, sem dados pessoais.
- No pacote com o Python dentro, o VS Code já usa esse Python (sem pedir *Select Interpreter*).
- A página de cada versão mostra o código SHA-256 do pacote, para conferir o download.

## 0.1.2 (23/10/2026)

- O pacote traz só os dois programas de exemplo: o `meu_programa.py` (luz, som e "Funcionou!") e o
  seguidor de linha básico com dois sensores.
- O `formato.md` documenta a consulta de bateria e os comandos de listar e apagar arquivos do robô.

## 0.1.1 (22/10/2026)

- "Atualizar o projeto" pega a última versão publicada, que já passou pelos testes, e mostra as novidades.
- O `calibracao.py` só ganha os campos novos de cada versão; as suas medidas ficam como estão.
- Tarefa "Voltar para a versão anterior", para desfazer uma atualização.
- O envio avisa quando sai uma versão nova (no máximo uma vez por dia).
- Correção: a tarefa "Testar conexão com o robô" voltou a funcionar.

## 0.1.0 (22/10/2026)

- Primeira versão beta: programar a controladora EST em Python pelo VS Code, sem a IDE do fabricante.
- `if`, `elif`, `else`, `while`, `and`, `or`, `not` e `for` do Python funcionam com os sensores.
- `calibracao.py` com as medidas do robô; `limite(porta)` dá o meio entre o preto e o branco.
- Notas pelo nome (`tocar('la')`, `melodia(...)`) e `painel(...)` na tela do robô.
- Antes de enviar: aviso de IDE EST aberta e de porta sem nada ligado.
- Simulador com pistas de prova, passo a passo e trilha de 8 desafios.
- Programar no navegador, em Python ou com blocos, sem instalar nada.
- Pacote para Windows com o Python dentro e tarefa "Atualizar o projeto".
- Ainda não testados no robô: `ao_mesmo_tempo`, botões da controladora, `ajustando`, envio pelo
  navegador e as tarefas "Programas no robô" e "Bateria do robô".
