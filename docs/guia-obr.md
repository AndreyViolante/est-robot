# Programa de OBR: como organizar

Guia para equipes que vão para a prova prática da OBR (Robótica de Resgate) programando a controladora
EST em Python. Ele não traz a solução da prova: mostra como **organizar, testar e ajustar** o programa
que a equipe escreve. Na OBR o robô é planejado, construído e programado pelos estudantes.

As regras mudam a cada ano: confira sempre o
[manual de regras da OBR](https://obr.robocup.org.br/documentos-e-manuais/) do ano da prova. Os números
abaixo são do manual de 2026 (etapa regional/estadual).

## O que vale ponto no percurso com linha

| Perigo | Pontos |
|---|---|
| Gap (falha na linha, até 10 cm no nível 1 e 15 cm no nível 2) | 10 por ladrilho |
| Obstáculo (desviar e voltar para a linha) | 20 |
| Interseção (com verde: vira para o lado dele; sem verde: segue reto) | 10 |
| Beco sem saída (dois verdes antes: meia-volta) | 10 |
| Rampa, lombada | 10 por ladrilho |
| Gangorra | 20 |
| Ladrilhos até cada checkpoint | 5, 3 ou 1 por ladrilho (1ª, 2ª ou 3ª tentativa) |
| Chegada (parar 5 s na faixa vermelha) | 60 menos 5 por falha de progresso |

A **falha de progresso** (perder a linha, ficar 10 s parado, pegar o caminho errado) leva o robô de volta
ao último checkpoint e **recomeça o programa do início**. Por isso o programa precisa funcionar bem
começando de qualquer checkpoint, e não só do ladrilho de partida.

## 1. Antes de programar: medir

- **Ver sensores na tela do robô** (tarefa do VS Code): anote a luz refletida no preto, no branco e no
  verde de cada sensor.
- **`calibrar_na_largada(1, 2)`**: o robô mede o preto e o branco na própria pista antes de sair. A luz do
  ginásio nunca é a do laboratório; use `limite_medido(1)` no lugar de um número fixo.
- **Um modo por sensor**: na controladora EST, usar o mesmo sensor em cor e em luz refletida deixa ele
  lento e errando (o programa avisa). Decida antes: quais sensores seguem a linha (luz refletida) e qual
  procura o verde (cor).

## 2. Cada parte da prova numa função

Um programa de OBR cresce rápido. Separar cada parte numa função com nome claro ajuda a testar uma coisa
de cada vez e a achar o erro na hora da prova:

```python
from robo import *

# ---- números para ajustar na arena (ou com ajustes(...), sem cabo)
VEL = 25
KP = 0.4


# ---- cada parte da prova numa função: teste uma de cada vez
def seguir_linha():
    """Um passo do seguidor: lê os sensores e corrige os motores (sem laço aqui dentro)."""
    erro = luz_refletida(1) - luz_refletida(2)
    motores(VEL + erro * KP, VEL - erro * KP)


def viu_obstaculo():
    return distancia(4) < 10


def viu_verde():
    return cor_vista(3) == VERDE


def desviar_obstaculo():
    parar()
    bip()                 # a sua equipe escreve o desvio aqui


def tratar_verde():
    parar()
    bip()                 # e aqui o que fazer no verde


# ---- o programa: calibra e repete o laço principal
calibrar_na_largada(1, 2)
while True:
    if viu_obstaculo():
        desviar_obstaculo()
    elif viu_verde():
        tratar_verde()
    else:
        seguir_linha()
```

- **O laço principal só decide**: ele olha os sensores e chama a função certa. Cada função faz uma coisa.
- **A ordem dos `if` é a prioridade**: o que vem primeiro ganha. Pense no que é mais urgente (bater na
  caixa? perder o verde?).
- **Cuidado com o tamanho**: no EST-ROBOT, cada vez que uma função é chamada, os blocos dela entram de
  novo no programa (é como copiar e colar). Chame cada função em um lugar só, de preferência dentro do
  laço principal.

## 3. Confirmar antes de agir

Uma leitura só engana: a borda da linha, uma sujeira ou o reflexo da luz parecem verde ou preto por um
instante. Antes de uma decisão grande (virar no verde, começar o desvio), confirme:

- leia de novo depois de um pequeno avanço;
- ou conte quantas vezes seguidas o sensor viu a mesma coisa (`guardar('vezes', ...)` e `ler('vezes')`) e
  só aja depois de algumas.

No simulador, ligue **Sensores com ruído** para ver se a decisão aguenta leituras que variam.

## 4. Mostrar o que o robô está pensando

Durante os testes, faça cada função acender uma cor de luz (`luz('azul')`, `luz('roxo')`,
`luz('vermelho')`) ou dar um `bip()`. Na arena, dá para ver na hora em que parte do programa o robô
estava quando errou. O `painel(...)` mostra até 3 números na tela, como o erro do seguidor.

## 5. Velocidade: medir antes de mexer

- **`with medir_laco(5):`** com o corpo do seu laço dentro mostra quantas voltas por segundo ele faz.
  Mais voltas = o robô corrige mais vezes e pode andar mais rápido sem perder a linha.
- Tire ou ponha uma leitura, um `mostrar(...)`, uma conta, e meça de novo: descubra o que custa caro.
- **`with ajustes(kp=(0.4, 0.05), vel=(25, 5)):`** muda os números pelos botões da controladora entre uma
  rodada e outra, sem cabo. Anote os que funcionaram e passe para o programa.

## 6. Testar uma parte de cada vez

1. Um programa só com o `seguir_linha()` no laço: reta, curvas, curva de 90°.
2. Depois o gap, depois o verde, depois o obstáculo: cada um num programa de teste pequeno.
3. Só então junte tudo no laço principal.

No simulador, a **Arena da OBR** monta o percurso com ladrilhos de 30 cm e conta os pontos como a súmula:
use as arenas prontas ou monte a sua em "Minha arena OBR" com os perigos que a equipe quer treinar. O
simulador não tem escorregão, bateria fraca nem a luz do ginásio: o teste final é sempre no robô.

## 7. No dia da prova

- [ ] Bateria cheia (com bateria fraca o robô se desconecta e erra leituras).
- [ ] IDE EST fechada no computador que envia.
- [ ] Programa gravado no robô (**Gravar no robô sem executar**) e uma cópia do `.py` num pendrive.
- [ ] `calibrar_na_largada` no começo do programa (ou o preto e o branco da arena medidos no `calibracao.py`).
- [ ] Os números do `ajustes` anotados na folha da equipe.
- [ ] Cada membro sabe o que cada função faz: no desafio surpresa, a equipe tem 30 minutos para mudar o programa.

Encontrou um problema no EST-ROBOT? A tarefa **Diagnóstico (para pedir ajuda)** copia um resumo para
mandar junto com o que aconteceu.
