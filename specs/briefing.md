# Sobre
Solução para monitoramento de novos posts e scrapping destes posts periodicamente para apresentação resumida e facilitada.

# Estrutura
Conjunto de arquivos de configuração com os seguintes itens:
- periodicidade de varredura
- lista de urls
- lista de categorias
- credenciais
Conjunto de scripts que, direcionados pelos arquivos de configuração, fazem acesso web e scrapping das urls selecionadas, filtrando por data de acordo com a estrutura de cada blog, e armazenando os resultados textuais em memória local. Uma segunda etapa de comunicação com LLM permite a estruturação dos posts, resumindo-os e atrelando categorias.
O resultado é uma segunda memória estruturada com o resumo das publicações, para envio via e-mail ou outro canal adequado de notificações.

# Ferramentas
- Código em python
- Github Copilot CLI para o LLM
- Módulo do beautifulsoup para scrapping
- Arquivos de configuração em JSON
- Outlook para envio de e-mails
- Github para armazenamento remoto
- Github Actions como CI para validação
- VSCode com Github Copilot para desenvolvimento

# Organização do Projeto
- workspace
	- github
		- (arquivos de ci)
	- configs
		- urls.json
		- config.json
	- scripts
		- scrapping.py
		- processing.py
		- load_configs.py
		- send_email.py
	- main.py
	- README.md
# Especificações
## TechBlogs Alvo
- Uber
- Meta
- Google Developers
- Google Cloud
- Microsoft
- AWS
- OpenAI
- Anthropic
- Github
- Netflix
## Configurações Básicas
- Frequência de varredura: 1 semana
- Categorias:
	- Dados e IA
	- Engenharia de Software
	- Infraestrutura e Cloud
	- Segurança
	- UX e Design
	- Negócios e Inovação
# Direcionamentos Importantes
- Fazer scrapping de posts por data (identificando os seletores de cada blog), apesar de frágil, é mais eficiente do que deixar todo o processamento dentro da LLM, pois isso gastaria muitos tokens.
# Gaps a Resolver
- Outlook é a ferramenta onde quero receber emails, mas é a mais adequada para a solução enviar os emails? Ela é pessoal e poderia usar minha própria conta.
- Consigo aplicar token ou credenciais em .env para acionar a LLM do Github Copilot CLI?

# TO-DO
- [ ] Listagem de urls (IA pode identificar a URL exata).
- [ ] Definição dos parâmetros de configuração.
- [ ] Mapeamento dos seletores e estrutura HTML de cada blog para construção do scrapper (IA pode consultar as URLs).
- [ ] Construção do script de scrapper.
- [ ] Construção do script de carregamento de configurações.
- [ ] Aplicação das credenciais.
- [ ] Construção do script de processamento com LLM.
- [ ] Definição do melhor meio de envio de e-mails.
- [ ] Construção do layout de e-mail (html estilizado).
- [ ] Construção do script de envio de e-mails.
- [ ] Construção do script principal, que encadeia os demais.
- [ ] Construção de um CI básico de validação.
- [ ] Publicação no github.
- [ ] Aplicação de eventuais configurações no github.
- [ ] Teste fim a fim.
- [ ] Agendamento da execução da solução.