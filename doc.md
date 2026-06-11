# CLAUDE.md — Contexto do Projeto PrevSolar

## O que é este projeto

**PrevSolar** é uma plataforma web para análise de imagens aéreas (drone) de instalações fotovoltaicas. O sistema recebe imagens de painéis solares, aplica um modelo de segmentação (UNet/PyTorch) para detectar os painéis na imagem, conta-os, estima a área total coberta e calcula o potencial de geração energética (kWh/mês). O resultado é apresentado com visualização da máscara sobre a imagem original, estatísticas e exportação em CSV.

**Contexto de uso:** distribuidoras de energia e equipes técnicas que precisam auditar ou dimensionar instalações solares a partir de imagens de drone, sem processamento manual.

---

## Stack completa

| Camada | Tecnologia |
|---|---|
| Backend API | FastAPI + Python 3.11 |
| IA | PyTorch 2.3 + segmentation-models-pytorch (UNet/ResNet34) + OpenCV |
| Banco | PostgreSQL 16 + SQLAlchemy 2.0 + Alembic |
| Fila | Celery 5.4 + Redis 7 |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Auth | JWT (python-jose) + bcrypt |
| Deploy | Docker Compose (5 serviços) |

---

## Estrutura de diretórios

```
sistema-prev-solar/
├── backend/
│   ├── ai/
│   │   ├── inference.py        # carrega Model-unet.pth e roda predição
│   │   └── pipeline.py         # orquestra: leitura → UNet → pós-proc → kWh
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── auth.py         # login, /me, CRUD usuários (admin)
│   │   │   ├── images.py       # upload, listar, detalhe, deletar
│   │   │   ├── results.py      # dashboard + estatísticas
│   │   │   ├── reports.py      # exportação CSV
│   │   │   └── visualization.py # overlay da máscara sobre a imagem
│   │   ├── core/
│   │   │   ├── config.py       # Settings (Pydantic BaseSettings, lê .env)
│   │   │   ├── database.py     # engine SQLAlchemy + SessionLocal
│   │   │   └── security.py     # create_access_token, verify_password
│   │   ├── models/             # ORM: User, Image, Result
│   │   ├── repositories/       # queries isoladas: ImageRepository, UserRepository
│   │   ├── schemas/            # Pydantic I/O: auth.py, image.py
│   │   ├── workers/
│   │   │   ├── celery_app.py   # instância Celery (broker/backend=Redis)
│   │   │   └── tasks.py        # process_image_task (max_retries=3)
│   │   └── main.py             # cria app FastAPI, registra routers, CORS
│   ├── alembic/versions/       # 3 migrações: schema inicial, TEXT error_msg, remove col
│   └── scripts/seed_admin.py   # cria admin@prevsolar.com / admin123
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── login/page.tsx
│       │   ├── (dashboard)/            # grupo de rotas protegidas
│       │   │   ├── layout.tsx          # verifica JWT, renderiza Sidebar
│       │   │   ├── dashboard/page.tsx  # 4 stat-cards + BarChart ranking top 10
│       │   │   ├── upload/page.tsx     # Dropzone + preview grid
│       │   │   ├── results/page.tsx    # tabela paginada + busca + filtros
│       │   │   ├── results/[id]/page.tsx # detalhe + visualização máscara
│       │   │   └── reports/page.tsx    # exportação CSV global
│       │   └── providers.tsx           # ReactQuery + Toaster
│       ├── lib/
│       │   ├── api.ts          # Axios com interceptor JWT + redirect 401
│       │   └── auth.ts         # login(), logout(), getUser()
│       └── types/index.ts      # User, ImageRecord, Result, DashboardStats
├── docs/model/Model-unet.pth   # arquivo do modelo (não está no git, montar via volume)
├── images-slz/                 # imagens de drone para testes
├── test-model-unet.ipynb       # notebook de validação do modelo
├── docker-compose.yml
├── .env / .env.example
└── README.md
```

---

## Banco de dados (3 tabelas)

