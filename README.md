# Agregador de TechBlogs

Aplicacao Python que coleta publicacoes recentes de blogs de tecnologia, resume e categoriza o conteudo usando o GitHub Copilot CLI e envia uma compilacao por e-mail.

## Requisitos

- Python 3.11 ou superior.
- Acesso aos sites configurados.
- GitHub Copilot CLI instalado e autenticado para resumir publicacoes.
- Conta/servico SMTP habilitado para envio de e-mail. A configuracao inicial usa o endpoint SMTP do Microsoft 365; SMTP AUTH pode precisar ser habilitado pelo administrador da conta.

## Instalacao

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Defina `SMTP_USER`, `SMTP_PASSWORD` e `SMTP_FROM` no `.env`, e configure o destinatario em `configs/config.json` (`email.recipient`) ou por `EMAIL_TO`. Nunca versione o arquivo `.env` nem credenciais.

O comando do modelo e seus argumentos ficam em `configs/config.json`. A configuracao inicial chama `copilot -p "{prompt}"`; confirme que a versao instalada oferece modo nao interativo e que a autenticacao funciona no ambiente agendado antes de habilitar execucoes automaticas.

## Execucao

```powershell
python main.py
```

O banco SQLite e criado em `data/techblogs.sqlite3`. Publicacoes com falhas de processamento ou envio permanecem pendentes para tentativa posterior. O comando termina com codigo diferente de zero quando uma fonte ou etapa falha.

Para coletar e processar sem enviar e-mail:

```powershell
python main.py --dry-run
```

O primeiro processamento ainda chama o Copilot CLI. O modo de teste apenas evita o envio SMTP.

## Configuracao das fontes

`configs/urls.json` lista as dez fontes. Cada fonte tem seletores CSS (`article_selector`, `title_selector`, `link_selector`, `date_selector`, `content_selector`) e campos opcionais:

- `type`: `html` (padrao) ou `feed` (RSS/Atom; usa o conteudo do feed e, se curto, a pagina do post).
- `page_param` / `max_pages`: pagina feeds com `?paged=N` ate sair da janela de datas ou atingir `max_pages`.
- `next_page_selector` ou `page_url_template` (ex.: `https://site/page/{page}/`): pagina listagens HTML, substituindo botoes "carregar mais".
- `feed_urls`: feeds adicionais da mesma fonte (deduplicados por URL).
- `date_from_article`: busca a data na pagina do post (`article:published_time`, JSON-LD ou `<time>`) quando a listagem nao a traz.

Datas textuais ("Oct 22, 2026") sao reconhecidas e tratadas como UTC. Posts sem data reconhecivel ou conteudo nao sao incluidos. A coleta por HTML pode ser afetada por mudancas no site, bloqueios (alguns posts, como os do OpenAI, respondem 403 e usam o resumo do feed) e conteudo renderizado por JavaScript.

`configs/config.json` controla a frequencia (janela de posts em dias), limites de coleta, caminho do banco local, categorias, SMTP e comando do LLM. A frequencia define a janela analisada em cada execucao; o agendamento semanal deve ser configurado no ambiente que hospeda a aplicacao.

## Validacao

```powershell
python -m pytest
python -m ruff check .
```

O workflow em `.github/workflows/ci.yml` executa os mesmos testes e lint em push e pull request.

