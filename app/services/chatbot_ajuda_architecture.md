# SCRUM-195 - Decisao arquitetural do chatbot de ajuda

## Avaliacao

O chat atual usa `mensagens_chat` e `ChatService` com forte dependencia de empresa,
historico e contexto operacional do empreendimento. O fluxo de relatorios tambem possui
prompt e persistencia proprios para relatorios de IA.

Reaproveitar essas entidades diretamente para a Central de Ajuda misturaria historicos e
contextos diferentes: relatorios analisam dados do negocio; ajuda precisa consultar tutoriais,
FAQ e futuros modulos de conhecimento.

## Decisao

Criar uma entidade generica de `chatbots` e uma entidade de
`chatbot_modulos_conhecimento`. Cada chatbot possui um `tipo` (`relatorios` ou `ajuda`) e os
modulos permitem injetar topicos dinamicos sem alterar o modelo principal.

O contrato de comunicacao reaproveita o padrao existente do chat: resposta JSON com `reply`.

## Consequencia

O chatbot de ajuda fica isolado do historico atual de mensagens e pode evoluir com novos
modulos de tutorial, FAQ ou integracoes futuras sem quebrar o principio de responsabilidade
unica.
