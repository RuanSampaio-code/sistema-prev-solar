
Desenvolva um sistema web completo para previsibilidade de geração de energia elétrica utilizando imagens de painéis solares.

O sistema será utilizado por distribuidoras de energia e equipes técnicas para processar imagens de instalações fotovoltaicas e estimar automaticamente o potencial energético gerado com base em modelos de visão computacional já existentes.

IMPORTANTE:
Os modelos de IA para reconhecimento dos painéis solares já estão prontos. O sistema deve focar principalmente em:

* upload e gerenciamento das imagens;
* integração com os modelos de IA;
* processamento;
* cálculo da previsão energética;
* autenticação;
* relatórios;
* dashboard;
* experiência do usuário.

Quero que a solução seja construída utilizando a stack mais simples, produtiva e moderna possível, priorizando facilidade de desenvolvimento fullstack integrado entre frontend e backend.

RECOMENDAÇÃO DE STACK:

* Backend: Python com FastAPI
* Frontend: Next.js
* Banco de Dados: PostgreSQL
* IA/Visão Computacional: OpenCV + TensorFlow/PyTorch
* ORM: SQLAlchemy
* Autenticação: JWT
* Upload de arquivos: armazenamento local inicialmente
* Containerização: Docker
* Filas/processamento assíncrono: Celery + Redis (caso necessário)

O motivo da escolha do Python é facilitar a integração direta com os modelos de IA já existentes.

O sistema deve possuir arquitetura moderna, modular e escalável.

---

# Objetivo do Sistema

O sistema deve permitir:

1. Upload de imagens de painéis solares;
2. Processamento automático das imagens;
3. Identificação de:

   * quantidade de painéis;
   * área estimada;
   * inclinação;
   * características relevantes;
4. Cálculo da previsão de geração energética;
5. Priorização automática dos maiores potenciais energéticos;
6. Exportação de relatórios CSV;
7. Controle de acesso por usuário;
8. Dashboard visual dos resultados.

---

# Funcionalidades Obrigatórias

## 1. Autenticação

Implementar:

* login;
* logout;
* JWT;
* criptografia de senhas;
* controle de acesso por perfil:

  * administrador;
  * operador.

---

## 2. Upload de Imagens

Criar interface moderna e responsiva para:

* upload individual;
* upload em lote;
* drag and drop;
* preview das imagens;
* barra/status de upload;
* validação de formatos:

  * PNG;
  * JPEG;
  * JPG.

Validar:

* tamanho máximo;
* qualidade mínima da imagem;
* formatos inválidos.

---

## 3. Processamento com IA

Integrar os modelos já existentes.

Fluxo:

1. usuário envia imagem;
2. backend envia para pipeline de IA;
3. IA retorna:

   * quantidade de painéis;
   * características detectadas;
   * métricas relevantes;
4. sistema calcula previsão energética;
5. salva no banco.

O processamento deve ser assíncrono para evitar travamento da interface.

---

## 4. Dashboard

Criar dashboard moderno contendo:

* total de imagens processadas;
* total de painéis detectados;
* maior previsão energética;
* ranking das unidades consumidoras;
* gráficos;
* filtros;
* histórico de processamentos.

---

## 5. Tabela de Resultados

A tabela deve possuir:

* unidade consumidora;
* quantidade de painéis;
* energia estimada;
* data do processamento;
* status;
* botão para detalhes.

Implementar:

* paginação;
* ordenação;
* busca;
* filtro;
* ordenação automática por maior potencial energético.

---

## 6. Exportação CSV

Permitir:

* exportação individual;
* exportação consolidada;
* download automático.

Campos obrigatórios:

* identificação da unidade consumidora;
* quantidade de painéis;
* potencial energético estimado.

---

# Requisitos Não Funcionais

## Performance

* processar até 10 imagens simultaneamente;
* suportar até 100MB totais;
* processamento eficiente;
* backend assíncrono.

---

## Segurança

* JWT;
* senhas criptografadas;
* RBAC;
* validação de uploads;
* proteção contra uploads maliciosos.

---

## Usabilidade

* interface intuitiva;
* design moderno;
* desktop-first;
* feedback visual;
* loading states;
* toasts;
* manual integrado.

---

# Arquitetura Esperada

Estruture o projeto utilizando:

* arquitetura modular;
* separação clara entre:

  * frontend;
  * backend;
  * serviços de IA;
  * banco de dados;
* boas práticas;
* SOLID;
* clean architecture quando fizer sentido.

---

# Estrutura Esperada do Backend

Desejo:

* controllers/routes;
* services;
* repositories;
* models;
* schemas;
* middlewares;
* autenticação;
* módulo de processamento;
* módulo de relatórios.

---

# Estrutura Esperada do Frontend

Desejo:

* páginas organizadas;
* components reutilizáveis;
* gerenciamento de estado;
* upload component;
* dashboard;
* tabelas;
* autenticação;
* telas modernas.

---

# Diferenciais Desejados

Se possível adicionar:

* fila de processamento;
* monitoramento do status da IA;
* logs;
* auditoria;
* dashboard analítico;
* gráficos em tempo real;
* suporte futuro para API externa;
* arquitetura preparada para cloud.

---

# Entregáveis Esperados

Quero que a IA gere:

1. Arquitetura completa do sistema;
2. Estrutura de pastas;
3. Modelagem do banco;
4. APIs REST;
5. Fluxos;
6. Código inicial backend;
7. Código inicial frontend;
8. Docker Compose;
9. Estrutura de autenticação;
10. Integração com IA;
11. Dashboard moderno;
12. Estratégia de escalabilidade;
13. Plano de deploy;
14. README técnico completo.

---

# Importante

Considere que:

* os modelos de IA já existem;
* o foco principal é construir a plataforma;
* o sistema deve ser profissional e escalável;
* o código deve ser limpo e organizado;
* priorize produtividade e integração fácil entre IA e backend;
* explique as decisões arquiteturais tomadas.

---

O documento base do projeto descreve um sistema de previsão energética por imagens de painéis solares utilizado no contexto de distribuidoras de energia elétrica. 

o model para uso estar na pagina model
