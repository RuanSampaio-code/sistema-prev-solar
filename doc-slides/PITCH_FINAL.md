# PREVSOLAR — Pitch Final (Segunda Avaliação)
> Roteiro de slides para apresentação de 7 min. Máximo 10 slides. Baseado no roteiro sugerido em *Sugestões de Pitch.pdf*.

---

## Slide 1 — Capa

**PREVSOLAR**
*Sistema de Previsibilidade de Geração de Energia Elétrica*

| Campo | |
|---|---|
| **Empresa parceira** | EQT Lab — Grupo Equatorial |
| **Orientador** | Marcos Sá |
| **Equipe** | Davi Azevedo · Suellen Santos · Mateus Pereira · Patrinny Ataíde · José Ruan Sampaio |
| **Programa** | Residência em TIC — UEMA BRISAS |

---

## Slide 2 — O Problema

### A divergência que custa dinheiro e segurança à rede

Distribuidoras de energia como o Grupo Equatorial recebem declarações de projetos fotovoltaicos com estimativas de geração. Na prática, **a energia real gerada muitas vezes não corresponde ao que foi homologado**.

- Risco de sobrecarga e instabilidade na rede elétrica
- Fraude e irregularidade em projetos de geração distribuída
- Verificação manual é lenta, cara e imprecisa

> *"Como saber, de fato, quantos painéis existem e quanto eles geram — só com uma imagem?"*

---

## Slide 3 — Nossa Solução

### Análise automatizada de imagens de drone com IA

O **PrevSolar** é uma plataforma web que recebe imagens aéreas de instalações fotovoltaicas e entrega, em minutos, um laudo completo:

- **Detecção** dos painéis solares via visão computacional
- **Cálculo de área real** de cada painel (em m²)
- **Estimativa de geração** (kWh/mês) baseada em fórmula física com GSD
- **Localização geográfica** de cada painel detectado
- **Relatório exportável** em Excel pronto para análise

Sem visita técnica. Sem contagem manual. Sem planilha.

---

## Slide 4 — Jornada do Cliente

### Como o fiscal usa o sistema

```
1. UPLOAD
   Arrasta a imagem de drone (PNG / JPG / GeoTIFF)
   para a plataforma — até 10 imagens por lote.

2. CONFIGURAÇÃO
   Escolhe o modelo de IA e a sensibilidade de detecção.
   GSD é lido automaticamente dos metadados do arquivo.

3. PROCESSAMENTO
   A IA processa em segundo plano (< 2 min por imagem).
   O usuário acompanha o status em tempo real.

4. RESULTADO
   Visualização interativa com zoom/pan.
   Mouse sobre qualquer painel mostra área, geração e endereço.

5. RELATÓRIO
   Exporta Excel em dois níveis:
   - Resumo por imagem
   - Dados individuais de cada painel (lat/lon + endereço)
```

---

## Slide 5 — Diferenciais

### O que nos separa de uma análise manual — ou de um sistema genérico

| Diferencial | Impacto |
|---|---|
| **Dois modelos de IA** (UNet v2 + YOLO v11) | Flexibilidade: escolha o modelo mais preciso para o tipo de imagem |
| **GSD automático via GeoTIFF** | Área real calculada sem nenhuma configuração manual |
| **Análise por painel individual** | Identifica painéis suspeitos, não apenas totais |
| **Geolocalização via OpenStreetMap** | Cada painel tem endereço — auditoria georreferenciada |
| **Visualização interativa** | Inspetor visual com zoom até 8× diretamente no navegador |
| **Exportação Excel estruturada** | Relatório pronto para importar em sistemas do cliente |
| **Processamento assíncrono** | Não trava a interface — envie e continue trabalhando |

---

## Slide 6 — Tecnologia

### Stack selecionada para robustez e escalabilidade

**Inteligência Artificial**
- UNet v2 com backbone ResNet34 (segmentação semântica por pixel)
- YOLO v11m-seg (detecção por instância)
- Tiling adaptativo (512–640 px) para imagens de alta resolução
- OpenCV + Rasterio para leitura de GeoTIFF e extração de GSD

