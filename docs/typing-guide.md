# Guia de Tipagem para Lazy Ninja

## O Problema Fundamental

### O Conflito Entre Dinâmico e Estático

O Lazy Ninja faz **metaprogramação**: gera código, schemas e APIs em **runtime** (quando o programa roda).

Exemplo do que fazemos:
```python
# Em runtime, inspecionamos o model User
User = get_user_model()  # Qual User? Só sabemos rodando!

# Geramos um schema Pydantic dinamicamente
for field in User._meta.get_fields():
    schema_fields[field.name] = (field.type, ...)  # 🔮 Mágica!

UserSchema = create_model('UserSchema', **schema_fields)

# Registramos rotas automaticamente
@api.get("/users")
def list_users() -> UserSchema:  # Esse tipo não existia no código!
    ...
```

**O problema**: Type checkers como Pylance/mypy funcionam de forma **estática** (analisam código SEM rodar).

```
┌─────────────────────────────────────────────────────┐
│  ANÁLISE ESTÁTICA (Pylance/mypy)                    │
│  • Lê arquivos .py                                  │
│  • Analisa imports, classes, funções                │
│  • NÃO executa código                               │
│  • NÃO sabe o que acontece em runtime               │
│  ❌ Não vê schemas gerados dinamicamente            │
└─────────────────────────────────────────────────────┘
          ⬇️  conflito  ⬇️
┌─────────────────────────────────────────────────────┐
│  EXECUÇÃO RUNTIME (Python)                          │
│  • Roda o código                                    │
│  • Descobre models, gera schemas                    │
│  • Cria classes/funções dinamicamente               │
│  ✅ Tudo funciona perfeitamente                     │
└─────────────────────────────────────────────────────┘
```

### Exemplos Concretos do Problema

#### 1️⃣ **User Model Desconhecido**
```python
User = get_user_model()  # Pylance: "Qual User? Pode ser qualquer um!"

# Tentamos acessar:
user.username  # ⚠️ Pylance: "User pode não ter username!"
user.email     # ⚠️ Pylance: "User pode não ter email!"

# Mas sabemos que tem! Só que Pylance não roda o código.
```

#### 2️⃣ **Schemas Gerados Dinamicamente**
```python
UserSchema = generate_schema(User, exclude=["password"])
# Pylance: "UserSchema é... o quê? Não posso ver o que 
#           generate_schema retorna sem rodar!"

class Response(Schema):
    user: UserSchema  # ❌ Type error: UserSchema is not a type
```

#### 3️⃣ **Fields Descobertos por Reflexão**
```python
field = model._meta.get_field("username")
is_unique = field.unique  # ⚠️ Pylance: "field pode ser ForeignKey, 
                          #            ManyToMany, GenericFK...
                          #            nem todos têm 'unique'!"
```

### Por Que Python?

Python foi **projetado para ser dinâmico**:
- Duck typing: "Se anda como pato e grasna como pato..."
- Reflexão poderosa: `getattr()`, `setattr()`, `__dict__`
- Metaclasses: Classes que criam classes
- `eval()`, `exec()`, `type()` para criar código em runtime

**Type hints são um "add-on"** (PEP 484, 2014), não parte fundamental.

```python
# Python: Tipagem opcional
def add(a, b):      # ✅ Funciona
    return a + b

def add(a: int, b: int) -> int:  # ✅ Funciona também
    return a + b

add("hello", "world")  # ✅ Runtime: funciona! ⚠️ Type checker: erro!
```

---

## Lazy Ninja em Outras Linguagens

### 🟢 **Linguagens PERFEITAS para Lazy Ninja**

#### 1. **Ruby** ⭐⭐⭐⭐⭐
```ruby
# Ruby foi FEITO para metaprogramação
class API
  def self.generate_routes(model)
    define_method("list_#{model.name.downcase}") do
      model.all.to_json  # ✅ Sem type errors!
    end
  end
end

# Rails é todo baseado em metaprogramação
User.find_by_email("test@test.com")  # Método gerado em runtime!
```
**Por quê?**
- Metaprogramação é *idiomática*
- `method_missing`, `define_method`, `class_eval`
- Não tem type checking estático irritante
- ActiveRecord faz exatamente isso!

#### 2. **JavaScript/TypeScript** ⭐⭐⭐⭐
```javascript
// JS: Proxies e Reflect API
const api = new Proxy({}, {
  get(target, prop) {
    return (data) => fetch(`/api/${prop}`, { body: data })
  }
})

api.users.list()  // ✅ Gera rota dinamicamente
api.music.create(song)  // ✅ Funciona!

// TypeScript: Conditional Types + Generics resolvem MUITO
type APIRoutes<T> = {
  [K in keyof T]: {
    list: () => Promise<T[K][]>
    get: (id: string) => Promise<T[K]>
  }
}
```
**Por quê?**
- JS é naturalmente dinâmico
- TS tem tipos avançados (Conditional, Mapped, Template Literal Types)
- `Proxy` permite interceptar tudo

