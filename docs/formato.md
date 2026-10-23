# Formato do programa e protocolo do robô EST

Tudo aqui foi obtido por engenharia reversa e conferido contra programas compilados pela IDE
oficial (ver `gabaritos/`). Onde algo ainda é hipótese, está marcado.

## 1. Protocolo USB

- Dispositivo HID: **VID `0x0483`, PID `0x5750`** (aparece como "EST USB HS Mode").
- Cada envio é um *output report* de **1025 bytes**: byte 0 = report ID `0x00`, seguido do pacote.
- Pacote: `68 11 [CMD] [PAYLOAD...] [SOMA] 16`, onde `SOMA` = soma de todos os bytes anteriores, módulo 256.

| CMD | Payload | Função |
|---|---|---|
| `0x01` | `00 00` | heartbeat (a resposta traz a versão do firmware, ex. "03.04") |
| `0x02` | `01 00 00` | consulta de estado: o que está ligado em cada porta (a IDE manda sem parar) |
| `0x03` | `00 00` | consulta de memória (resposta de 4 bytes) |
| `0x04` | `len16 01 01 00 [tam_dir] [caminho.dbf]` | nome do arquivo de programa |
| `0x04` | `len16 02 [total] [n] [bytecode]` | conteúdo do programa, pedaço `n` de `total` |
| `0x0A` | `len16 01 [caminho.dbf]` | **executar** o programa gravado |
| `0x0A` | `len16 02 [caminho]` | selecionar (enviado antes do envio; função exata desconhecida) |
| `0x09` | `01 00 03` | listar os arquivos gravados (total, número, tamanho e caminho de cada um) |
| `0x09` | `len16 02 [/pasta/arquivo]` | apagar um arquivo (responde 1 se apagou) |
| `0x0C` | `01 00 01` | consulta a bateria (nível de 0 a 4). O envio manda antes e depois dos dados, como a IDE |

A resposta da consulta de estado (`0x02`) tem 8 grupos `[00, porta, tipo, ?]`, um por porta (1–4 sensores,
5–8 = A–D; porta 0 = nada ligado). Tipos vistos: 1 = sensor de cor, 4 = motor. A controladora **não**
manda as leituras dos sensores pelo USB: elas só aparecem na tela dela. Os comandos `0x09` e `0x0C`
foram descobertos na IDE; listar e apagar ainda não foram testados no robô.

`len16` é o comprimento (little-endian) do que vem depois dele. O caminho tem a forma
`/pasta/programa.dbf`; a pasta é criada pelo robô se não existir.

O programa vai em pedaços de até **1014 bytes** (o que cabe num report junto com os 10 bytes do
pacote), numerados a partir de 0, e todos levam o total de pedaços. Um programa pequeno vai num
pedaço só (`01 00`). Conferido contra a IDE: o BrickPID_v6 (8762 bytes) foi em 9 pedaços, e os
nossos saem iguais byte a byte.

Sequência usada por `est_protocol.py`: SELECT → heartbeat → DOWNLOAD → nome → dados (um pacote por
pedaço) → heartbeat → DOWNLOAD → **executar**. Sem o pacote de executar (`--so-gravar`), o programa
fica gravado e é iniciado pelo menu do robô.

## 2. Estrutura de um programa

```
tabela de constantes   8 x  02 [reg] [valor]     0.0 1.0 2.0 3.0 4.0 5.0 (float) e 1, 2 (inteiro)
entradas com fio       N x  02 [reg] FF FF FF FF  uma por parâmetro alimentado por fio
thread principal       blocos da cadeia principal ... 24
thread 1               corpo do primeiro loop / ramo de switch ... 21 01 00
thread 2               ...                                      ... 21 02 00
```

- **Registradores** são posições de memória. Nas instruções, endereços vão em 4 bytes
  **big-endian**; valores float vão em 4 bytes **little-endian**.
- As constantes ficam nos registradores logo depois dos de todos os blocos (ids internos 100–107).
- **Ordem única**: a IDE aloca registradores e gera código na mesma ordem: a cadeia principal
  inteira e depois cada thread, na ordem em que foram numeradas (em largura).
- Todo bloco começa com o marcador `48`, seguido das inicializações dos seus parâmetros, dos passos
  do bloco e das cópias para os blocos ligados por fio.

## 3. Instruções conhecidas