**Backend**
- FastAPI · Celery + Redis (fila assíncrona) · PostgreSQL

**Frontend**
- Next.js 14 · React · TypeScript · Tailwind CSS · TanStack Query

---

## Slide 7 — Demonstração

### Navegação pelas telas implementadas

> **[INSERIR VÍDEO AQUI — gravar navegação pelas telas abaixo]**

Roteiro do vídeo (sugestão, ~90 s):
1. Login na plataforma
2. Dashboard — visão geral com contagem de imagens e potencial total
3. Upload — arrastar imagem, selecionar modelo UNet v2, enviar
4. Aguardar processamento (mostrar badge "processando")
5. Abrir resultado: imagem com bounding boxes, passar mouse sobre painéis (tooltip com área, kWh, endereço)
6. Usar zoom na imagem processada
7. Tabela de painéis individuais — destacar coluna de coordenadas e endereço
8. Exportar Excel — abrir arquivo e mostrar as duas abas
9. Relatórios — dashboard de totais e download consolidado

---

## Slide 8 — Ganhos para o Cliente

### O que o Grupo Equatorial passa a ter com o PrevSolar

| Antes | Com PrevSolar |
|---|---|
| Verificação manual por técnico em campo | Análise remota via imagem de drone |
| Dias para obter um laudo | Resultado em menos de 2 minutos |
| Contagem de painéis imprecisa | IA com confiança por painel |
| Sem localização exata de irregularidades | Endereço e coordenadas de cada painel |
| Planilha montada à mão | Excel gerado automaticamente |
| Sem rastreabilidade do processo | Histórico completo de análises no sistema |

**ROI direto:** Redução de custo operacional de fiscalização e maior velocidade de identificação de projetos irregulares.

---

## Slide 9 — Para Implantar

### O que o cliente precisa fazer para colocar o PrevSolar em produção

**Infraestrutura mínima**
- Servidor Linux com Docker (CPU ou GPU NVIDIA recomendada)
- Banco PostgreSQL + Redis (podem ser containers)
- Domínio e HTTPS para o frontend

**Dados necessários**
- Imagens de drone das instalações fiscalizadas (PNG, JPG ou GeoTIFF)
- Cadastro de usuários (operadores e administradores)

**Integração opcional**
- API REST disponível para conectar ao sistema de gestão atual do cliente
- Exportação Excel compatível com qualquer sistema de BI

**Entregáveis da equipe**
- Código-fonte completo (repositório Git)
- Documentação técnica
- Manual de uso integrado ao sistema
- Suporte na implantação inicial

---

## Slide 10 — Contato e Chamada para Ação

### Vamos colocar o PrevSolar em produção?

Convite: **adotem a solução e a equipe estará disponível para dar suporte na implantação.**

---

**Equipe PrevSolar — Residência TIC UEMA BRISAS**

| Integrante | Contato |
|---|---|
| Davi Azevedo | — |
| Suellen Santos | — |
| Mateus Pereira | — |
| Patrinny Ataíde | patrinnyataiderocha@gmail.com |
| José Ruan Sampaio | jruansampaiodev@gmail.com |

**Orientador:** Marcos Sá
**Parceiro:** EQT Lab — Grupo Equatorial

---

## Notas de Apresentação

- **Tempo total: 7 min** — sugestão de distribuição:
  - Slides 1–2: 1 min (problema)
  - Slides 3–5: 2 min (solução e diferenciais)
  - Slide 6: 30 s (tecnologia — só mencionar, não detalhar)
  - Slide 7: 2 min (vídeo de demo)
  - Slides 8–10: 1,5 min (ganhos, implantação, chamada)
- Use linguagem simples — evite jargões técnicos com a banca/cliente
- O vídeo de demo é o coração da apresentação — grave com qualidade e ensaie o roteiro
- Ao final, a banca fará sugestões de comercialização — anotem tudo
