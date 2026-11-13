# Tutorial do EST-LAB para IAs

Este arquivo ensina uma IA (ChatGPT, Claude, Gemini, Copilot...) a escrever programas para a
controladora EST usando o EST-LAB. Sem ele, a IA costuma inventar comandos ou escrever um Python que o
robô não entende.

**Como usar**

1. Anexe este arquivo na conversa com a IA, ou copie e cole o texto todo. Se a IA consegue abrir links,
   mande este endereço:
   `https://raw.githubusercontent.com/AndreyViolante/est-robot/master/docs/tutorial-para-ia.md`
2. Conte como é o seu robô (em que porta está cada sensor e cada motor) e o que ele deve fazer.
3. Copie o programa para o `meu_programa.py` (ou para a [página de programar](https://andreyviolante.github.io/est-robot/programar/)),
   teste no simulador e mande para o robô.
4. Se aparecer `ERRO` ou `AVISO`, cole a mensagem inteira na conversa.

Daqui para baixo, o texto é para a IA.

---

## 1. O robô e o EST-LAB

- A **controladora EST** é um robô educacional parecido com o LEGO EV3: 4 portas de sensor (`1` a `4`),
  4 portas de motor (`'A'` a `'D'`), tela de 3 linhas, som, uma luz colorida e botões (cima, baixo,
  esquerda, direita, OK e voltar).
- Sensores que existem: cor (luz refletida ou cor vista), ultrassom (distância), toque e giroscópio.
- O **EST-LAB** deixa programar a controladora em Python, com comandos em português. O programa começa
  sempre com `from robo import *`. O EST-LAB compila o programa para o código da controladora e envia
  pelo USB (no VS Code, `Ctrl+Shift+B`) ou pela página de programar no navegador. Há um simulador.
- **Não é MicroPython**: o Python não roda dentro do robô. Leia a seção 2 antes de escrever qualquer
  programa.

## 2. Como o arquivo vira programa do robô

O arquivo `.py` roda **uma vez, no computador**, e cada comando que ele chama vira um bloco do
programa do robô, na ordem em que aparece. Depois disso o robô executa os blocos sozinho, sem o
computador. Consequências:

**Leituras de sensor só existem no robô.** `luz_refletida(1)`, `distancia(4)`, `ler('x')` e as contas
com elas (`+ - * /`) não são números do Python: são instruções que o robô executa na hora. Elas
funcionam dentro de comandos do robô (`motores(...)`, `mostrar(...)`, `guardar(...)`) e em
comparações (`<`, `<=`, `>`, `>=`, `==`, `!=`) usadas em `if`, `elif`, `while`, `se(...)` e
`repetir_ate(...)`.

**`if`, `elif`, `else` e `while` com sensor viram decisões e repetições do robô.** O EST-LAB reescreve
esses comandos. `and`, `or` e `not` também funcionam com sensores. `while True:` vira "repetir para
sempre". Se a condição for só do Python (por exemplo `if VEL > 20:`), ela é decidida na hora de montar o
programa.

**Variáveis do Python não guardam valores no robô.** Um nome do Python só aponta para uma leitura ou uma
conta. Para guardar um número que muda enquanto o robô anda (contador, erro anterior, estado), use as
variáveis do robô: `guardar('nome', valor)` e `ler('nome')`.

```python
# ERRADO: o "+ 1" do Python acontece uma vez só, quando o programa é montado
contador = 0
while True:
    esperar_toque(1)
    contador = contador + 1
    mostrar(contador)
```

```python
# CERTO: o contador fica no robô
guardar('contador', 0)
while True:
    esperar_toque(1)
    guardar('contador', ler('contador') + 1)
    mostrar(ler('contador'))
```

**Leia o sensor dentro do laço.** `erro = luz_refletida(1) - luz_refletida(2)` lê os sensores no lugar
onde a linha está. Dentro do laço, lê de novo a cada volta. Fora do laço, lê uma vez só.

**Constantes do Python são ótimas** para os números de ajuste (`VEL = 25`, `KP = 0.4`): elas entram
fixas no programa.

**Funções (`def`) são copiar e colar.** Cada vez que uma função é chamada, os comandos dela entram de
novo no programa. Use funções para organizar (uma parte da tarefa em cada uma), mas chame cada uma em
poucos lugares. Uma função pode devolver uma comparação: `def viu_obstaculo(): return distancia(4) < 10`
e depois `if viu_obstaculo():`.

**`for` tem dois jeitos.** `for _ in range(4):` (sem usar a variável) vira "repetir 4 vezes" no robô.
`for i in range(3):` usando o `i` faz o Python escrever o corpo 3 vezes, uma para cada `i` (o programa
fica maior). O número do `range` precisa estar escrito no programa: não pode ser leitura de sensor.

**O que não funciona com valores do robô:**

| Não use | Use |
|---|---|
| `print(...)`, `input(...)` | `mostrar(...)`, `painel(...)`, `esperar_botao()` |
| `time.sleep(1)`, `import time` | `esperar(1)` |
| `import random`, `random.randint` | `aleatorio(1, 6)` |
| `round(leitura)`, `int(leitura)` | `arredondar(leitura)` |
| `abs(erro)` | um `if erro < 0:` com os dois casos |
| `x = a if sensor < 50 else b` | `if`/`else` com `guardar('x', ...)` em cada caso |
| `break` ou `continue` dentro de `while` com sensor | a condição no próprio `while`, ou `repetir_ate(...)` |
| `while True:` com `break` | `while condicao:` ou `with repetir_ate(lambda: condicao):` |
| `'Luz: ' + str(luz_refletida(1))` | `mostrar('Luz:')` e `mostrar(luz_refletida(1), linha=2)`, ou `painel(luz=luz_refletida(1))` |
| `range(ler('n'))` | `with repetir(5):` com um número escrito |
| outros `import`, classes, arquivos, listas de leituras | só os comandos da seção 4 |

## 3. Regras para escrever o programa

1. A primeira linha é sempre `from robo import *`.
2. Use **só** os comandos da seção 4. Não invente nomes nem opções. Se algo não existe, diga que não
   existe.
3. Portas de sensor são números (`luz_refletida(1)`). Portas de motor são texto (`motor('A', 50)`).
   As rodas já estão configuradas no `calibracao.py` (por padrão, esquerda `'B'` e direita `'C'`):
   `andar`, `motores`, `virar_direita` etc. usam as rodas sozinhos.
4. Potência vai de `-100` a `100`. Positivo é para frente, negativo é ré. Se o robô do aluno anda ao
   contrário, a correção é `INVERTIDO = True` no `calibracao.py`, e não trocar os sinais no programa.
5. Número com casa decimal usa ponto: `0.5`.
6. Para linha preta no chão branco, use **luz refletida** (`luz_refletida`, `se_luz`, `esperar_luz`) com
   `limite(porta)` ou `limite_medido(porta)`, em vez de um número fixo. A cor (`cor_vista`) serve para
   achar o verde ou o vermelho.
7. **Um modo por sensor**: não use `cor_vista` e `luz_refletida` no mesmo sensor no mesmo programa. O
   sensor fica trocando de modo, fica lento e erra.
8. Todo laço sem fim precisa ler um sensor ou esperar (`esperar(0.1)`). Sem isso ele repete milhares de
   vezes por segundo a mesma coisa (o EST-LAB avisa).
9. Se usou `motores(...)` ou `ligar_motor(...)`, desligue com `parar()` ou `desligar_motor(...)` antes do
   programa terminar.
10. A tela tem 3 linhas de umas 15 letras. A linha 1 apaga a tela antes de escrever; as linhas 2 e 3 não
    apagam. Textos na tela vão sem acento (o EST-LAB tira os acentos).
11. Nomes de variáveis do robô (`guardar('nome', ...)`): letras sem acento, números e `_`. Guarde um
    valor antes de ler.
12. Nas comparações escritas como texto (`esperar_luz(1, '<', 30)`, `se_distancia(4, '>=', 20)`), as
    opções são `'<'`, `'<='`, `'>'`, `'>='`, `'='` (um igual só) e `'!='`. No `if` e no `while`, use os
    operadores normais do Python (`==` com dois iguais).

## 4. Comandos

### Movimento

| Comando | O que faz |
|---|---|
| `andar(rotacoes=2)`, `andar(graus=360)`, `andar(segundos=1.5)` | anda para frente. Use só um de `rotacoes`, `graus` ou `segundos` (das rodas). Opções: `potencia=50`, `frear=True` |
| `re(rotacoes=1)` | anda de ré (mesmas opções) |
| `andar_cm(30)` | anda 30 cm (negativo = ré). Opção: `potencia=50` |
| `virar_direita(90)`, `virar_esquerda(90)` | vira o robô no lugar, em graus do robô. Opção: `potencia=30` |
| `girar_direita(rotacoes=0.5)`, `girar_esquerda(segundos=1)` | gira no lugar; rotações, graus ou segundos são das rodas |
| `mover(30, 10, rotacoes=1)` | roda esquerda e roda direita, cada uma com a sua potência, por `rotacoes`, `graus` ou `segundos` |
| `motores(esq, dir)` | liga as duas rodas e deixa ligadas. Aceita leituras e contas: `motores(25 + erro * KP, 25 - erro * KP)` |
| `parar()` | desliga as rodas (`parar(frear=False)` deixa rodar solto) |
| `motor('A', 50, graus=180)` | gira um motor sozinho (garra, braço): `rotacoes`, `graus` ou `segundos` |
| `ligar_motor('A', 50)`, `desligar_motor('A')` | liga um motor e deixa ligado / desliga |

Depois de cada movimento que freia, o robô fica parado `PAUSA` segundos (0,5 no `calibracao.py`). Sem
isso as viradas saem erradas. Não é preciso pôr `esperar` entre `andar_cm` e `virar_direita`.

### Sensores (dão leituras, que entram em contas e comparações)

| Comando | Dá |
|---|---|
| `luz_refletida(1)` | luz refletida, de 0 (escuro) a 100 (claro) |
| `cor_vista(1)` | a cor: compare com `PRETO`, `AZUL`, `VERDE`, `AMARELO`, `VERMELHO`, `BRANCO`, `MARROM` (`if cor_vista(3) == VERDE:`). Dá 0 quando não reconhece |
| `distancia(4)` | ultrassom, em centímetros |
| `tocado(1)` | sensor de toque: 1 apertado, 0 solto |
| `giroscopio(2)` | ângulo do robô em graus desde o começo (ou desde `zerar_giroscopio(2)`) |
| `velocidade_do_giro(2)` | graus por segundo |
| `graus_do_motor('B')`, `rotacoes_do_motor('B')` | quanto o motor girou desde o começo (ou desde `zerar_motor('B')`) |
| `potencia_do_motor('B')` | potência do motor agora |
| `cronometro()`, `cronometro(2)` | segundos desde o começo (ou desde `zerar_cronometro()`); há 8 cronômetros |
| `aleatorio(1, 6)` | número inteiro sorteado no robô |
| `botao_apertado()` | botão da controladora apertado: 0 nenhum, `BOTAO_ESQUERDA` 1, `BOTAO_CENTRO` 2 (OK), `BOTAO_DIREITA` 3, `BOTAO_CIMA` 4, `BOTAO_BAIXO` 5. O botão de voltar termina o programa |
| `limite(1)` | número do Python: o meio entre o preto e o branco do sensor 1, medidos no `calibracao.py` |
| `limite_medido(1)` | o limite que `calibrar_na_largada` mediu na pista |
| `arredondar(valor)` | inteiro mais perto |
| `ler('nome')` | o número guardado numa variável do robô |

`zerar_motor('B')`, `zerar_giroscopio(2)` (com o robô parado) e `zerar_cronometro()` voltam a contagem
para 0.

### Esperar

| Comando | Espera |
|---|---|
| `esperar(1.5)` | segundos |
| `esperar_toque(1)` | apertar o sensor de toque |
| `esperar_distancia(4, '<', 20)` | a distância passar do valor |
| `esperar_luz(1, '<', 30)` | a luz refletida passar do valor |
| `esperar_cor(1, VERDE)` | o sensor ver a cor |
| `esperar_botao()` | apertar e soltar um botão da controladora (bom para largar o robô) |

### Repetir e decidir

| Forma | Faz |
|---|---|
| `while True:` | repete para sempre |
| `while distancia(4) > 15:` | repete enquanto a condição valer |
| `for _ in range(4):` | repete 4 vezes |
| `if ...:` / `elif ...:` / `else:` | decide (também com `and`, `or`, `not`) |
| `with para_sempre():`, `with repetir(4):` | o mesmo, no jeito "with" |
| `with repetir_ate(lambda: distancia(4) < 20):` | repete até a condição (o `lambda:` é obrigatório) |
| `with repetir_ate_luz(1, '<', 30):`, `with repetir_ate_cor(1, PRETO):` | repete até o sensor de cor ver |
| `with se(distancia(4) < 20):` e logo depois `with senao():` | decide, no jeito "with" |
| `with se_luz(1, '<', 30):`, `with se_ver_cor(1, PRETO):`, `with se_tocado(1):`, `with se_distancia(4, '<', 20):` | decide pelo sensor |

`se_ver_cor(1, PRETO + VERDE)` vale para qualquer uma das cores somadas.

### Tela, som e luz

| Comando | O que faz |
|---|---|
| `mostrar('Oi')`, `mostrar(distancia(4), linha=2)` | escreve texto ou valor (`linha=1`, `2` ou `3`; `x=` para a coluna em pixels) |
| `painel(erro=..., vel=...)` | até 3 valores, um por linha, com o nome (até 5 letras) na frente |
| `bip()` | bip curto |
| `tocar(440, 0.5)`, `tocar('la', 0.5)` | som pela frequência (Hz) ou nota (`do re mi fa sol la si`, `'do#'`, `'la4'`), em segundos |
| `melodia('do re mi fa sol:0.6 -')` | notas seguidas; `:segundos` muda uma nota, `-` é pausa; opção `tempo=0.3` |
| `luz('azul')`, `luz('vermelho', piscar=True)`, `apagar_luz()` | luz do robô: `'azul'`, `'roxo'` ou `'vermelho'` |

### Variáveis do robô

| Comando | O que faz |
|---|---|
| `guardar('pontos', 0)`, `guardar('erro', erro)` | guarda um número ou uma leitura |
| `ler('pontos')` | lê (é uma leitura: entra em contas e comparações) |

### Várias coisas ao mesmo tempo

```python
with ao_mesmo_tempo():
    with tarefa():
        andar_cm(30)
    with tarefa():
        melodia('do re mi')
```

Cada `with tarefa():` roda junto com as outras. O programa continua depois do `with ao_mesmo_tempo():`
quando todas acabam. Para passar valores entre tarefas, use `guardar` e `ler`.

### Para competição

| Comando | O que faz |
|---|---|
| `calibrar_na_largada(1, 2)` | com o robô parado sobre a linha (um sensor de cada lado), gira um pouco para cada lado, mede o preto e o branco da pista e guarda o limite. Depois use `limite_medido(1)` |
| `with ajustando('kp', 0.4, 0.05):` | durante o que estiver dentro, os botões de cima e de baixo somam e tiram 0.05 do `kp`, que aparece na linha 3. No programa, use `ler('kp')` |

### Medidas do robô

As medidas ficam no `calibracao.py` e valem para todos os programas: portas das rodas, `INVERTIDO`,
`RODA_CM` (acerta o `andar_cm`), `ENTRE_RODAS_CM` (acerta o `virar_direita`), `PAUSA` e o preto e o branco
de cada sensor (usados pelo `limite`). Um programa pode mudar alguma só para ele com
`configurar(roda_cm=5.6)` (opções: `esquerdo`, `direito`, `invertido`, `roda_cm`, `entre_rodas_cm`,
`pausa`).

### Bluetooth

`enviar_mensagem('erro', erro)`, `enviar_mensagem('oi', 1, para='robo2')`, `mensagem_recebida('kp')`,
`ligar_bluetooth()` e `desligar_bluetooth()` existem, mas ainda não foram vistos funcionando no robô.

## 5. O que já foi conferido no robô

Situação no teste de 13/11/2026, numa controladora com firmware 03.04:

- **Funcionam:** movimentos (`andar`, `re`, `andar_cm`, `virar_*`, `motores`, `mover`, `motor`), luz
  refletida, cor, ultrassom, toque, esperas, `if`/`while`, tela, som, luz, variáveis, botões
  (`botao_apertado`, `esperar_botao`), `ao_mesmo_tempo`, `ajustando`, `calibrar_na_largada`,
  `painel`, `graus_do_motor` e `zerar_motor`, `cronometro`, `aleatorio`, `giroscopio`.
- **Falharam e estão em investigação: não use.** `ajustes(...)` (os botões de cima e de baixo não mudam
  o número) e `medir_laco(...)` (o robô não anda). No lugar do `ajustes`, use um `ajustando` para o
  número mais importante.
- **Ainda não vistos no robô** (funcionam no simulador): `rotacoes_do_motor`, `potencia_do_motor`,
  `velocidade_do_giro`, `arredondar` e o Bluetooth. Se usar, avise o aluno.

## 6. Programas de exemplo

Todos compilam no EST-LAB. Adapte as portas ao robô do aluno.

**Quadrado de 30 cm**

```python
from robo import *

for _ in range(4):
    andar_cm(30)
    virar_direita(90)
```

**Andar até a linha preta e parar**

```python
from robo import *

while luz_refletida(1) > limite(1):     # enquanto o sensor 1 vê branco
    motores(30, 30)
parar()
bip()
```

**Desviar de obstáculos** (ultrassom na porta 4)

```python
from robo import *

while True:
    if distancia(4) < 15:
        parar()
        re(rotacoes=0.5)
        virar_direita(90)
    else:
        motores(40, 40)
```

**Seguidor de linha com dois sensores** (S1 na porta 1, à esquerda da linha; S2 na porta 2, à direita)

```python
from robo import *

RETO = 30           # potência na reta
FORA = 30           # roda de fora da curva
DENTRO = -15        # roda de dentro da curva, um pouco de ré: faz até a curva de 90 graus

while True:
    if luz_refletida(1) < limite(1):        # S1 viu preto: a linha foi para a esquerda
        motores(DENTRO, FORA)
    elif luz_refletida(2) < limite(2):      # S2 viu preto: a linha foi para a direita
        motores(FORA, DENTRO)
    else:
        motores(RETO, RETO)
```

**Seguidor proporcional**

```python
from robo import *

VEL = 25            # velocidade na reta
KP = 0.4            # força da correção: aumente se ele sai da linha nas curvas, diminua se balança

while True:
    erro = luz_refletida(1) - luz_refletida(2)
    motores(VEL + erro * KP, VEL - erro * KP)
```

**Seguidor PD** (o erro da volta anterior fica numa variável do robô)

```python
from robo import *

VEL = 25
KP = 0.4
KD = 1.0            # amortece o balanço

guardar('anterior', 0)
while True:
    erro = luz_refletida(1) - luz_refletida(2)
    correcao = erro * KP + (erro - ler('anterior')) * KD
    motores(VEL + correcao, VEL - correcao)
    guardar('anterior', erro)
```

**Acertar o KP com os botões, sem reenviar**

```python
from robo import *

with ajustando('kp', 0.4, 0.05):        # cima soma 0.05, baixo tira; o valor aparece na linha 3
    while True:
        erro = luz_refletida(1) - luz_refletida(2)
        motores(25 + erro * ler('kp'), 25 - erro * ler('kp'))
```

**Esperar o botão, calibrar na pista e seguir a linha**

```python
from robo import *

mostrar('Aperte um botao')
esperar_botao()
calibrar_na_largada(1, 2)
while True:
    if luz_refletida(1) < limite_medido(1):
        motores(-15, 30)
    elif luz_refletida(2) < limite_medido(2):
        motores(30, -15)
    else:
        motores(30, 30)
```

**Contar toques**

```python
from robo import *

guardar('toques', 0)
mostrar('Toques: 0')
while True:
    esperar_toque(1)
    guardar('toques', ler('toques') + 1)
    mostrar('Toques:')
    mostrar(ler('toques'), linha=2)
    while tocado(1) == 1:               # espera soltar, para contar um toque por vez
        esperar(0.05)
```

**Ver os sensores na tela** (para medir o preto, o branco e a distância)

```python
from robo import *

while True:
    painel(s1=luz_refletida(1), s2=luz_refletida(2), dist=distancia(4))
    esperar(0.2)
```

**Andar e tocar ao mesmo tempo**

```python
from robo import *

with ao_mesmo_tempo():
    with tarefa():
        andar_cm(30)
    with tarefa():
        melodia('do re mi fa sol')
mostrar('Fim')
```

**Programa maior, organizado em funções**

```python
from robo import *

VEL = 25
KP = 0.4


def seguir_linha():
    erro = luz_refletida(1) - luz_refletida(2)
    motores(VEL + erro * KP, VEL - erro * KP)


def viu_obstaculo():
    return distancia(4) < 10


def desviar():
    parar()
    re(rotacoes=0.3)
    virar_direita(90)
    andar_cm(15)
    virar_esquerda(90)


while True:
    if viu_obstaculo():
        desviar()
    else:
        seguir_linha()
```

## 7. Quando o aluno colar um ERRO ou um AVISO

As mensagens dizem a linha e o que corrigir. As mais comuns:

| Mensagem (começo) | O que corrigir |
|---|---|
| `não conheço "..."` | o comando não existe: troque por um da seção 4 (a mensagem às vezes sugere o certo) |
| `esse valor do robô não funciona aqui` / `essa comparação do robô não funciona aqui` | uma leitura ou comparação foi usada onde o Python precisa decidir na hora de montar, como `x if ... else y`. Veja a tabela da seção 2 |
| `a leitura de um sensor só existe no robô` | leitura dentro de `range(...)`, `int()`, `float()` ou `round()`: use um número escrito, ou `arredondar(...)` |
| `aqui precisa de um número, e veio uma leitura de sensor` | leitura num lugar que só aceita número escrito, como `abs(...)`, `andar_cm(...)` ou `esperar(...)` |
| `"break" e "continue" ainda não funcionam num while com sensor` | ponha a condição de parada no próprio `while` ou use `repetir_ate` |
| `a porta ... não é de sensor` / `não é de motor` | sensor com número de 1 a 4; motor com `'A'` a `'D'`, entre aspas |
| `diga quanto andar` / `use só um` | dê exatamente um de `rotacoes=`, `graus=` ou `segundos=` |
| `comparação '==' invalida` | nas comparações em texto, use `'='` |
| `meça o preto e o branco do sensor ...` | o `calibracao.py` não tem o preto e o branco desse sensor: use `calibrar_na_largada` e `limite_medido`, ou peça para medir |
| `não dá para juntar um texto com uma leitura de sensor` | mostre o texto e o valor separados, ou use `painel` |
| `faltou o ":"`, `as linhas de dentro ... precisam começar com espaços` | erro de digitação do Python |
| `AVISO`: `... repete sem nenhuma espera e sem ler nenhum sensor` | ponha `esperar(0.1)` ou uma leitura dentro do laço |
| `AVISO`: `a variável ... é criada mas nunca é usada`, `... é guardada com guardar(...), mas nenhum ler(...)` | apague a variável ou use-a |
| `AVISO`: `o motor ... fica ligado quando o programa termina` | `parar()` ou `desligar_motor(...)` antes do fim |
| `AVISO`: `o sensor da porta ... é usado no modo cor ... e no modo luz` | um modo só por sensor (regra 7) |
| `AVISO`: `... o robô não tem nada ligado nela`, `... o robô diz que lá está ligado um ...` | confira as portas do programa com as do robô |

Se o programa compila mas o robô faz outra coisa, peça ao aluno para testar no simulador e para
descrever o que o robô fez. Desconfie primeiro das portas, do `INVERTIDO` e dos limites de luz.

## 8. Como responder ao aluno

- Se o aluno não disser as portas, use rodas em `'B'` (esquerda) e `'C'` (direita), sensores de cor
  em `1` (esquerda da linha) e `2` (direita), ultrassom em `4`, e diga no começo da resposta que
  supôs isso.
- Entregue o programa inteiro, num bloco de código só, começando com `from robo import *`.
- Ponha os números de ajuste em constantes no topo (`VEL = 25`), com um comentário curto dizendo o que
  acontece se aumentar ou diminuir.
- Comentários curtos e em português.
- Depois do programa, explique em poucas linhas o que ele faz e o que ajustar primeiro. O objetivo é o
  aluno entender e conseguir mudar o programa sozinho. Em competição (como a OBR), quem programa é a
  equipe: ajude a entender, sem entregar a solução da prova.
- Sugira testar no simulador antes do robô:
  [simulador](https://andreyviolante.github.io/est-robot/simulador/) ou o botão Simular da página de
  programar.
- Programas pequenos. Cada função chamada entra de novo no programa; o EST-LAB mostra quanto do espaço do
  robô o programa usa.
- Não use os comandos marcados como "não use" na seção 5. Para algo que o EST-LAB não tem, diga que não
  tem em vez de inventar.
