# Guia do professor

Roteiro de 8 aulas para ensinar programação com o robô EST pelo VS Code. Cada aula parte de um
programa curto, que a turma digita, e introduz um conceito de programação. A ideia de cada encontro
é: **digitar e ver o programa funcionando → os alunos mudam números e veem o efeito → desafios**.

## Antes da primeira aula

- Instale tudo em cada computador seguindo o [INSTALAR.md](../INSTALAR.md). Onde não dá para instalar
  programas, use o `est-robot-windows.zip`, que já traz o Python: copie para cada computador (pode ser
  por pendrive), use **Extrair Tudo** e abra a pasta no VS Code. Dica: prepare um computador, meça o
  robô no `calibracao.py` e copie a pasta inteira para os outros.
- De tempos em tempos, rode a tarefa **Atualizar o projeto**. Ela troca só os arquivos do projeto e
  nunca mexe no `calibracao.py`, no `meu_programa.py` nem em programas criados por vocês; a versão
  antiga do que foi trocado fica em `copias_de_seguranca`. Peça a cada aluno que salve o programa num
  arquivo com nome próprio (ex.: `aulas\joao_aula3.py`).
- A tarefa **Programas no robô** mostra a bateria e apaga os programas antigos da pasta vscode do robô.
- Em cada computador, com o robô no USB, abra o `meu_programa.py` e aperte **`Ctrl+Shift+B`**: luz,
  som e "Funcionou!" na tela mostram que conectou (a tarefa **Testar conexão com o robô** faz o mesmo).
- Descubra em que porta está cada sensor do seu robô (S1, S2, S3, S4) e anote no quadro: os
  programas deste guia usam S1 e S2 para os sensores de cor e S4 para toque e ultrassom.
- Rode o quadrado da aula 2. Os valores do `calibracao.py` foram medidos num robô EST e fazem o
  quadrado certo. Se o seu robô virar mais ou menos que 90°, ajuste `ENTRE_RODAS_CM`; se cada lado não
  tiver 30 cm, ajuste `RODA_CM`. Com a tarefa **Ver sensores na tela do robô**, anote também o preto e
  o branco de cada sensor (`PRETO` e `BRANCO`). Fica tudo no `calibracao.py` do computador daquele
  robô, e os programas dos alunos usam sozinhos.

## Como é uma aula

1. O aluno cria um arquivo `.py` (por exemplo `aula1_joao.py`) com a primeira linha
   `from robo import *`.
2. Escreve os comandos e aperta **`Ctrl+Shift+B`**: o programa vai para o robô e já começa a rodar.
   Para o robô esperar na posição de largada, use a tarefa **Gravar no robô sem executar** e inicie
   pelo menu do robô (pasta **vscode**).
3. Se houver erro, aparece no terminal **em português, com o número da linha**, e nada é enviado.

**Segurança:** o robô se mexe logo depois do envio. Combine com a turma: robô no chão (nunca na
mesa) e ninguém na frente dele. Para parar um programa, use o botão do robô.

**Dica:** passar o mouse sobre um comando no VS Code mostra a explicação dele, e começar a digitar
mostra a lista de comandos (autocompletar).

## Quando não há robô para todos: o simulador

Com o programa aberto, **Terminal → Executar Tarefa → Simular no computador** abre o programa no
navegador, com o robô numa pista vista de cima. Ele executa os mesmos bytes que iriam para o robô,
então os erros de lógica aparecem do mesmo jeito. Use para:

- as equipes testarem enquanto esperam a vez do robô;
- mostrar no projetor o que o programa faz linha a linha (a linha que está rodando fica destacada) e
  o valor das variáveis, por exemplo no PID;
- conferir a ideia antes de gastar bateria: o quadrado fecha? o seguidor faz a curva de 90°?

Arraste o robô para a largada (a bolinha azul gira) e escolha a pista. Antes, meça o robô da turma
(roda, distância entre as rodas, posição dos sensores) e ajuste em **Medidas do robô**. O simulador
não tem escorregão, bateria fraca nem variação de luz: o teste final é sempre no robô.

---

## Aula 1: sequência

**Conceito:** um programa é uma lista de passos executados em ordem.

**Programa da aula** (a turma digita):

```python
from robo import *

# Anda para frente, para um pouco, vira e volta de ré.
andar(rotacoes=2)
esperar(1)
virar_direita(90)
andar_cm(20)
re(rotacoes=1)
```

**Comandos:** `andar(rotacoes=...)`, `re(...)`, `esperar(...)`, `virar_direita(90)`, `andar_cm(...)`

**Roteiro**
- Antes de enviar, peça para preverem o caminho.
- Os alunos trocam números: mais rotações, outra potência (`andar(rotacoes=2, potencia=30)`), virar para o outro lado.

