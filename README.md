# AlcancePro

Sistema web para auditar el **alcance contractual** de expedientes públicos y privados (TI, obras civiles, consultorías y servicios). Carga los documentos del proceso, aplica el protocolo de analista senior de requisitos y genera la matriz checklist con trazabilidad horizontal, más el Excel `Checklist_Alcance_Proyecto.xlsx`.

## Qué hace

- Login, registro y roles (`ADMIN`, `ANALISTA`, `REVISOR`).
- Expedientes persistidos en **MongoDB** (`alcancepro`).
- Carga de Bases/TDR, consultas, propuesta, contrato, adendas y anexos (PDF, DOCX, XLSX, TXT).
- Análisis con IA usando granularidad microscópica y cruce documental TDR → consultas → propuesta → contrato.
- Matriz de alcance del producto y del proyecto, con casilla de cumplimiento.
- Entregables de gestión con plazo y referencia.
- Exportación Excel (hojas `Checklist_Alcance` y `Entregables`, desplegable en columna F).

## Arquitectura

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite |
| Backend | Python FastAPI |
| Base de datos | MongoDB 7 (`alcancepro`) |
| Archivos | `backend/uploads` |
| Excel | pandas + openpyxl |
| IA | Gemini (`LLM_API_KEY`) lee los PDF y extrae la matriz |

## 1. MongoDB

Este equipo no requiere Docker. MongoDB portable queda en `tools/` y los datos en `mongo/data`.

Primera vez (si aún no está extraído):

```bat
powershell -ExecutionPolicy Bypass -File scripts\setup-mongo.ps1
```

Arranque:

```bat
powershell -ExecutionPolicy Bypass -File scripts\start-mongo.ps1
```

URI local:

```env
MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DB=alcancepro
```

Colecciones: `users`, `expedientes`, `documents`, `analysis_jobs`, `scope_items`, `deliverables`, `audit_logs`.

Si más adelante instala Docker, también puede usar `docker compose up -d` (Mongo autenticado `alcance` / `alcance123` y consola en http://localhost:8081). En ese caso cambie la URI a:

```env
MONGODB_URI=mongodb://alcance:alcance123@localhost:27017/?authSource=admin
```

## 2. Backend

```bat
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En `backend/.env` configure la clave de Gemini (Google AI Studio):

```env
LLM_API_KEY=
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta
LLM_MODEL=gemini-flash-latest
```

Sin `LLM_API_KEY` el sistema opera (login, expedientes, documentos) con extractor local. Con clave, **Ejecutar análisis** envía los PDF a Gemini.

```bat
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1
```

API: http://localhost:8008/api/health

Cuentas iniciales:

| Rol | Correo | Contraseña |
|---|---|---|
| Admin | `admin@alcancepro.pe` | `Admin123*` |
| Analista | `analista@alcancepro.pe` | `Admin123*` |
| Revisor | `revisor@alcancepro.pe` | `Admin123*` |

## 3. Frontend

```bat
cd frontend
copy .env.example .env
npm install
npm run dev
```

Aplicación: http://localhost:5173

## Uso

1. Inicie sesión.
2. Cree un expediente (entidad, sector, público/privado).
3. Adjunte documentos clasificándolos. El motor no asume el nombre del archivo.
4. Pulse **Ejecutar análisis**.
5. Revise la matriz (producto vs proyecto), marque cumplimiento y contradicciones.
6. Descargue `Checklist_Alcance_Proyecto.xlsx`.

## Módulos

- **Tablero**: expedientes, pendientes y contradicciones.
- **Expedientes**: documentos, análisis, checklist y entregables.
- **Usuarios**: roles (solo admin).
- **Configuración**: estado de MongoDB y clave de Gemini.