#### 3. **Elixir/Erlang** ⭐⭐⭐⭐⭐
```elixir
# Macros são metaprogramação HIGIÊNICA
defmodule API do
  defmacro generate_routes(model) do
    quote do
      def list do
        unquote(model).all()
      end
    end
  end
end

# Phoenix usa isso extensivamente
use MyApp.Router  # Gera rotas via macros!
```
**Por quê?**
- Macros em compile time (melhor que runtime!)
- Pattern matching resolve muita coisa
- Tipagem gradual (Dialyzer não enche o saco)

---

### 🟡 **Linguagens POSSÍVEIS mas Trabalhosas**

#### 4. **Java** ⭐⭐
```java
// Reflection existe mas é VERBOSO
Method method = user.getClass().getMethod("getUsername");
String username = (String) method.invoke(user);  // 😫 Casting manual

// Geração de código em runtime é doloroso
// Melhor usar code generation (compile time)
// Ex: Lombok, MapStruct, Hibernate
```
**Por quê?**
- Type system rígido trava metaprogramação
- Reflection é lento e verboso
- Precisa usar bibliotecas como Byte Buddy
- Spring faz, mas sofre

#### 5. **C# / .NET** ⭐⭐⭐
```csharp
// Reflection + Expression Trees
var user = Activator.CreateInstance(userType);
var prop = userType.GetProperty("Username");

// Source Generators (C# 9+) são EXCELENTES
[AutoGenerateAPI]
public class User { }  // Gera API em compile time!
```
**Por quê?**
- Melhor que Java (LINQ, Expression Trees)
- Source Generators modernos ajudam
- Entity Framework usa reflection
- Mas ainda é estaticamente tipado

#### 6. **Go** ⭐
```go
// Reflection limitado
t := reflect.TypeOf(user)
field := t.Field(0)  // 😞 Sem generics decentes até Go 1.18

// Geração de código via go generate é comum
//go:generate go run gen.go
```
**Por quê?**
- Filosofia minimalista não gosta de "mágica"
- Reflection fraco
- Sem generics poderosos
- Prefere código explícito

---

### 🔴 **Linguagens RUINS para Lazy Ninja**

#### 7. **Rust** ⭐
```rust
// Type system EXTREMAMENTE rígido
// Macros procedurais são poderosos MAS...

#[derive(CRUD)]  // Macro gera código
struct User {
    username: String,  // ❌ Tipos devem ser conhecidos em compile time
}

// Runtime reflection? NÃO EXISTE (por design!)
```
**Por quê?**
- Zero-cost abstractions = zero runtime magic
- Tipos devem ser conhecidos em compile time
- Ownership/borrowing complica reflexão
- Filosofia: "explícito > implícito"

#### 8. **C++** ⭐
```cpp
// Sem reflection nativa (até C++26?)
// Templates são poderosos mas complexos

template<typename T>
class API {
    // ❌ Não conseguimos iterar fields de T em runtime
};

// Bibliotecas como Boost.Hana tentam, mas é DIFÍCIL
```
**Por quê?**
- Sem reflection (proposals há décadas)
- Templates são compile time only
- Metaprogramação via templates é pesadelo

#### 9. **Haskell** ⭐⭐
```haskell
-- Type system avançado MAS rígido
data User = User { username :: String }

-- Template Haskell existe mas é complexo
$(deriveJSON defaultOptions ''User)  -- Gera JSON codec

-- Tipos fantasma, GADTs... muito acadêmico
```
**Por quê?**
- Pureza funcional complica mutação
- Type system forte demais
- Comunidade prefere explícito
- Template Haskell é nicho

---

## Ranking Final para Lazy Ninja

| Linguagem | Nota | Por quê? |
|-----------|------|----------|
| **Ruby** | 🏆 10/10 | Feita para isso (Rails!) |
| **Elixir** | 🥈 10/10 | Macros higiênicas são perfeitas |
| **Python** | 🥉 9/10 | Dinâmico + bibliotecas ricas (atual!) |
| **JavaScript** | 8/10 | Proxies + TS avançado |
| **C#** | 6/10 | Source Generators salvam |
| **Java** | 5/10 | Possível mas doloroso |
| **Go** | 3/10 | Filosofia contra metaprogramação |
| **Rust** | 2/10 | Type system trava tudo |
| **C++** | 2/10 | Sem reflection |
| **Haskell** | 2/10 | Acadêmico demais |

### Por Que Python Foi Escolhido?

✅ **Vantagens:**
1. **Ecossistema Django** - Django ORM já existe
2. **Pydantic** - Validação + serialização fácil
3. **Adoção** - Muitos desenvolvedores conhecem
4. **Flexibilidade** - Metaprogramação é natural
5. **Prototipagem rápida** - Lazy Ninja surgiu rápido

