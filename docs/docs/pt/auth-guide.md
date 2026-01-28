# Guia de Autenticação

Este guia explica o módulo de auth do Lazy Ninja, sua configuração e conceitos avançados. O auth é baseado em JWT, suporta modo stateless ou stateful e se adapta a projetos simples e complexos.

## Início rápido

Registre as rotas de auth na sua API:

```python
from ninja import NinjaAPI
from lazy_ninja.auth import register_auth_routes

api = NinjaAPI()
register_auth_routes(api)
```

## Configuração

As opções ficam em `LAZY_NINJA_AUTH` no Django settings.

### Configurações principais

- `JWT_SECRET`: Segredo para assinar tokens. Usa `SECRET_KEY` se omitido.
- `JWT_ALGORITHM`: Algoritmo JWT (padrão: `HS256`).
- `JWT_ISS` / `JWT_ISSUER`: Emissor (padrão: `lazy-ninja`).
- `JWT_AUD` / `JWT_AUDIENCE`: Audiência (padrão: `lazy-ninja-api`).
- `JWT_ACCESS_EXP`: Expiração do access em segundos (padrão: 86400).
- `JWT_REFRESH_EXP`: Expiração do refresh em segundos (padrão: 2592000).

### Campos de login

Controle explicitamente quais identificadores são aceitos:

```python
LAZY_NINJA_AUTH = {
    "LOGIN_FIELDS": ["email", "username", "login"],
}
```

### Cookies

- `SET_COOKIES`: Define cookies de auth (padrão: `True`).
- `COOKIE_SECURE`: Força cookie seguro (padrão: `not DEBUG`).

### Validação de senha

- `VALIDATE_PASSWORD`: Habilita validadores do Django (padrão: `True`).

### Logs

- `LOG_AUTH_EVENTS`: Registra eventos de login/registro/refresh/logout.

### Modo stateful

Ative revogação server-side via cache:

```python
LAZY_NINJA_AUTH = {
    "STATEFUL": True,
}
```

Quando stateful está ligado:

- Tokens têm `jti`.
- Refresh rotaciona e faz blacklist do token anterior.
- Logout faz blacklist do access e refresh.

## Endpoints

- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/refresh`
- `GET /auth/me`
- `POST /auth/logout`

## Hooks

Hooks de ciclo de vida:

- `ON_LOGIN` / `LOGIN_HOOK`
- `ON_REGISTER` / `REGISTER_HOOK`
- `ON_REFRESH` / `REFRESH_HOOK`
- `ON_LOGOUT` / `LOGOUT_HOOK`

## Conceitos avançados

### Stateless vs stateful

Stateless confia apenas na validade do token. Stateful adiciona revogação por blacklist e permite logout imediato e invalidação do refresh.

### Claims

Os tokens incluem:

- `iss` e `aud` para validação de contexto
- `jti` para revogação stateful
