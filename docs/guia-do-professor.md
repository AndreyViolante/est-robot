# Guia do professor

Roteiro de 8 aulas para ensinar programação com o robô EST pelo VS Code. Cada aula parte de um
exemplo da pasta `exemplos/` e introduz um conceito de programação. A ideia de cada encontro é:
**mostrar o exemplo funcionando → os alunos mudam números e veem o efeito → desafios**.

## Antes da primeira aula

- Instale tudo em cada computador seguindo o [INSTALAR.md](../INSTALAR.md).
- Em cada robô, rode a tarefa **Testar conexão com o robô** (Terminal → Executar Tarefa).
- Descubra em que porta está cada sensor do seu robô (S1, S2, S3, S4) e anote no quadro: os
  exemplos usam S1 e S2 para os sensores de cor e S4 para toque e ultrassom.
- Rode o `exemplos/2_quadrado.py`. Os valores padrão foram medidos num robô EST e fazem o quadrado
  certo. Se o seu robô virar mais ou menos que 90°, ajuste `configurar(entre_rodas_cm=...)`; se cada
  lado não tiver 30 cm, ajuste `configurar(roda_cm=...)`. Anote os valores do seu robô para passar
  aos alunos.

## Como é uma aula

1. O aluno cria um arquivo `.py` (por exemplo `aula1_joao.py`) com a primeira linha
   `from robo import *`.
2. Escreve os comandos e aperta **`Ctrl+Shift+B`**: o programa vai para o robô e já começa a rodar.
3. Se houver erro, aparece no terminal **em português, com o número da linha**, e nada é enviado.

**Segurança:** o robô se mexe logo depois do envio. Combine com a turma: robô no chão (nunca na
mesa) e ninguém na frente dele. Para parar um programa, use o botão do robô.

**Dica:** passar o mouse sobre um comando no VS Code mostra a explicação dele, e começar a digitar
mostra a lista de comandos (autocompletar).

---

## Aula 1: sequência

**Exemplo:** `1_andar_e_virar.py` · **Conceito:** um programa é uma lista de passos executados em ordem.

**Comandos:** `andar(rotacoes=...)`, `re(...)`, `esperar(...)`, `virar_direita(90)`, `andar_cm(...)`

**Roteiro**
- Mostre o exemplo e peça para preverem o caminho antes de enviar.
- Os alunos trocam números: mais rotações, outra potência (`andar(rotacoes=2, potencia=30)`), virar para o outro lado.

**Desafios**
1. Ir até uma marca no chão e voltar de ré.
2. Fazer um "L": andar, virar 90°, andar.
3. Estacionar numa "vaga" desenhada com fita.

**Erros comuns:** esquecer `from robo import *`; escrever `0,5` em vez de `0.5`; esquecer os
parênteses (`andar` em vez de `andar(rotacoes=1)`).

## Aula 2: repetição

**Exemplo:** `2_quadrado.py` · **Conceito:** repetir um bloco de comandos em vez de copiá-lo.

**Comandos:** `with repetir(n):`

**Roteiro**
- Primeiro escrevam o quadrado *sem* `repetir` (8 linhas); depois mostre a versão com `repetir`.
- Destaque o `:` no fim do `with` e os espaços no começo das linhas de dentro: é isso que diz o que repete.

**Desafios**
1. Triângulo (dica: o robô vira 120° em cada canto).
2. Hexágono (6 lados, 60°).
3. Zigue-zague: repetir 5 vezes andar, virar 45° para um lado, andar, virar 45° para o outro.

**Erros comuns:** esquecer o `:`; linhas de dentro sem espaço no começo (o programa avisa as duas coisas).

## Aula 3: sensores e decisões

**Exemplo:** `3_seguidor_liga_desliga.py` · **Conceito:** o programa decide o que fazer conforme o que o sensor vê.

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

**Exemplo:** `4_seguidor_proporcional.py` · **Conceito:** usar contas com valores de sensor para controlar o movimento.

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