**Desafios**
1. Ir até uma marca no chão e voltar de ré.
2. Fazer um "L": andar, virar 90°, andar.
3. Estacionar numa "vaga" desenhada com fita.

**Erros comuns:** esquecer `from robo import *`; escrever `0,5` em vez de `0.5`; esquecer os
parênteses (`andar` em vez de `andar(rotacoes=1)`).

## Aula 2: repetição

**Conceito:** repetir um bloco de comandos em vez de copiá-lo.

**Programa da aula** (a turma digita):

```python
from robo import *

with repetir(4):            # um quadrado: andar e virar 90 graus, 4 vezes
    andar_cm(30)
    virar_direita(90)
```

**Comandos:** `with repetir(n):`

**Roteiro**
- Primeiro escrevam o quadrado *sem* `repetir` (8 linhas); depois mostre a versão com `repetir`.
- Destaque o `:` no fim do `with` e os espaços no começo das linhas de dentro: é isso que diz o que repete.

**Desafios**
1. Triângulo (dica: o robô vira 120° em cada canto).
2. Hexágono (6 lados, 60°).
3. Zigue-zague: repetir 5 vezes andar, virar 45° para um lado, andar, virar 45° para o outro.

**Erros comuns:** esquecer o `:`; linhas de dentro sem espaço no começo (o programa avisa as duas coisas).

**Python de verdade:** quando a turma já estiver à vontade com o `with`, mostre que o `if`, o `else`,
o `elif` e o `while` do Python também funcionam com os sensores: `if luz_refletida(1) < 50:` faz o
mesmo que `with se(luz_refletida(1) < 50):`. É o mesmo Python que eles vão encontrar fora do robô.

## Aula 3: sensores e decisões

**Conceito:** o programa decide o que fazer conforme o que o sensor vê.

**Programa da aula** (a turma digita):

```python
from robo import *

# Seguidor com um sensor (S1) na borda esquerda da linha preta.
with para_sempre():
    with se_ver_cor(1, PRETO):
        motores(10, 30)     # viu preto: puxa para a esquerda
    with senao():
        motores(30, 10)     # viu branco: puxa para a direita
```

**Comandos:** `with para_sempre():`, `with se_ver_cor(porta, cor):`, `with senao():`, `motores(esq, dir)`

**Roteiro**
- Desenhe uma linha preta grossa no chão claro (fita isolante funciona).
- Explique o "se… senão": viu preto, puxa para um lado; senão, puxa para o outro.
- Mostre que `motores(10, 30)` faz o robô curvar (um lado mais rápido que o outro).

**Desafios**
1. Seguir a linha pela outra borda (troque os dois `motores`).
2. Andar até encontrar a linha e parar: `with repetir_ate_cor(1, PRETO): motores(30, 30)` e depois `parar()`.
3. Deixar o seguidor mais rápido sem sair da linha.

## Aula 4: matemática no robô (controle proporcional)

**Conceito:** usar contas com valores de sensor para controlar o movimento.

**Programa da aula** (a turma digita):

```python
from robo import *

# Seguidor proporcional: S1 à esquerda e S2 à direita da linha.
VELOCIDADE = 25
GANHO = 0.4

with para_sempre():
    erro = luz_refletida(1) - luz_refletida(2)
    correcao = erro * GANHO
    motores(VELOCIDADE + correcao, VELOCIDADE - correcao)
```

**Comandos:** `luz_refletida(porta)`, contas `+ - * /` com sensores

**Roteiro**
- Compare com a aula 3: em vez de só "viu ou não viu", o robô mede *quanto* está fora da linha.
- `erro = luz_refletida(1) - luz_refletida(2)`: se a linha está embaixo do sensor esquerdo, o erro fica negativo.
- O robô corrige mais forte quanto maior o erro.

**Desafios**
1. Mudar o `GANHO` (0.2, 0.4, 0.8): o que acontece? (pouco: sai nas curvas; muito: balança).
2. Achar a maior `VELOCIDADE` que ainda completa a pista.
3. Cronometrar uma volta e fazer uma competição entre as equipes.

## Aula 5: ultrassom e obstáculos

**Conceito:** decidir por distância; condições com números.

**Programa da aula** (a turma digita):

```python
from robo import *

# Anda até chegar perto de um obstáculo (ultrassom na porta 4), dá ré e vira.
with para_sempre():
    with se_distancia(4, '<', 15):
        re(rotacoes=0.5)
        virar_direita(90)
    with senao():
        motores(30, 30)
```

**Comandos:** `distancia(porta)`, `with se_distancia(porta, '<', cm):`, `with se(distancia(4) < 15):`

**Desafios**
1. Parar a exatamente 10 cm de uma caixa.
2. Desviar sempre para o lado contrário da última vez.
3. Andar em linha reta e contar (com bips) quantos obstáculos passaram na frente.