```
users
  id, name, email, hashed_password
  role: enum(admin | operator)
  is_active, created_at

images
  id, user_id → FK users
  filename, filepath, original_name, file_size_kb
  status: enum(pending | processing | done | error)
  error_message (TEXT), uploaded_at

results
  id, image_id → FK images (UNIQUE — 1 resultado por imagem)
  panel_count (int)
  detected_area_m2 (float)
  estimated_kwh_month (float)
  mask_filepath (path da máscara salva)
  processed_at
```

---

## Modelo de IA — UNet

**Arquivo:** `docs/model/Model-unet.pth` (montado como volume read-only em `/app/ai/model/`)

**Arquitetura:**
- UNet com encoder ResNet34 (`segmentation_models_pytorch.Unet`)
- Input: tiles RGB 640×640 (3 canais, normalização ImageNet)
- Output: logits 1 canal → sigmoid → threshold 0.40 → máscara binária

**Pipeline de inferência (`backend/ai/pipeline.py`):**
1. Lê imagem em **resolução nativa** com OpenCV (TIFFs via PIL para suporte a 16-bit/multi-banda)
2. Lê o **GSD real** (metros/pixel) dos metadados do GeoTIFF via `rasterio`; converte graus→metros para CRS EPSG:4326; fallback de 0.30 m/px
3. **Inferência por tiling:** tiles 640×640 com overlap de 128px; tiles sobrepostos combinados por média de probabilidades (suaviza artefatos de borda)
4. Normaliza cada tile com mean `[0.485, 0.456, 0.406]` e std `[0.229, 0.224, 0.225]`
5. Threshold 0.40 → máscara binária
6. `cv2.findContours` com filtro mínimo de 10 px por contorno
7. Calcula `detected_area_m2 = Σ(área_contorno_px × gsd²)` — fisicamente correto via GSD real
8. Calcula `kWh/mês = área × IRRADIACAO_LOCAL × EFICIENCIA_MEDIA × (1 − PERDAS_SISTEMA) × 30`
9. Salva máscara PNG em `uploads/mask_{stem_original}.png`
10. Retorna: `panel_count`, `detected_area_m2`, `estimated_kwh_month`, `mask_filepath`

**Constantes configuráveis via `.env`:**
```
IRRADIACAO_LOCAL=5.5    # kWh/m²/dia — São Luís-MA (média anual INMET)
EFICIENCIA_MEDIA=0.18   # eficiência típica de painel fotovoltaico (18%)
PERDAS_SISTEMA=0.14     # perdas por cabeamento, inversor, sujeira etc.
```

---

## Fluxo de processamento de imagens

```
Usuário → POST /api/images/upload (até 10 arquivos, PNG/JPG/TIFF, max 200MB total)
  ↓
Backend salva arquivos em /app/uploads/
Backend insere registros em `images` (status=pending)
Backend chama process_image_task.delay(image_id) para cada imagem
  ↓
Celery Worker:
  1. status → processing
  2. pipeline.process_image(filepath) → UNet → resultado
  3. INSERT em `results`
  4. status → done
  (falha: status → error, max 3 retries com 30s countdown)
  ↓
Frontend faz polling a cada 5s em /results/[id]
Exibe overlay da máscara via GET /api/images/{id}/visualization
```

---

## Autenticação e perfis