**Exemplo:** `5_desviar_obstaculo.py` · **Conceito:** decidir por distância; condições com números.

**Comandos:** `distancia(porta)`, `with se_distancia(porta, '<', cm):`, `with se(distancia(4) < 15):`

**Desafios**
1. Parar a exatamente 10 cm de uma caixa.
2. Desviar sempre para o lado contrário da última vez.
3. Andar em linha reta e contar (com bips) quantos obstáculos passaram na frente.

## Aula 6: toque, som e luz

**Exemplo:** `6_botao_de_toque.py` · **Conceito:** esperar um evento; dar sinais para as pessoas.

**Comandos:** `esperar_toque(porta)`, `with se_tocado(porta):`, `bip()`, `tocar(freq, seg)`, `luz('azul' | 'roxo' | 'vermelho')`, `apagar_luz()`, `mostrar(texto, linha=1..3)`

**Desafios**
1. Campainha: cada toque faz um bip.
2. Sinal de trânsito do robô: luz azul (pode ir), roxa (atenção), vermelha (pare), com esperas entre elas.
3. Uma musiquinha com `tocar` (dó = 262, ré = 294, mi = 330, fá = 349, sol = 392 Hz).

## Aula 7: medindo com sensores

**Exemplo:** `7_mostrar_sensor.py` · **Conceito:** observar dados antes de programar; escolher um limite.

**Comandos:** `mostrar(valor, linha=2)` (a tela tem 3 linhas), `esperar_luz(porta, '<', valor)`, `with se_luz(porta, '<', valor):`

**Roteiro**
- Os alunos anotam numa tabela o valor da luz refletida em cima do preto e em cima do branco.
- O limite para decidir é a média dos dois. Usem esse número num `se_luz`.

**Desafios**
1. Medir também o verde, o vermelho e o azul. Qual é fácil de separar do preto?
2. Fazer o robô parar quando chegar na faixa preta usando `esperar_luz`.

## Aula 8: variáveis

**Exemplo:** `8_contador.py` · **Conceito:** guardar um valor e mudá-lo durante o programa.

**Comandos:** `guardar(nome, valor)`, `ler(nome)`

**Desafios**
1. Cronômetro: mostrar os segundos passando na tela.
2. Contar quantas vezes o sensor de toque foi apertado.
3. Contar quantas linhas pretas o robô cruzou andando em frente.

---

## Ainda não conferido em todos os robôs

Já testados no robô: movimento, `andar_cm` e `virar_*` (o quadrado fecha certo), seguidor de
linha, tela (3 linhas), som, luz (azul, roxo, vermelho), esperar, ultrassom, `se(...)`,
`repetir_ate(...)`, variáveis e `cor_vista`. Ainda não visto funcionando: o sensor de toque (o
compilador gera para ele os mesmos bytes que a IDE oficial).
Teste antes de levar para a turma.

**Movimentos seguidos:** depois de cada movimento que freia (`andar`, `re`, `andar_cm`, `girar_*`,
`virar_*`), o robô fica parado meio segundo antes do próximo comando. Sem essa pausa ele emenda um
movimento no outro e as viradas saem erradas. Dá para mudar com `configurar(pausa=...)`.

**Sensor de cor:** cada sensor deve ser usado num modo só. Misturar comandos de cor (`cor_vista`, `se_ver_cor`) com
comandos de luz refletida (`luz_refletida`, `se_luz`) no mesmo sensor faz ele trocar de modo o tempo todo, ficar lento
e errar leituras; o programa mostra um aviso quando isso acontece. No modo cor, o branco às vezes aparece como 0
("nenhuma cor"): para linha preta no chão branco, a luz refletida é mais confiável.

**Bateria:** com a bateria fraca o robô mostra um aviso na tela, se desconecta do USB e deixa de
executar partes do programa. Se algo estranho acontecer, carregue o robô antes de procurar erro no
programa.
