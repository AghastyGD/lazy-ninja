# Guia de Autenticação

Este guia explica o módulo de auth do Lazy Ninja, sua configuração e conceitos avançados. O auth é baseado em JWT, suporta modo stateless ou stateful e se adapta a projetos simples e complexos.

## Início rápido

Para proteger as rotas geradas e registrar as rotas de auth:

```python
from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI

api = NinjaAPI()
DynamicAPI(api, auth=True).init()
```

O modelo configurado em `AUTH_USER_MODEL` nunca recebe CRUD gerado. Crie rotas de gestão de contas com permissões específicas do projeto.

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

Com `DynamicAPI(api, auth=True)`, as rotas protegidas aceitam bearer token ou cookie de access. Pedidos POST, PATCH, PUT e DELETE autenticados por cookie exigem o token CSRF no cabeçalho `X-CSRFToken`. Login e registro devolvem o token no cabeçalho de resposta `X-CSRFToken` e emitem o cookie `csrftoken` quando a configuração CSRF do Django o permite. Refresh e logout com cookie também exigem CSRF. Para clientes que usam apenas bearer, configure `SET_COOKIES=False`.

Se a `NinjaAPI` já tiver um autenticador próprio, `DynamicAPI` preserva-o. Para aceitar também os tokens do Lazy Ninja, adicione `LazyNinjaAccessToken()` e `LazyNinjaAccessCookie()` à configuração de autenticação da API.

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

Use um cache Django partilhado entre processos no modo stateful. Com `ROTATE_REFRESH=False`, o refresh atual permanece válido e volta na resposta; rotação com revogação exige `ROTATE_REFRESH=True` e `STATEFUL=True`.

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
