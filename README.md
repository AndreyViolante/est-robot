# est-robot

Programe o robô educacional **Dr. Luck EST** em Python, direto do **VS Code**, sem a IDE
proprietária. Pensado para aulas de robótica: os comandos são em português.

**Tem uma controladora EST?** Ajude a testar: [andreyviolante.github.io/est-robot](https://andreyviolante.github.io/est-robot/)

**Quer ver antes de instalar?** O exemplo roda no simulador, no navegador:
[andreyviolante.github.io/est-robot/simulador](https://andreyviolante.github.io/est-robot/simulador/)

**Sem instalar nada:** abra [andreyviolante.github.io/est-robot/programar](https://andreyviolante.github.io/est-robot/programar/)
no Chrome ou no Edge (Windows, Mac, Linux ou Chromebook). Dá para escrever em Python ou montar o
programa com blocos, vendo ao lado o Python que os blocos geram. A página compila no próprio
navegador, com os mesmos arquivos do projeto, mostra os erros em português, simula o robô, confere as
portas e envia o programa pelo cabo USB (o envio pelo navegador ainda não foi testado no robô). No
celular dá para programar e simular. O mesmo arquivo `.py` funciona no VS Code.

```python
from robo import *

with repetir(4):            # desenha um quadrado
    andar_cm(30)
    virar_direita(90)
```

```python
from robo import *

with para_sempre():         # seguidor de linha proporcional com dois sensores
    erro = luz_refletida(1) - luz_refletida(2)
    correcao = erro * 0.4
    motores(25 + correcao, 25 - correcao)
```

O projeto tem um compilador próprio, que transforma o programa no bytecode que o robô executa, e
um cliente USB que grava e executa o programa no robô. O compilador foi construído por engenharia
reversa e é testado comparando, byte a byte, a saída dele com programas compilados pela IDE oficial.

## Para professores

| | |
|---|---|
| [INSTALAR.md](INSTALAR.md) | instalação passo a passo (Python, VS Code, `instalar.bat`, teste do robô) |
| [docs/guia-do-professor.md](docs/guia-do-professor.md) | roteiro de 8 aulas, com objetivos, desafios e erros comuns |
| [docs/cola-do-aluno.md](docs/cola-do-aluno.md) | uma página com todos os comandos, para imprimir |

## Uso

Funciona no **Windows**, com Python 3.10+ ou com o pacote que já traz o Python, e VS Code (veja o
[INSTALAR.md](INSTALAR.md)).

**Computador da escola que não deixa instalar programas?** Use o pacote para Windows com o Python
dentro: baixe o `est-robot-windows.zip` em [Releases](https://github.com/AndreyViolante/est-robot/releases/latest),
clique com o botão direito → **Extrair Tudo** e abra a pasta no VS Code. Não instala o Python e não
precisa de administrador nem de internet: as tarefas do VS Code usam sozinhas o Python da pasta
`python`. Para receber as novidades, use **Terminal → Executar Tarefa… → Atualizar o projeto**: ela
baixa a versão nova do GitHub e não mexe no `calibracao.py`, no `meu_programa.py` nem nos programas
dos alunos.

1. Abra esta pasta no VS Code.
2. Abra o [meu_programa.py](meu_programa.py) e aperte **`Ctrl+Shift+B`**: se o robô acender a luz,
   apitar e escrever "Funcionou!", o computador está conversando com a controladora.
3. Apague as linhas do teste e escreva o seu programa embaixo do `from robo import *` (ou crie outro
   arquivo `.py` começando com essa linha). **`Ctrl+Shift+B`** compila, grava e já executa no robô.

> **Atenção:** o robô começa a se mexer logo depois do envio. Deixe-o no chão ou segure-o.

Se o programa tiver um erro, nada é enviado e aparece uma explicação em português com a linha:

```
ERRO na linha 3 de quadrado.py:
    andr(rotacoes=2)
  não conheço "andr". Você quis dizer "andar"?
```

Para conferir se o computador fala com o robô: **Terminal → Executar Tarefa → Testar conexão com o
robô** (ele apita, acende a luz e escreve "Funcionou!").

Para gravar sem o robô sair andando (por exemplo, numa prova, em que ele precisa estar na posição
de largada): **Terminal → Executar Tarefa → Gravar no robô sem executar**. O programa fica na pasta
**vscode** do robô e é iniciado pelo menu dele.

Pelo terminal:

```bash
python enviar.py meu_programa.py
python enviar.py meu_programa.py --so-gravar
```

### Programas gravados no robô e bateria

Cada envio grava o programa na pasta **vscode** do robô, e ela vai enchendo. Para ver e apagar:
**Terminal → Executar Tarefa → Programas no robô**. Aparecem a bateria e a lista de programas; para
apagar um, digite o número dele e confirme com `s`. Arquivos de outras pastas (gravados pela IDE EST)
só são apagados se você digitar o caminho completo, como aparece na lista. Apagar não tem volta.

**Terminal → Executar Tarefa → Bateria do robô** mostra só a bateria, de 0 a 4 tracinhos, como na IDE.
Com 0 ou 1 tracinho, carregue o robô: bateria fraca deixa os motores fracos e os sensores lendo errado,
e o programa parece estar com defeito sem estar. Pelo terminal: `python ferramentas/programas_no_robo.py`
(também aceita `--listar`, `--bateria` e `--apagar nome`), com a IDE EST fechada.

Os comandos de listar, apagar e ler a bateria são os mesmos que a IDE manda, mas **ainda não foram
testados no robô**.

### Simulador (sem o robô)

**Terminal → Executar Tarefa → Simular no computador** abre o programa no navegador, numa pista
vista de cima. O simulador executa os mesmos bytes que iriam para o robô: dá para ver o caminho
(rastro), a linha do programa que está rodando, os sensores, os motores, as variáveis, a tela, a luz
e o som. Funciona sem internet e sem instalar nada. O exemplo do projeto está na
[demonstração online](https://andreyviolante.github.io/est-robot/simulador/).

- Pistas: chão quadriculado, oval, quadrado com cantos de 90°, curvas de 90° com uma falha na
  linha, e uma arena com uma caixa.
- Arraste o robô para escolher a largada; a bolinha azul na frente gira o robô. A caixa da arena
  também pode ser arrastada.
- Em **Medidas do robô** ficam a roda, a distância entre as rodas e a posição de cada sensor. O padrão
  é o robô do laboratório (S1 e S2 um de cada lado da linha, S3 no meio e mais à frente, ultrassom na
  porta 4); meça o seu e ajuste.

```bash
python simular.py meu_programa.py
```

O simulador também tem pistas de prova: cruzamentos com quadrado verde (na cor o verde dá 3; na luz
refletida fica perto do preto) e um seguidor com uma caixa em cima da linha. A caixa "Sensores com
ruído" faz a luz variar como num sensor de verdade. Em "Minha pista" dá para desenhar a sua pista com
linhas, quadrados verdes e caixas (fica guardada no navegador). O botão "Próxima linha" executa o
programa linha por linha, e clicar no número de uma linha põe um ponto de parada. A trilha de desafios
traz 8 desafios, do "andar 30 cm" ao "desviar do obstáculo", com verificação automática; cada um
cumprido destrava o próximo. Os botões da controladora aparecem na tela do robô simulado quando o
programa usa `botao_apertado()`.

O robô de verdade escorrega, a bateria muda a velocidade e a luz da sala muda os sensores: o
simulador serve para testar a lógica, mas confira no robô.

## Comandos

| Movimento | |
|---|---|
| `andar(rotacoes=2)`, `andar(segundos=1)`, `andar(graus=360)` | anda para frente (`potencia=50` por padrão) |
| `re(rotacoes=1)` | anda de ré |
| `andar_cm(20)` | anda 20 cm |
| `virar_direita(90)`, `virar_esquerda(90)` | vira o robô no lugar, em graus |
| `girar_direita(rotacoes=0.5)`, `girar_esquerda(...)` | gira as rodas em sentidos opostos |
| `motores(esq, dir)` | liga os dois motores e deixa ligados (aceita valores de sensor) |
| `parar()` | desliga os motores |
| `motor('A', 50, graus=180)`, `ligar_motor('A', 50)`, `desligar_motor('A')` | um motor sozinho (garra, braço) |

| Sensores (dão valores que entram em contas: `+ - * /`) | |
|---|---|
| `luz_refletida(porta)` | luz refletida, de 0 (escuro) a 100 (claro) |
| `cor_vista(porta)` | número da cor (`PRETO`, `AZUL`, `VERDE`, `AMARELO`, `VERMELHO`, `BRANCO`, `MARROM`) |
| `distancia(porta)` | sensor ultrassônico, em centímetros |
| `tocado(porta)` | sensor de toque: 1 apertado, 0 solto |

| Esperar | |
|---|---|
| `esperar(1.5)` | segundos |
| `esperar_toque(porta)` | até apertar o sensor de toque |
| `esperar_distancia(porta, '<', 20)` | até a distância passar do valor |
| `esperar_luz(porta, '<', 30)`, `esperar_cor(porta, VERDE)` | até o sensor de cor ver |

| Repetir e decidir | |
|---|---|
| `if luz_refletida(1) < 50:` / `elif ...:` / `else:` | decide pelo sensor, com o `if` normal do Python (vale `and`, `or` e `not`) |
| `while distancia(4) > 15:` / `while True:` | repete enquanto a condição valer / para sempre |
| `for _ in range(4):` | repete 4 vezes (vira o "repetir" do robô) |
| `with para_sempre():` / `with repetir(4):` | repete o que está dentro |
| `with repetir_ate(lambda: distancia(4) < 20):` | repete até a condição acontecer |
| `with repetir_ate_luz(1, '<', 30):`, `with repetir_ate_cor(1, PRETO):` | repete até o sensor de cor ver |
| `with se(distancia(4) < 20):` | faz se a comparação for verdadeira |
| `with se_ver_cor(1, PRETO):`, `with se_luz(1, '<', 30):` | decide pelo sensor de cor |
| `with se_tocado(4):`, `with se_distancia(4, '<', 20):` | decide pelo toque / ultrassom |
| `with senao():` | logo depois de um `with se...`: o que fazer no caso contrário |

| Tela, som, luz e variáveis | |
|---|---|
| `mostrar('Oi')`, `mostrar(distancia(4), linha=2)` | escreve texto ou valor na tela (3 linhas; a linha 1 apaga a tela) |
| `tocar(440, 0.5)`, `tocar('la', 0.5)`, `bip()` | som pela frequência em Hz ou pelo nome da nota, com a duração em segundos |
| `melodia('do re mi fa sol:0.6')` | várias notas seguidas (`:segundos` muda a duração de uma nota, `-` é pausa) |
| `luz('azul')`, `apagar_luz()` | luz do robô: `'azul'`, `'roxo'` ou `'vermelho'` |
| `guardar('contador', 0)`, `ler('contador')` | variáveis guardadas no robô |
| `painel(erro=..., vel=...)` | mostra até 3 valores na tela, um por linha, com o nome na frente (para ver o PID andando) |

| Ainda não testados no robô (funcionam no simulador) | |
|---|---|
| `with ao_mesmo_tempo():` com um `with tarefa():` para cada parte | faz várias coisas ao mesmo tempo (ex.: andar e tocar uma música) e continua quando todas acabam |
| `esperar_botao()`, `botao_apertado()` | os botões da própria controladora: esperar apertar e soltar, ou o número do botão apertado (0 = nenhum) |
| `with ajustando('kp', 0.4, 0.05):` | ajusta um número com os botões de cima e de baixo enquanto o programa roda, sem reenviar (use `ler('kp')`) |

### Para competição: obr.py

Quem compete pode usar funções prontas com `from obr import *`: `Seguidor(kp=..., kd=..., velocidade=...)`
com `seguidor.passo()` dentro do laço (PID com velocidade adaptativa opcional), `curva_esquerda()` /
`curva_direita()` (avança até as rodas chegarem na esquina, vira 90° e procura a linha),
`procurar_linha()`, `ve_verde(porta)` e `desviar('direita')`. São um ponto de partida, ainda não
testadas no robô: cada robô tem sensores e rodas num lugar diferente, então ajuste os números no seu.
Veja o exemplo no começo do [obr.py](obr.py).

Comparações (`<`, `<=`, `>`, `>=`, `==`, `!=`) com sensores e variáveis do robô funcionam no `if`,
no `elif`, no `while` (também com `not`), em `se(...)` e em `repetir_ate(...)`. Como a leitura
acontece no robô, e não no computador, o `if` e o `while` com sensor viram os blocos de decisão e de
repetição do robô; `and` e `or` viram um `if` dentro do outro. Um `while` com sensor ainda não aceita
`break`, e o `x if ... else y` numa linha só não funciona com sensor (o programa avisa nos dois casos).

### Ajustando ao seu robô: calibracao.py

As medidas do robô ficam no [calibracao.py](calibracao.py), e todos os programas da pasta usam esses
números sozinhos. Os valores que vêm nele foram medidos num robô EST: com eles, `andar_cm(30)` anda
30 cm e `virar_direita(90)` vira 90°. Meça uma vez por robô:

- `MOTOR_ESQUERDO`, `MOTOR_DIREITO` e `INVERTIDO` (True se o robô andar de ré quando deveria ir para frente).
- `RODA_CM` acerta o `andar_cm`: se `andar_cm(30)` andar menos que 30 cm, diminua.
- `ENTRE_RODAS_CM` acerta o `virar_direita(90)`: se o robô virar a mais, diminua; se virar a menos, aumente.
- `PAUSA` é o tempo parado depois de cada movimento que freia. Sem ela, o robô emenda um movimento no
  outro e as viradas saem erradas; `0` desliga.
- `PRETO` e `BRANCO`: a luz refletida de cada sensor no preto e no branco. Para ver os números,
  **Terminal → Executar Tarefa → Ver sensores na tela do robô** (a controladora não manda as leituras
  pelo USB: elas aparecem na tela dela). Nos programas, `limite(1)` dá o meio entre o preto e o
  branco do sensor 1: `if luz_refletida(1) < limite(1):`.

Um programa pode mudar algum valor só para ele com `configurar(roda_cm=5.6)`, por exemplo.

Antes de enviar, o programa confere o robô e avisa:
- se a IDE EST estiver aberta, porque ela conversa com o robô ao mesmo tempo e pode atrapalhar;
- se o programa usar uma porta em que o robô não tem nada ligado, por exemplo um sensor na porta 4
  ou o motor A. O robô informa pelo USB o que está ligado em cada porta.

## Exemplo

[exemplos/11_seguidor_dois_sensores.py](exemplos/11_seguidor_dois_sensores.py): seguidor básico com
dois sensores (se S1 vê preto vira, senão se S2 vê preto vira para o outro lado, senão anda reto),
conferido no simulador.

## Para quem quer ir além

Os comandos em português geram blocos de [blocos.py](blocos.py), que seguem os blocos da IDE
oficial (fios entre saídas e entradas, parâmetros por número). Os dois podem ser usados juntos: um
programa só de blocos define `PROGRAMA = [start(), ...]` (veja os testes em
[verificar_gabaritos.py](verificar_gabaritos.py)).

| Arquivo | Papel |
|---|---|
| [robo.py](robo.py) | a linguagem em português |
| [blocos.py](blocos.py) | os blocos da IDE |
| [estc.py](estc.py) | o compilador: registradores, threads, fios, saltos |
| [est_protocol.py](est_protocol.py) | o protocolo USB HID (gravar e executar) |
| [enviar.py](enviar.py) | compila o arquivo e envia |
| [simular.py](simular.py) | compila o arquivo e abre o simulador |
| [simulador/](simulador/) | o simulador: VM do robô em JavaScript (`vm.js`), física (`robo.js`), pistas (`mundo.js`) e a página |
| [verificar_gabaritos.py](verificar_gabaritos.py) | testes: compara com a IDE oficial e confere a linguagem |
| [gabaritos/](gabaritos/) | programas compilados pela IDE oficial, usados como referência |
| [ferramentas/decodificar.py](ferramentas/decodificar.py) | mostra o bytecode instrução por instrução |
| [ferramentas/testar_robo.py](ferramentas/testar_robo.py) | teste de conexão com o robô |
| [ferramentas/ver_sensores.py](ferramentas/ver_sensores.py) | mostra a luz dos sensores S1, S2 e S3 na tela do robô (para medir o preto e o branco) |
| [ferramentas/programas_no_robo.py](ferramentas/programas_no_robo.py) | lista e apaga os programas gravados no robô e mostra a bateria |
| [ferramentas/rodar.cmd](ferramentas/rodar.cmd) | as tarefas do VS Code usam o Python do pacote, se houver, ou o do computador |
| [ferramentas/atualizar.py](ferramentas/atualizar.py) | tarefa "Atualizar o projeto" (baixa a versão nova sem mexer nos arquivos do professor) |
| [ferramentas/empacotar.py](ferramentas/empacotar.py) | monta o pacote para Windows com o Python dentro |
| [calibracao.py](calibracao.py) | as medidas do robô (roda, entre rodas, motores, preto e branco de cada sensor) |
| [ferramentas/publicar_simulador.py](ferramentas/publicar_simulador.py) | copia o simulador para `docs/simulador/` com o exemplo compilado (a demonstração online) |
| [instalar.bat](instalar.bat) | prepara um computador novo |
| [docs/formato.md](docs/formato.md) | protocolo, estrutura do programa e instruções da VM |

```bash
python verificar_gabaritos.py
```

O resultado esperado é `13/13 gabaritos identicos` e `linguagem em portugues: OK`.

**Já testado no robô:** movimento (com `andar_cm` e `virar_*` calibrados), seguidores de linha
(liga-desliga, proporcional e PID), parar na linha, tela, som, luz, esperar, ultrassom, `se(...)`,
`repetir_ate(...)`, variáveis, `cor_vista`, envio em pedaços e "gravar sem executar".
**Ainda não visto funcionando no robô:** o sensor de toque (os bytes batem com a IDE), `ao_mesmo_tempo`,
os botões da controladora, `ajustando`, o envio pelo navegador e as tarefas "Programas no robô" e
"Bateria do robô". Cada comando em português gera exatamente o que a IDE geraria para o bloco equivalente.

### Versões e testes automáticos

A versão instalada fica no arquivo [VERSAO](VERSAO) e o que mudou em cada uma, no
[NOVIDADES.md](NOVIDADES.md). A cada envio para o GitHub, os testes rodam sozinhos
([.github/workflows/testes.yml](.github/workflows/testes.yml)): conferência com a IDE, testes da
linguagem e erros de escrita nos arquivos Python e JavaScript.

Para publicar uma versão nova: mude o número no `VERSAO`, escreva as novidades no `NOVIDADES.md`, faça
o commit e o push, e envie a tag com o mesmo número:

```bash
git tag v0.2.0
git push origin v0.2.0
```

O GitHub testa, monta o pacote para Windows com o Python dentro e publica a versão em Releases
([.github/workflows/publicar.yml](.github/workflows/publicar.yml)). É dessa versão publicada que o
"Atualizar o projeto" dos professores baixa.

## Licença e aviso

Código e material sob a [licença MIT](LICENSE): pode usar, copiar e adaptar livremente, mantendo o
aviso de licença.

Projeto independente, sem relação com o fabricante do robô. O formato foi obtido por engenharia
reversa, para interoperabilidade. Use por sua conta e risco.
