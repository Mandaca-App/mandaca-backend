# Mandaca-backend

API do **Mandacá** — backend responsável pelo gerenciamento dos dados e regras do projeto.

## Visão geral

Este repositório contém a API do Mandacá: endpoints REST/HTTP para autenticação, CRUD de recursos do sistema, integrações e lógica de negócio. É pensado para ser leve, testável e fácil de evoluir.

## Stack

* Linguagem: **Python**
* Framework da API: **FastAPI**
* Banco de dados: usamos Supabase (Postgres gerenciado)
* Orquestração e outras dependências: arquivos de configuração

## Recursos principais

* Endpoints organizados por módulos (auth, users, items, etc.)
* Validação automática de dados
* Documentação automática (OpenAPI / Swagger) via FastAPI
* Migrações de banco 
* Testes unitários e de integração

## Pré-requisitos

* Python 3.10+ instalado
* pip e venv (ou alternativa) configurados
* Conta/configuração do banco

## Instalação rápida

1. Clone o repositório
   `git clone <repo-url> && cd mandaca-backend`

2. Crie e ative um ambiente virtual
   Linux / macOS:
   `python -m venv .venv && source .venv/bin/activate`
   Windows (PowerShell):
   `python -m venv .venv; .\.venv\Scripts\Activate.ps1`

3. Instale dependências
   `pip install -r requirements.txt`

## Boas práticas

* Separe responsabilidades por módulos (routers, services, repositories)
* Use Pydantic para validação e esquemas de resposta
* Não exponha chaves sensíveis no repositório; utilize variáveis de ambiente ou um vault
* Proteja endpoints com autenticação e controle de acesso

## Contribuição

1. Abra uma issue descrevendo a mudança.
2. Crie uma branch com `feature/` ou `fix/`.
3. Abra o PR com descrição clara e referência à issue.
4. Adicione testes para novas funcionalidades / correções.

---

## Swagger / OpenAPI

Com o backend rodando, a documentacao interativa fica disponivel em:

* Swagger UI: `http://localhost:8000/api-docs`
* OpenAPI JSON: `http://localhost:8000/api-docs/openapi.json`

A documentacao e gerada automaticamente pelo FastAPI. Sempre que um endpoint novo
ou parametro novo for criado no codigo, ele aparece no Swagger sem edicao manual.


