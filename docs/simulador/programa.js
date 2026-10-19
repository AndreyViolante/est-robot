// Gerado por simular.py: os programas compilados (os mesmos bytes que vão para o robô).
window.PROGRAMAS = [
 {
  "nome": "11_seguidor_dois_sensores.py",
  "bytes": "020000003d0000000002000000410000803f020000004500000040020000004900004040020000004d0000804002000000510000a040020000005501000000020000005902000000480200000000000000000100000008001d000000950100200100090000000000000000000000410100000004001a00000094000000081b00000058000000040a0000000000000000000000412448010000000c012d0000000d020030000000000c0101040000000f11000000130000000f0000000d1f000001050000001303001e000000dc000000130200200200200300210100480100000017900200000018000070c1020000001c0000f04131000000001783020800000018210200480100000020022d00000021020030000000002001010400000023110000002700000023000000211f000001750000002705001e0000014c00000027040020040020050021030048010000002b90020000002c0000f0410200000030000070c131000000002b8302080000002c2104004801000000349002000000350000f04102000000390000f04131000000003483020800000035210500",
  "fonte": "from robo import *\n\n# Seguidor de linha b\u00e1sico com dois sensores: S1 \u00e0 esquerda e S2 \u00e0 direita da linha preta.\n#   S1 viu preto: a linha foi para a esquerda, vira para a esquerda.\n#   Sen\u00e3o, S2 viu preto: a linha foi para a direita, vira para a direita.\n#   Sen\u00e3o (os dois no branco): a linha est\u00e1 no meio, anda reto.\n# Na virada a roda de dentro anda um pouco de r\u00e9: assim ele faz at\u00e9 a curva de 90 graus.\n\nRETO = 30            # pot\u00eancia dos dois motores na reta\nFORA = 30            # roda de fora da curva\nDENTRO = -15         # roda de dentro da curva (negativo = de r\u00e9)\n\nwith para_sempre():\n    with se_ver_cor(1, PRETO):\n        motores(DENTRO, FORA)           # vira para a esquerda\n    with senao():\n        with se_ver_cor(2, PRETO):\n            motores(FORA, DENTRO)       # vira para a direita\n        with senao():\n            motores(RETO, RETO)         # anda reto\n",
  "linhas": [
   13,
   14,
   15,
   17,
   18,
   20
  ],
  "variaveis": {},
  "avisos": [],
  "titulo": "Seguidor b\u00e1sico com dois sensores",
  "pista": "quadrado",
  "inicial": true
 }
];
