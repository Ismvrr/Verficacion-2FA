# Verificación 2FA + Validación de Teléfonos

API REST con autenticación de dos factores (2FA) y validación de números telefónicos a través de múltiples proveedores externos.

---

## v1 — Versión original

Tag: `v1`

### Funcionalidad

- Login con usuario/contraseña + verificación OTP (2FA)
- Generación y validación de códigos OTP numéricos de 6 dígitos
- Integración con **reCAPTCHA v3** (invisible)
- Validación de números telefónicos contra múltiples APIs externas configurables
- Carga de archivos CSV para poblar la base de datos local de numeraciones
- Autenticación por **API Key** para endpoints de terceros
- CRUD básico de usuarios y tokens por línea de comandos (`crear_usuario.py`)
- Panel de administración de proveedores API (dashboard)
- Base de datos: SQLite con SQLModel

### Stack técnico

| Componente | Tecnología |
|------------|-----------|
| Backend | Python + FastAPI |
| ORM | SQLModel |
| Base de datos | SQLite |
| Frontend | Bootstrap 5 básico |
| CAPTCHA | Google reCAPTCHA v3 |
| Cliente HTTP | httpx (Async) |

### Rutas originales

| Ruta | Descripción |
|------|-------------|
| `GET /` | Página de login (3 pasos: login → OTP → dashboard) |
| `POST /auth/login` | Autenticación usuario/contraseña |
| `POST /auth/generar-otp` | Generar código OTP |
| `POST /auth/validar-otp` | Validar código OTP |
| `GET /telefonos/consulta` | Consultar número telefónico vía API externa |
| `POST /telefonos/actualizar-bd` | Cargar CSV a base de datos local |

### Frontend original

- Página única `index.html` con estilo Bootstrap básico
- Flujo de 3 pasos: login → generar OTP → validar OTP
- Sin panel de administración unificado
- Sin diseño responsivo avanzado

---

## v1.1 — Actualización actual

*Sin tag — versión en desarrollo activo*

### Cambios realizados

#### Frontend (rediseño completo)

- **Nuevo diseño visual**: Glassmorphism + paleta **Vapor Neon**
  - Fondo morado oscuro con degradados
  - Acento neón rosa `#ff2d95`
  - Acento cian `#00fff0`
  - Acento violeta `#b388ff`
- **Dashboard unificado** (`dashboard.html`):
  - Pantalla de login integrada (overlay)
  - Sidebar con 7 secciones: Verificador, Historial, OTP Config, BD Local, Usuarios, Tokens, APIs
  - Tablas con estilo glassmorphism
  - Modales con diseño glassmorphism
  - Elementos decorativos: esferas flotantes animadas, botones neón
- **Página independiente** (`telefonos.html`):
  - Diseño glassmorphism consistente
  - Validación de tokens
  - Consulta de teléfonos y búsqueda en BD local
  - Botón de regreso al dashboard
- Eliminación de `index.html` (ya no se sirve)

#### Backend

- Nuevo router `/admin` con endpoints protegidos para:
  - CRUD completo de usuarios
  - CRUD completo de tokens
  - CRUD completo de proveedores API
  - Consulta y recarga de base de datos local
- Refactor a estructura modular con `__init__.py` en todos los paquetes
- Ruta raíz `GET /` ahora sirve `dashboard.html`
- Ruta `GET /telefonos` sirve `telefonos.html`

### Instalación y uso

```bash
# Clonar
git clone https://github.com/Ismvrr/Verficacion-2FA.git
cd Verficacion-2FA

# Entorno virtual
python -m venv venv
venv\Scripts\activate

# Dependencias
pip install -r requirements.txt

# Ejecutar
python main.py
```

Servidor en `http://localhost:8000`

### Variables de entorno (.env)

```
SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
RECAPTCHA_SECRET_KEY=...
RECAPTCHA_SITE_KEY=...
```