⚠️ **Desvantagens:**
1. Type checking estático irritante
2. Performance inferior (mas OK para APIs)
3. GIL (não usa multi-core bem)

### Conclusão

**Python é a escolha certa para Lazy Ninja!**

- Ruby seria melhor tecnicamente, mas Django >> Rails (em 2026)
- Elixir seria excelente, mas ecossistema menor
- TypeScript seria ótimo, mas não tem Django
- Linguagens compiladas estaticamente matam a proposta

**O problema de tipagem é aceitável** porque:
- Só afeta desenvolvimento (não runtime)
- Tem workarounds (cast, type guards)
- Trade-off vale a pena pela produtividade

---

## Soluções Aplicadas

### 1. ✅ **`TYPE_CHECKING` para imports condicionais**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from django.db.models.fields.related import Field
```

**Benefício**: Tipos disponíveis para o type checker, mas sem overhead em runtime.

### 2. ✅ **`cast()` para conversão explícita**

```python
from typing import cast

def _serialize_user(user: Any) -> dict:
    schema_instance = UserPublicSchema.model_validate(user)
    return cast(dict, schema_instance.model_dump())
```

**Benefício**: Informa ao type checker o tipo esperado sem validação em runtime.

### 3. ✅ **Type Guards para validação segura**

```python
def _has_username_field() -> bool:
    """Check if User model has a unique username field."""
    if not hasattr(User, "username"):
        return False
    try:
        field = User._meta.get_field("username")
        return getattr(field, "unique", False)
    except Exception:
        return False

# Uso:
if _has_username_field():
    # Type checker sabe que username existe aqui
    User.objects.filter(username__iexact=username)
```

**Benefício**: Encapsula verificações complexas, reduz warnings.

### 4. ✅ **Usar `dict` ao invés de schema dinâmico**

```python
# ❌ Antes
class AuthResponseSchema(TokenPairSchema):
    user: UserPublicSchema  # type: ignore[valid-type]

# ✅ Depois
class AuthResponseSchema(TokenPairSchema):
    user: dict  # Dynamic schema from generate_schema
```

**Benefício**: Aceita qualquer dict, que é o que realmente retornamos.

### 5. ✅ **Documentação clara em docstrings**

```python
def _generate_token(user: Any, *, expires_in: int, token_type: str) -> str:
    """Generate JWT token for user.
    
    Args:
        user: Django user instance (requires .id attribute)
        expires_in: Token lifetime in seconds
        token_type: Token type ("access" or "refresh")
    """
```

**Benefício**: Desenvolvedores entendem o contrato mesmo sem tipos perfeitos.

### 6. ✅ **Verificação de métodos antes de usar**

```python
user_manager = User.objects
if not hasattr(user_manager, "create_user"):
    raise RuntimeError("User model must have a create_user method")

user = user_manager.create_user(**user_kwargs)
```

**Benefício**: Falha rápido com erro claro, sem `type: ignore`.

## Quando `type: ignore` é Aceitável

Em bibliotecas dinâmicas como Lazy Ninja, alguns `type: ignore` são inevitáveis:

### ✅ Aceitável:
```python
# Schemas gerados dinamicamente que não podemos tipar estaticamente
schema_class = create_dynamic_schema(model)  # type: ignore[misc]
```

### ❌ Evitar:
```python
# Quando existe alternativa melhor com cast/type guard
user.username  # type: ignore[attr-defined]  # Use type guard!
```

## Alternativas Avançadas

### Para Projetos Maiores:

1. **django-stubs**: Melhora tipagem Django
```bash
pip install django-stubs
```

2. **Protocol Types**: Para contratos de interface
```python
from typing import Protocol

class HasUsername(Protocol):
    username: str

def process_user(user: HasUsername) -> str:
    return user.username  # ✅ Type safe!
```

3. **Stub Files (.pyi)**: Para código muito dinâmico
```python
# lazy_ninja.pyi
def generate_schema(model: Type[Model], **kwargs) -> Type[Schema]: ...
```

## Resumo

- ✅ Use `cast()` quando você sabe o tipo mas o type checker não
- ✅ Use Type Guards para verificações complexas
- ✅ Use `TYPE_CHECKING` para imports pesados
- ✅ Use `dict` para schemas dinâmicos
- ✅ Documente contratos em docstrings
- ⚠️ Use `type: ignore` apenas quando inevitável
- ❌ Nunca ignore erros reais de tipo!

## Configuração do Pylance (pyproject.toml)

```toml
[tool.pylance]
typeCheckingMode = "basic"  # ou "standard" para libs
reportGeneralTypeIssues = "warning"
reportAttributeAccessIssue = "warning"
reportUnknownMemberType = "none"  # Para código muito dinâmico
```

Isso balanceia segurança de tipos com flexibilidade necessária para bibliotecas dinâmicas.