## Aula 6: toque, som e luz

**Conceito:** esperar um evento; dar sinais para as pessoas.

**Programa da aula** (a turma digita):

```python
from robo import *

# Espera apertar o sensor de toque (porta 4) para começar.
mostrar('Aperte')
mostrar('o botao', linha=2)
esperar_toque(4)
bip()
luz('azul')
andar(rotacoes=2)
apagar_luz()
```

**Comandos:** `esperar_toque(porta)`, `with se_tocado(porta):`, `bip()`, `tocar(freq, seg)`, `luz('azul' | 'roxo' | 'vermelho')`, `apagar_luz()`, `mostrar(texto, linha=1..3)`

**Desafios**
1. Campainha: cada toque faz um bip.
2. Sinal de trânsito do robô: luz azul (pode ir), roxa (atenção), vermelha (pare), com esperas entre elas.
3. Uma musiquinha com `melodia('do re mi fa sol sol:0.6')` (as notas também vão no `tocar('la', 0.5)`).
4. Andar e tocar a música ao mesmo tempo, com `with ao_mesmo_tempo():` e um `with tarefa():` para
   cada parte (ainda não testado no robô: confira no simulador e depois no robô).

## Aula 7: medindo com sensores

**Conceito:** observar dados antes de programar; escolher um limite.

**Programa da aula** (a turma digita):

```python
from robo import *

# Mostra sem parar quanta luz o S1 vê (0 = escuro, 100 = claro).
with para_sempre():
    mostrar('Luz:')
    mostrar(luz_refletida(1), linha=2)
    esperar(0.2)
```

**Comandos:** `mostrar(valor, linha=2)` (a tela tem 3 linhas), `esperar_luz(porta, '<', valor)`, `with se_luz(porta, '<', valor):`

**Roteiro**
- Os alunos anotam numa tabela o valor da luz refletida em cima do preto e em cima do branco.
- O limite para decidir é a média dos dois. Usem esse número num `se_luz`.

**Dica:** `painel(s1=luz_refletida(1), s2=luz_refletida(2))` mostra os dois sensores ao mesmo tempo,
um em cada linha.

**Desafios**
1. Medir também o verde, o vermelho e o azul. Qual é fácil de separar do preto?
2. Fazer o robô parar quando chegar na faixa preta usando `esperar_luz`.

## Aula 8: variáveis

**Conceito:** guardar um valor e mudá-lo durante o programa.

**Programa da aula** (a turma digita):

```python
from robo import *

# Conta de 1 até 10 na tela, com um bip a cada número.
guardar('contador', 0)

with repetir(10):
    guardar('contador', ler('contador') + 1)
    mostrar('Contando')
    mostrar(ler('contador'), linha=2)
    bip()
    esperar(1)
```

**Comandos:** `guardar(nome, valor)`, `ler(nome)`

**Desafios**
1. Cronômetro: mostrar os segundos passando na tela.
2. Contar quantas vezes o sensor de toque foi apertado.
3. Contar quantas linhas pretas o robô cruzou andando em frente.

---

## Ainda não conferido em todos os robôs

Já testados no robô: movimento (`andar`, `re`, rotações, graus e segundos, com e sem frear),
`andar_cm` e `virar_*` (o quadrado fecha certo), seguidor de linha, parar na linha (`esperar_luz`,
`repetir_ate_luz`, `repetir_ate_cor`), tela (3 linhas), som, luz (azul, roxo, vermelho), esperar,
ultrassom (inclusive desviando de obstáculo com o robô andando), `se(...)`, `repetir_ate(...)`,
variáveis e `cor_vista`. Ainda não visto funcionando: o sensor de toque (o
compilador gera para ele os mesmos bytes que a IDE oficial).
Teste antes de levar para a turma.

**Movimentos seguidos:** depois de cada movimento que freia (`andar`, `re`, `andar_cm`, `girar_*`,
`virar_*`), o robô fica parado meio segundo antes do próximo comando. Sem essa pausa ele emenda um
movimento no outro e as viradas saem erradas. Dá para mudar a `PAUSA` no `calibracao.py`.

**Sensor de cor:** cada sensor deve ser usado num modo só. Misturar comandos de cor (`cor_vista`, `se_ver_cor`) com
comandos de luz refletida (`luz_refletida`, `se_luz`) no mesmo sensor faz ele trocar de modo o tempo todo, ficar lento
e errar leituras; o programa mostra um aviso quando isso acontece. No modo cor, o branco às vezes aparece como 0
("nenhuma cor"): para linha preta no chão branco, a luz refletida é mais confiável.

**Bateria:** com a bateria fraca o robô mostra um aviso na tela, se desconecta do USB e deixa de
executar partes do programa. Se algo estranho acontecer, carregue o robô antes de procurar erro no
programa.