| Op | Bytes | Formato | Significado |
|---|---|---|---|
| `01` | 6 | `01 [r] [byte]` | r = byte |
| `02` | 9 | `02 [r] [f32]` | r = float (ou inteiro de 32 bits, ou endereço de texto) |
| `03` | 9 | `03 [dest] [orig]` | copia 1 byte (valores lógicos) |
| `04` | 9 | `04 [dest] [orig]` | copia 4 bytes |
| `08` | 9 | `08 [dest] [orig]` | dest = float(byte orig) |
| `09` `0A` `0B` `0C` | 13 | `op [res] [a] [b]` | res = a + b, a − b, a × b, a ÷ b |
| `0D` | 10 | `0D 15 [r] [r]` | converte a cor lida para o número da cor (usado antes de exportar a leitura) |
| `10` | 14 | `10 [tipo] [res] [a] [b]` | compara floats; tipo 1 =, 2 ≠, 3 >, 4 ≥, 5 <, 6 ≤ |
| `11` | 13 | `11 [res] [leitura] [máscara]` | cor lida pertence ao conjunto da máscara |
| `29` | 14 | `29 [tipo] [res] [a] [b]` | compara bytes (sensor de toque) |
| `2B` | 17 | `2B [r_tipo] [res] [a] [b]` | compara floats com o tipo num registrador (0 =, 1 ≠, 2 >, 3 ≥, 4 <, 5 ≤) |
| `2F` | 6+n | `2F [endereço] [n] [bytes]` | grava texto na área de textos |
| `33` | 8 | `33 [tipo] [modo] [tam] [r_dados]` | escreve num dispositivo interno (tela, som, luz) |
| `47` | 9 | `47 [endereço_texto] [r]` | converte um número em texto |
| `1A` | 9 | `1A [pc] [r]` | salta para pc se r ≠ 0 |
| `1B` | 9 | `1B [pc] [r]` | salta para pc se r = 0 |
| `1D` | 7 | `1D [pc] [tid] 00` | inicia a thread tid em pc |
| `1E` / `1F` | 11 | `op [pc] [r] [tid] 00` | inicia a thread tid se r for verdadeiro / falso |
| `20` | 3 | `20 [tid] 00` | espera a thread tid terminar |
| `21` | 3 | `21 [tid] 00` | fim da thread tid |
| `23` | 5 | `23 [r]` | espera r segundos |
| `24` | 1 | `24` | fim da thread principal |
| `2D` | 7 | `2D [r] [u16]` | r = valor de 16 bits (máscara de cores) |
| `30` | 13 | `30 00 [r_porta] [tipo] [modo] [tam] [r_dados]` | **lê** um dispositivo |
| `31` | 13 | `31 00 [r_porta] [tipo] [modo] [tam] [r_dados]` | **escreve** em um dispositivo |
| `48` | 1 | `48` | marcador de início de bloco |

`pc` é a posição absoluta (em bytes, desde o início do programa).

O `InstructionSet.xml` da IDE erra o tamanho de algumas instruções (`2D`, `20`, `21`, `37`), e a IDE
traduz alguns opcodes dos modelos `compile_xml` antes de gravar (o "comparar" `0x37` vira `0x10`, o
"multiplicar" `0x0C` vira `0x0B`). A tabela acima é a do bytecode real.

### Dispositivos (`30`/`31`)

| tipo | dispositivo | modos e tamanho dos dados |
|---|---|---|
| `0x01` | sensor de cor | 1 = cor (1–2 bytes), 2 = luz refletida, 3 = ambiente (4 bytes, um float) |
| `0x07` | sensor de toque | 1 = estado (1 byte: 0 solto, 1 apertado) |
| `0x08` | sensor ultrassônico | 3 = distância em cm (4 bytes) |
| `0x80` | motor médio | como o grande |
| `0x81` | motor grande | 1 desligar (1 B), 2 ligar (4 B), 3 segundos, 4 graus, 5 rotações (9 B) |
| `0x82` | mover com direção | 1 (1 B), 2 (8 B), 3–5 (13 B) |
| `0x83` | mover tanque | 1 desligar (1 B), 2 ligar (8 B), 3 segundos, 4 graus, 5 rotações (13 B) |

Os dados começam em `r_dados`: potência(s) em float, depois o valor do modo (segundos, graus ou
rotações) em float e por fim o freio em 1 byte (1 = frear). No "mover com direção" a direção vem
antes da potência.

### Dispositivos internos (`33`)

