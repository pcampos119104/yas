# Projeto: Organizador de Exercícios de Balé com IA

## Objetivo

Desenvolver uma aplicação em Python que utiliza inteligência artificial para transformar narrações de professores de balé clássico em sequências estruturadas de exercícios.

A professora poderá narrar livremente um exercício, descrevendo movimentos, posições, repetições, direções, movimentos dos braços e contagens musicais.

O sistema deverá interpretar essa narração e produzir uma ficha organizada para que os alunos possam revisar e memorizar os exercícios aprendidos presencialmente.

**O objetivo não é ensinar a técnica de balé, mas registrar fielmente as sequências ensinadas pela professora.**

## Funcionamento esperado

O fluxo principal será:

1. Receber um arquivo de áudio contendo a narração da professora.
2. Transcrever o áudio para texto.
3. Utilizar um LLM através do LangChain para interpretar a narração.
4. Transformar os movimentos identificados em dados estruturados, validados com Pydantic.
5. Gerar uma ficha de exercícios em Markdown e um arquivo JSON.
6. Preservar a transcrição original para conferência.

Exemplo de execução futura:

```bash
uv run python main.py aula.ogg
```

Arquivos gerados:

```text
output/
├── transcricao.txt
├── aula.json
└── aula.md
```

## Interpretação dos movimentos

O principal desafio é interpretar corretamente a sequência coreográfica, incluindo movimentos simultâneos de diferentes partes do corpo.

Por exemplo, a professora pode narrar:

"Faz dois demi-pliés. No primeiro, traz os braços para primeira posição e, no segundo, abre para segunda."

O sistema deve identificar:

- Primeiro demi-plié: braços movimentam-se para primeira posição.
- Segundo demi-plié: braços movimentam-se para segunda posição.

Isso é diferente de realizar dois demi-pliés mantendo os braços em segunda posição ou de fechar e abrir os braços durante cada repetição.

### Modelo conceitual

A representação dos exercícios será baseada em uma estrutura de movimentos e eventos temporais, inspirada em princípios de notação de dança, como Labanotation e Benesh Movement Notation.

Não pretendemos implementar essas notações formais.

O modelo deverá permitir representar:

- Exercícios e movimentos.
- Repetições.
- Posições e direções.
- Ações independentes de pernas, braços, cabeça e tronco.
- Movimentos simultâneos ou sequenciais.
- Contagens musicais, quando informadas.
- Transições entre posições.

A estrutura exata dos modelos Pydantic será definida gradualmente, conforme os casos de uso forem implementados.

### Tratamento de ambiguidades

O LLM não deve inventar movimentos, posições, repetições ou contagens que não foram informados.

Quando uma narração permitir múltiplas interpretações, o sistema deverá preservar a incerteza em vez de escolher arbitrariamente uma delas.

Futuramente, essas ambiguidades poderão ser apresentadas à professora para esclarecimento.

## Stack tecnológica

- Python com uv para gerenciamento do projeto.
- LangChain para integração com os LLMs.
- OpenRouter como provedor inicial.
- Pydantic para Structured Output.
- LangSmith para tracing e avaliações.
- Ferramenta de Speech-to-Text a definir, possivelmente Whisper.
- pytest para testes.

## Estratégia de desenvolvimento

O desenvolvimento será incremental, implementando e testando uma funcionalidade de cada vez.

A primeira versão será exclusivamente uma aplicação de linha de comando (CLI).

Não utilizar inicialmente:

- Django ou outro framework web.
- Banco de dados.
- LangGraph.
- RAG ou banco vetorial.
- Interface gráfica.
- Sistemas multiagentes.

O projeto não precisa ser um agente autônomo. Inicialmente, um pipeline de processamento com LangChain é suficiente.

## Situação atual

O projeto Python já foi inicializado e existe uma implementação básica que realiza uma chamada a um LLM usando LangChain.

Essa implementação é o ponto de partida.

Não recriar o projeto nem substituir sua configuração atual sem necessidade.

## Orientações para o desenvolvimento

- Implementar apenas a funcionalidade solicitada em cada etapa.
- Não antecipar funcionalidades futuras.
- Manter a arquitetura simples, modular e testável.
- Utilizar recursos atuais do LangChain, evitando APIs obsoletas.
- Separar interpretação por IA de processamento determinístico em Python.
- Preferir Structured Output com Pydantic em vez de gerar JSON manualmente por prompt.
- Preservar os dados originais para depuração e avaliação.
- Priorizar fidelidade à narração em vez de completar informações ausentes.

**Importante: este documento descreve o contexto e a direção do projeto. Não é uma solicitação para implementar todas as funcionalidades agora. Aguarde instruções específicas para cada etapa.**
