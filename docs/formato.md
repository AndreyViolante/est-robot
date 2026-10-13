# Formato do programa e protocolo do robô EST

Tudo aqui foi obtido por engenharia reversa e conferido contra programas compilados pela IDE
oficial (ver `gabaritos/`). Onde algo ainda é hipótese, está marcado.

## 1. Protocolo USB

- Dispositivo HID: **VID `0x0483`, PID `0x5750`** (aparece como "EST USB HS Mode").
- Cada envio é um *output report* de **1025 bytes**: byte 0 = report ID `0x00`, seguido do pacote.
- Pacote: `68 11 [CMD] [PAYLOAD...] [SOMA] 16`, onde `SOMA` = soma de todos os bytes anteriores, módulo 256.

| CMD | Payload | Função |
|---|---|---|
| `0x01` | `00 00` | heartbeat |
| `0x02` | `01 00 00` | consulta de estado (a IDE manda sem parar) |
| `0x04` | `len16 01 01 00 [tam_dir] [caminho.dbf]` | nome do arquivo de programa |
| `0x04` | `len16 02 01 00 [bytecode]` | conteúdo do programa |
| `0x0A` | `len16 01 [caminho.dbf]` | **executar** o programa gravado |
| `0x0A` | `len16 02 [caminho]` | selecionar (enviado antes do download; função exata desconhecida) |
| `0x0C` | `01 00 01` | iniciar/confirmar download |

`len16` é o comprimento (little-endian) do que vem depois dele. O caminho tem a forma
`/pasta/programa.dbf`; a pasta é criada pelo robô se não existir.

Sequência usada por `est_protocol.py`: SELECT → heartbeat → DOWNLOAD → nome → dados → heartbeat →
DOWNLOAD → **executar**.

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
| `02` | 9 | `02 [r] [f32]` | r = float (ou inteiro de 32 bits) |
| `04` | 9 | `04 [dest] [orig]` | copia 4 bytes |
| `09` `0A` `0B` `0C` | 13 | `op [res] [a] [b]` | res = a + b, a − b, a × b, a ÷ b |
| `10` | 14 | `10 [tipo] [res] [a] [b]` | comparação (tipo 4 usado no loop por contagem) |
| `11` | 13 | `11 [res] [leitura] [máscara]` | cor lida pertence ao conjunto da máscara |
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
| `0x01` | sensor de cor | 1 = cor, 2 = luz refletida, 3 = ambiente; 4 bytes (um float) |
| `0x80` | motor médio | como o grande |
| `0x81` | motor grande | 1 desligar (1 B), 2 ligar (4 B), 3 segundos, 4 graus, 5 rotações (9 B) |
| `0x82` | mover com direção | 1 (1 B), 2 (8 B), 3–5 (13 B) |
| `0x83` | mover tanque | 1 desligar (1 B), 2 ligar (8 B), 3 segundos, 4 graus, 5 rotações (13 B) |

Os dados começam em `r_dados`: potência(s) em float, depois o valor do modo (segundos, graus ou
rotações) em float e por fim o freio em 1 byte (1 = frear).

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

**Fios**: o bloco de origem termina com `04 [registrador do parâmetro de destino] [sua saída]`, uma
cópia por destino. Parâmetros ligados por fio não são inicializados no bloco; começam com
`FF FF FF FF` na tabela do início.

## 5. Como acrescentar um bloco novo

1. Monte um programa mínimo com o bloco na IDE oficial, envie ao robô e feche a IDE.
2. Copie o `order_content.txt` da pasta da IDE (ela só termina de gravá-lo ao fechar).
3. Rode `python ferramentas/decodificar.py order_content.txt` para ver as instruções.
4. Crie o modelo do bloco em `estc.MODELOS` e a função em `blocos.py`.
5. Salve o programa da IDE em `gabaritos/` e acrescente o teste em `verificar_gabaritos.py`.
   O compilador só está certo quando o teste mostra os bytes idênticos.
