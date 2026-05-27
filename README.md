# PrevSolar

Plataforma web para previsão de geração de energia solar via análise de imagens de painéis fotovoltaicos.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + Python 3.11 |
| IA | PyTorch (UNet) + OpenCV |
| Banco | PostgreSQL 16 |
| Fila | Celery + Redis 7 |
| Frontend | Next.js 14 + TypeScript + Tailwind |
| Auth | JWT + bcrypt |

---

## Como rodar

### Opção A — Docker (recomendado)

#### Pré-requisitos
- Docker + Docker Compose

#### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite .env com suas configurações
```

#### 2. Subir os serviços

```bash
docker compose up -d --build
```

#### 3. Executar as migrações

```bash
docker compose exec backend alembic upgrade head
```

#### 4. Criar o usuário administrador

```bash
docker compose exec backend python -m scripts.seed_admin
```

Acesse: **http://localhost:3000**  
Login padrão: `admin@prevsolar.com` / `admin123`

---

### Opção B — Execução local (sem Docker)

#### Pré-requisitos

| Ferramenta | Versão mínima | Download |
|---|---|---|
| Python | 3.11 | https://python.org/downloads |
| Node.js | 18.x | https://nodejs.org |
| PostgreSQL | 16 | https://postgresql.org/download |
| Redis | 7 | https://redis.io/download (Windows: https://github.com/tporadowski/redis/releases) |

---

#### 1. Clonar o repositório

```bash
git clone https://github.com/RuanSampaio-code/sistema-prev-solar.git
cd sistema-prev-solar
```

---

#### 2. Configurar o banco de dados (PostgreSQL)

Após instalar o PostgreSQL, acesse o terminal do banco e crie o banco e o usuário:

```sql
CREATE USER prevsolar WITH PASSWORD 'prevsolar_secret';
CREATE DATABASE prevsolar_db OWNER prevsolar;
```

---

#### 3. Configurar variáveis de ambiente

Copie o arquivo de exemplo e edite para o ambiente local:

```bash
cp .env.example .env
```

Abra o `.env` e ajuste os valores para execução local:

```env
POSTGRES_USER=prevsolar
POSTGRES_PASSWORD=prevsolar_secret
POSTGRES_DB=prevsolar_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

REDIS_URL=redis://localhost:6379/0

SECRET_KEY=troque-por-uma-chave-segura
ACCESS_TOKEN_EXPIRE_MINUTES=480

BACKEND_CORS_ORIGINS=http://localhost:3000
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=200

WP_PER_M2=160
EFFICIENCY_FACTOR=0.75
DAILY_PEAK_SUN_HOURS=4.5
```

> **Atenção:** `POSTGRES_HOST` deve ser `localhost` (não `postgres` como no Docker).  
> `REDIS_URL` deve apontar para `localhost` também.

---

#### 4. Backend

```bash
cd backend

# Criar e ativar ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar as migrações
alembic upgrade head

# Criar usuário administrador
python -m scripts.seed_admin

# Iniciar o servidor
uvicorn app.main:app --reload --port 8000
```

API disponível em: **http://localhost:8000**  
Documentação interativa: **http://localhost:8000/docs**

---

#### 5. Worker Celery (processamento de imagens)

Em um **novo terminal**, com o ambiente virtual ativado:

```bash
cd backend
.venv\Scripts\activate  # Windows

celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
```

> O worker é necessário para que as imagens enviadas sejam processadas pelo modelo de IA.

---

#### 6. Frontend

Em um **novo terminal**:

```bash
cd frontend

# Instalar dependências
npm install

# Iniciar em modo desenvolvimento
npm run dev
```

Frontend disponível em: **http://localhost:3000**  
Login padrão: `admin@prevsolar.com` / `admin123`

---

#### Resumo dos terminais necessários

| Terminal | Comando | O que faz |
|---|---|---|
| 1 | `uvicorn app.main:app --reload --port 8000` | API backend |
| 2 | `celery -A app.workers.celery_app worker ...` | Processamento de imagens |
| 3 | `npm run dev` | Interface web |

> PostgreSQL e Redis devem estar rodando como serviços do sistema antes de iniciar o backend.

---

## Estrutura

```
sistema-prev-solar/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # auth, images, results, reports
│   │   ├── core/           # config, database, security
│   │   ├── models/         # SQLAlchemy ORM
│   │   ├── repositories/   # queries ao banco
│   │   ├── schemas/        # Pydantic
│   │   └── workers/        # Celery tasks
│   ├── ai/
│   │   ├── inference.py    # carrega UNet e roda predição
│   │   └── pipeline.py     # pré-proc → inferência → cálculo energia
│   ├── alembic/            # migrações
│   └── scripts/            # seed de usuário admin
├── frontend/
│   └── src/app/            # Next.js App Router
│       ├── login/
│       ├── (dashboard)/
│       │   ├── dashboard/
│       │   ├── upload/
│       │   ├── results/
│       │   └── reports/
└── docs/
    └── model/Model-unet.pth
```

---

## Estimativa energética

O modelo UNet retorna a segmentação dos painéis (máscara binária).
A área detectada é convertida em potencial energético usando:

```
kWh/mês = área_m² × WP_PER_M2 × EFFICIENCY_FACTOR × DAILY_PEAK_SUN_HOURS × 30 / 1000
```

Valores padrão (configuráveis via `.env`):
- `WP_PER_M2 = 160` (W/m²)
- `EFFICIENCY_FACTOR = 0.75`
- `DAILY_PEAK_SUN_HOURS = 4.5`

---

## Perfis de acesso

| Perfil | Permissões |
|---|---|
| `admin` | Tudo + gerenciar usuários |
| `operator` | Upload, visualizar resultados, exportar |

---

## Variáveis de ambiente relevantes

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | Chave JWT — troque em produção |
| `POSTGRES_*` | Credenciais do banco |
| `REDIS_URL` | URL do Redis |
| `MAX_UPLOAD_SIZE_MB` | Limite por upload (padrão: 100) |
| `WP_PER_M2` | Watts-pico por m² de painel |
| `EFFICIENCY_FACTOR` | Fator de eficiência do sistema |
| `DAILY_PEAK_SUN_HOURS` | Horas de pico solar por dia |