- JWT com `python-jose`, expiração em 480 min (configurável via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Token payload: `{ sub: user_id, role, exp }`
- `get_current_user()` — valida JWT, retorna User ou 401
- `require_admin()` — exige `role=admin` ou retorna 403
- Frontend: token em `localStorage`, Axios interceptor adiciona `Authorization: Bearer`; 401 limpa token e redireciona `/login`

**Perfis:**
- `admin` — tudo + criar/listar usuários
- `operator` — upload, visualização, exportação

---

## API endpoints principais

```
POST   /api/auth/login            # OAuth2PasswordRequestForm → JWT
GET    /api/auth/me               # usuário autenticado
POST   /api/auth/users            # criar usuário (admin only)
GET    /api/auth/users            # listar usuários (admin only)

POST   /api/images/upload         # upload de imagens (multipart/form-data)
GET    /api/images                # listar paginado (?search, ?status, ?order_by, ?page)
GET    /api/images/{id}           # detalhe + resultado
POST   /api/images/{id}/delete    # deletar imagem e máscara
GET    /api/images/{id}/visualization  # retorna imagem com overlay (blob)

GET    /api/results/dashboard     # stats globais + ranking top 10

GET    /api/reports/csv           # exporta CSV (?image_id para individual)
```

Swagger disponível em `http://localhost:8000/docs`

---

## Frontend — páginas e comportamento

| Rota | Componente | Detalhe |
|---|---|---|
| `/login` | `login/page.tsx` | form email+senha, chama `auth.login()` |
| `/dashboard` | `dashboard/page.tsx` | 4 stat-cards, BarChart Recharts, refetch a cada 15s |
| `/upload` | `upload/page.tsx` | react-dropzone, preview grid, POST multipart |
| `/results` | `results/page.tsx` | tabela paginada, busca, filtro status, sort |
| `/results/[id]` | `results/[id]/page.tsx` | detalhe + overlay imagem, polling 5s, delete, CSV |
| `/reports` | `reports/page.tsx` | exportação CSV global |

**Dependências chave do frontend:**
- `@tanstack/react-query` — cache e polling de dados
- `recharts` — gráfico de barras no dashboard
- `react-dropzone` — interface de upload
- `react-hook-form` + `zod` — validação de formulários
- `@radix-ui/*` — componentes Dialog, Select, Label
- `sonner` — toasts
- `lucide-react` — ícones

---

## Docker Compose — 5 serviços

```yaml
postgres     # postgres:16-alpine, porta 5432
redis        # redis:7-alpine, porta 6379
backend      # FastAPI, porta 8000, volume ./backend:/app
worker       # Celery worker, mesmo Dockerfile do backend
frontend     # Next.js, porta 3000
```

**Volumes:**
- `postgres_data` — persistência do banco
- `uploads_data` — imagens enviadas e máscaras geradas (`/app/uploads`)
- `./docs/model:/app/ai/model:ro` — modelo UNet (read-only)

---

## Comandos de desenvolvimento

```bash
# Subir tudo com Docker
docker compose up -d --build

# Migrações
docker compose exec backend alembic upgrade head

# Criar admin inicial
docker compose exec backend python -m scripts.seed_admin

# Celery local (sem Docker)
cd backend && celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Backend local
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend local
cd frontend && npm run dev

# Nova migração Alembic
docker compose exec backend alembic revision --autogenerate -m "descrição"
```

**Credenciais padrão:** `admin@prevsolar.com` / `admin123`

---

## Decisões de arquitetura relevantes

- **Repositórios separados dos modelos:** `repositories/` encapsula todas as queries SQL, rotas apenas orquestram.
- **Worker isolado:** o Celery worker roda em container separado, mas compartilha o mesmo código Python via volume. O modelo UNet é carregado uma vez na inicialização do worker.
- **Processamento assíncrono obrigatório:** o pipeline PyTorch/OpenCV pode levar 5–30s por imagem; sem Celery a API travaria.
- **CPU-only PyTorch:** o Dockerfile instala `torch+cpu` para reduzir tamanho da imagem. Se GPU disponível, ajustar Dockerfile e `inference.py` (já suporta via `torch.cuda.is_available()`).
- **Máscara salva em disco:** a máscara PNG gerada pelo UNet é persistida em `uploads/`, não no banco. O campo `mask_filepath` aponta para ela.
- **Visualização on-demand:** o overlay amarelo+contornos é gerado em memória em cada request a `/visualization`, não pré-computado.
- **Área via GSD real:** a área detectada é calculada por `Σ(área_contorno_px × gsd²)`, onde o GSD (metros/pixel) é lido dos metadados do GeoTIFF via `rasterio`. Para CRS geográfico (EPSG:4326) o GSD em graus é convertido para metros. Fallback de 0.30 m/px quando os metadados estão ausentes ou o arquivo não é TIFF.

---

## Arquivos que não estão no git

- `docs/model/Model-unet.pth` — modelo treinado (grande, deve ser provido separadamente)
- `.env` — variáveis de ambiente (`.env.example` serve de base)
- `images-slz/` — imagens de drone para teste
- `test-model-unet.ipynb` — notebook de validação do modelo
