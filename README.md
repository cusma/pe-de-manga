# Pé de Manga NFT 🥭

[VÍDEO AULA (em Português)](https://www.youtube.com/watch?v=Wl2JDXudGrM) - Programação Algorand Smart Contracts em Python! 🐍

Assista a explicação passo-a-passo do exemplo Pé de Manga NFT 🥭 na vídeo aula!

## Prerequisitos

- [Docker](https://www.docker.com/)
- [Algorand Sandbox](https://github.com/algorand/sandbox)
- [poetry](https://python-poetry.org/)
- [pre-commit](https://pre-commit.com/)

1. Clonar o repositório

```bash
git clone https://github.com/cusma/pe-de-manga
```

2. Instale os requisitos do Python

```bash
poetry install # instale todas as dependências
poetry shell # active o virtual env
```

## Pé de Manga NFT 🥭 na MainNet
Um pé de manga já foi plantado na MainNet:

`<pe-de-manga-id>`: [570610614](https://algoexplorer.io/application/570610614)

## CLI

⚠️ Mantenha seu `<mnemonic>` seguro! Embora você só vá usá-lo em sua máquina
local, é altamente recomendável fazer uso de uma conta dedicada apenas para
jogar com o Pé de Manga NFT 🥭!

```bash
$ python3 pe_de_manga.py -h

Pé de manga NFT 🥭 (by cusma)
Plante e regue um pé de manga, grite oxê e colhe sua deliciosa manga NFT!

Usage:
  pe_de_manga.py plantar <mnemonic>
  pe_de_manga.py regar <mnemonic> <pe-de-manga-id>
  pe_de_manga.py colher <mnemonic> <pe-de-manga-id> <palavra>
  pe_de_manga.py [--help]

Commands:
  plantar    Plante um novo pé de manga.
  regar      Regue o pé de manga para deixar a manga crescer.
  colher     Diga a palavra certa e tire a manga do pé.

Options:
  -h --help
```
