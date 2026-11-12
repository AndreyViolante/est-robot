# Novidades

Cada versão publicada fica em [Releases](https://github.com/AndreyViolante/est-robot/releases).
O "Atualizar o projeto" mostra daqui o que mudou desde a versão que você tem.

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