| tipo | dispositivo | dados |
|---|---|---|
| 1 | tela, modo 1 = texto | 10 bytes: endereço do texto (4), 1 reservado, limpar, x, y, cor, fonte |
| 2 | som, modo 1 = tom | 13 bytes: frequência, duração, volume (floats) e tipo de reprodução |
| 4 | luz do bloco | modo 1 = ligar (cor, piscar); modo 0 = desligar (`33 04 00 00 FFFFFFFF`) |

Textos ficam numa área separada, a partir de `0xD7FF`, numa vaga de 50 bytes por parâmetro de
texto. O bloco grava o texto com `2F` e põe o endereço da vaga no seu registrador.

### Porta (byte gravado no registrador de porta)

| Porta | Byte |
|---|---|
| sensores `1`–`4` | 1–4 |
| motores `A`–`D` | 5–8 |
| par de motores `X+Y` | `f(X)<<4 + f(Y)<<6`, com A=0, B=1, C=2, D=3 (`B+C` = `0x90`) |

**Cores** vão como máscara de bits `1 << cor`: preto = 1 → `0x0002`, verde = 3 → `0x0008`,
branco = 6 → `0x0040`. Um conjunto de cores soma as máscaras.

## 4. Exemplos de blocos

Mover tanque B+C, 50/50, 1 rotação:
```
48
01 [rP] 90                    porta B+C
02 [rD] 50.0                  potência esquerda
02 [rD+4] 50.0                potência direita
02 [rD+8] 1.0                 rotações
01 [rD+12] 01                 frear
31 00 [rP] 83 05 0D [rD]
```

Switch de cor (S1 vê preto?):
```
48
01 [r0] 01                    porta 1
2D [r1] 02 00                 máscara de preto
30 00 [r0] 01 01 04 [r3]      lê a cor
11 [r7] [r3] [r1]             r7 = cor está na máscara
1F [pc_nao] [r7] [tid_nao] 00
1E [pc_sim] [r7] [tid_sim] 00
20 [tid_sim] 00
20 [tid_nao] 00
```

Loop por contagem:
```
48
02 [contador] 0.0
01 [flag] 00
L: 1D [pc_corpo] [tid] 00
   20 [tid] 00
   02 [N] 3.0
   09 [contador] [contador] [const 1.0]
   10 04 [cond] [contador] [N]
   1A [fim] [flag]
   1B [L] [cond]
   0A [contador] [contador] [const 1.0]
fim:
```

**Fios**: o bloco de origem termina com uma cópia para o registrador do parâmetro de destino, uma
por destino. A instrução depende dos tipos: `04` (número → número), `03` (lógico → lógico), `08`
(byte → número) ou `47` (número → texto, gravando na vaga de texto). Parâmetros ligados por fio não
são inicializados no bloco. Os numéricos começam com `FF FF FF FF` na tabela do início; os de texto,
com `2F [vaga] 03 0D 0D 00`.

**Esperar por sensor**: o bloco lê, compara e volta à leitura com `1B` enquanto a condição for falsa.
```
48
01 [r0] 01                     porta
01 [r8] 04                     tipo de comparação (4 = "<")
02 [r6] 30.0                   limite
L: 30 00 [r0] 01 02 04 [r4]    lê a luz refletida
   2B [r8] [r43] [r4] [r6]     r43 = leitura < limite
   1B [L] [r43]                volta enquanto falso
```

**Variáveis** têm um registrador por nome, compartilhado por todos os blocos. "Ler" copia dele para o
destino do fio; "escrever valor fixo" grava direto nele (`02`); "escrever" ligada por fio usa um
registrador intermediário e copia (`04`).

**Loops** com o mesmo nome (o padrão é `01`) usam o mesmo registrador de interrupção: o do primeiro
loop. Os outros reservam o seu, mas não o usam.

## 5. Como acrescentar um bloco novo

1. Monte um programa mínimo com o bloco na IDE oficial, envie ao robô e feche a IDE.
2. Copie o `order_content.txt` da pasta da IDE (ela só termina de gravá-lo ao fechar).
3. Rode `python ferramentas/decodificar.py order_content.txt` para ver as instruções.
4. Crie o modelo do bloco em `estc.MODELOS` e a função em `blocos.py`.
5. Salve o programa da IDE em `gabaritos/` e acrescente o teste em `verificar_gabaritos.py`.
   O compilador só está certo quando o teste mostra os bytes idênticos.
