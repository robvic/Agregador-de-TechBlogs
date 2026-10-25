# Especificação: Monitoramento de TechBlogs

**Data**: 2026-10-25  
**Origem**: [briefing.md](../briefing.md)

## Resumo

Monitorar periodicamente publicações recentes de blogs de tecnologia, coletar o conteúdo textual, produzir resumos classificados por categoria e enviar uma compilação por e-mail. A primeira versão atende dez fontes e executa uma varredura semanal.

## Objetivos

- Reunir publicações recentes de fontes de tecnologia em uma única compilação.
- Reduzir leitura manual com resumos claros e categorias consistentes.
- Evitar processar novamente publicações já coletadas.
- Permitir atualizar fontes e configurações sem alterar o fluxo principal.

## Fora de escopo

- Interface web ou aplicativo para leitura.
- Publicação automática em redes sociais ou outros canais além de e-mail.
- Monitoramento em tempo real.
- Cobertura garantida de alterações no HTML ou nas políticas dos sites de origem.

## Histórias de usuário

### P1 — Receber uma compilação semanal

Como leitor de notícias de tecnologia, quero receber por e-mail uma compilação semanal dos novos posts dos blogs selecionados, para acompanhar novidades sem visitar cada site.

**Critérios de aceite**

1. Dada uma execução semanal, quando houver posts publicados no período, então a compilação contém os posts encontrados e seus links para as fontes originais.
2. Quando não houver posts elegíveis, então a execução termina sem enviar uma compilação vazia.
3. Quando uma fonte falhar, então as demais fontes ainda são processadas e a falha fica identificada no resultado da execução.

### P2 — Entender rapidamente cada publicação

Como leitor, quero ver um resumo e uma categoria para cada publicação, para decidir rapidamente o que merece leitura completa.

**Critérios de aceite**

1. Cada item enviado contém título, fonte, data de publicação, URL original, resumo e uma categoria.
2. Cada item recebe uma das categorias configuradas: Dados e IA; Engenharia de Software; Infraestrutura e Cloud; Segurança; UX e Design; Negócios e Inovação.
3. Se o processamento de um item falhar, o item não é apresentado como se tivesse um resumo válido; a falha é registrada e os outros itens continuam.

### P3 — Ajustar fontes e execução

Como responsável pela solução, quero configurar a frequência, as fontes, as categorias e os parâmetros necessários sem editar a lógica do programa, para manter a seleção atualizada.

**Critérios de aceite**

1. As fontes e os parâmetros gerais são carregados de arquivos JSON.
2. Uma configuração inválida é apontada com informação suficiente para identificar o campo ou a fonte incorreta.
3. As fontes iniciais são Uber, Meta, Google Developers, Google Cloud, Microsoft, AWS, OpenAI, Anthropic, GitHub e Netflix.

## Requisitos funcionais

- **FR-001**: A solução DEVE carregar de configuração a periodicidade de varredura, a lista de fontes, as categorias e as credenciais necessárias.
- **FR-002**: A solução DEVE iniciar com frequência de varredura semanal e com as dez fontes definidas nesta especificação.
- **FR-003**: Cada fonte DEVE ter uma URL de listagem e as informações necessárias para localizar posts e suas datas de publicação.
- **FR-004**: A coleta DEVE selecionar posts publicados no período da varredura, em vez de enviar páginas inteiras à etapa de processamento.
- **FR-005**: A solução DEVE extrair e armazenar localmente o conteúdo textual e os metadados necessários de cada post elegível.
- **FR-006**: A solução DEVE evitar incluir mais de uma vez a mesma publicação em compilações futuras.
- **FR-007**: A solução DEVE resumir cada publicação elegível e associá-la a uma das categorias configuradas.
- **FR-008**: A solução DEVE compor uma mensagem de e-mail legível, com os dados identificadores, resumo e link original de cada publicação.
- **FR-009**: A solução DEVE enviar a compilação ao destinatário configurado quando houver itens válidos.
- **FR-010**: A solução DEVE registrar o resultado da execução, incluindo fontes processadas, falhas e itens coletados, processados e enviados.
- **FR-011**: Uma falha isolada em uma fonte ou publicação NÃO DEVE impedir o processamento dos demais itens independentes.
- **FR-012**: Credenciais NÃO DEVEM ser armazenadas em arquivos de configuração versionados; devem ser fornecidas por mecanismo seguro de configuração do ambiente de execução.
- **FR-013**: A solução DEVE poder ser executada manualmente e por um agendador semanal.

## Requisitos não funcionais

- **NFR-001**: O fluxo deve ser automatizável em CI para validação.
- **NFR-002**: O conteúdo coletado e os resultados processados devem ser armazenados localmente, de modo que publicações já tratadas possam ser reconhecidas em execuções posteriores.
- **NFR-003**: A integração com fontes deve identificar separadamente a configuração de extração de cada blog, pois as estruturas HTML variam.
- **NFR-004**: Erros de configuração, coleta, processamento e envio devem ser observáveis; não devem ser convertidos em sucesso silencioso.

## Entidades e dados

- **Fonte**: nome, URL, configuração de extração e informação de data de publicação.
- **Publicação coletada**: fonte, título, URL original, data de publicação e conteúdo textual.
- **Publicação processada**: publicação coletada, resumo, categoria e estado do processamento.
- **Execução**: horário, período coberto, fontes tentadas, contagens por etapa e falhas.
- **Configuração**: frequência, fontes, categorias, destinatário e referências às credenciais fornecidas pelo ambiente.

## Critérios de sucesso

- **SC-001**: Uma execução semanal consegue produzir uma compilação com os posts elegíveis das fontes configuradas.
- **SC-002**: Todo item enviado possui título, fonte, data, URL original, resumo e uma categoria válida.
- **SC-003**: Posts fora do período não são incluídos; posts já enviados não são enviados novamente.
- **SC-004**: Uma falha em uma fonte não impede a conclusão das outras fontes, e aparece no resultado da execução.
- **SC-005**: É possível alterar a lista de fontes e os parâmetros sem modificar os scripts de processamento.

## Premissas e questões em aberto

- A janela semanal corresponde aos sete dias anteriores ao início da execução. O fuso horário usado para calcular essa janela precisa ser definido na configuração de implantação.
- A URL exata e os seletores de cada fonte serão confirmados durante o mapeamento dos sites; não são inventados nesta especificação.
- **Entrega de e-mail**: o briefing indica Outlook, mas deixa em aberto se ele é o meio adequado. Definir o serviço de envio, autenticação e destinatário antes da implementação do envio.
- **LLM**: o briefing propõe GitHub Copilot CLI e pergunta se é possível autenticá-lo por credenciais em `.env`. Confirmar uma interface suportada para processamento automatizado e como suas credenciais serão fornecidas. Não assumir que uma conta pessoal ou sessão interativa do CLI é adequada para execução agendada.
- **Armazenamento remoto**: o briefing cita GitHub, mas não especifica quais dados devem ser armazenados remotamente. Definir esse escopo antes de sincronizar conteúdo ou credenciais.
