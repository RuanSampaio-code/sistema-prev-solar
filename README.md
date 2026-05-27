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

### Pré-requisitos
- Docker + Docker Compose

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite .env com suas configurações
```

### 2. Subir os serviços

```bash
docker compose up -d --build
```

### 3. Executar as migrações

```bash
docker compose exec backend alembic upgrade head
```

### 4. Criar o usuário administrador

```bash
docker compose exec backend python -m scripts.seed_admin
```

Acesse: **http://localhost:3000**  
Login padrão: `admin@prevsolar.com` / `admin123`

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
