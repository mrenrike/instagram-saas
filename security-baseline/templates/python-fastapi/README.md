# Módulo de segurança para Python/FastAPI

A implementação de referência não é duplicada aqui — ela vive em
[`backend/security/`](../../../backend/security/) na raiz deste repositório, onde é
exercitada pelos testes em `backend/tests/test_security.py`. Um template copiado
diverge silenciosamente do código que roda; um módulo testado, não.

## Copiar para outro projeto

```bash
cp -r backend/security /caminho/do/projeto/backend/security
cp backend/tests/test_security.py /caminho/do/projeto/backend/tests/
```

Dependências: apenas `starlette` e `pydantic` (que qualquer projeto FastAPI já tem).
Nada de novo entra no `requirements.txt`.

## Ligar no app

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .security import (
    BodySizeLimitMiddleware,
    HTTPSRedirectMiddleware,
    SecurityHeadersMiddleware,
    build_csp,
)

app = FastAPI(
    # Item 17 — o schema enumera toda rota e todo parâmetro.
    docs_url=None if IS_PRODUCTION else "/docs",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# A ordem importa. O middleware adicionado por último é o mais externo, então este
# empilhamento faz o redirect de HTTPS rodar antes de qualquer rota ler o corpo, e os
# cabeçalhos envolverem inclusive as respostas de erro.
app.add_middleware(SecurityHeadersMiddleware, csp=build_csp(), trust_proxy=True)   # 18
app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=256 * 1024)             # 16
app.add_middleware(HTTPSRedirectMiddleware, enabled=IS_PRODUCTION)                 # 19
app.add_middleware(                                                               # 18
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # nunca ["*"]
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)
```

## Rate limit num endpoint (item 11)

```python
from fastapi import Depends
from .security import RateLimiter, rate_limit

_login_limiter = RateLimiter(5, 300, name="login")   # 5 tentativas / 5 min

@router.post("/login", dependencies=[Depends(rate_limit(_login_limiter))])
async def login(...):
    ...
    await _login_limiter.reset(key)   # zere a contagem só quando o login der certo
```

## Corpo de requisição (itens 8, 14)

```python
from pydantic import Field
from .security import StrictModel

class CreateOrder(StrictModel):        # extra="forbid" — campo desconhecido dá 422
    product_id: str = Field(max_length=64)
    quantity: int = Field(ge=1, le=100)
    # Sem campo `price`: o preço vem do banco, no servidor.
```

## Acesso a registro (item 7)

```python
from .security import sign_resource_token, verify_resource_token

token = sign_resource_token(order_id, SIGNING_KEY, ttl_seconds=3600, scope="order")
verify_resource_token(token, order_id, SIGNING_KEY, scope="order")  # levanta se inválido
```

Derive `SIGNING_KEY` da chave mestra em vez de reusá-la:

```python
SIGNING_KEY = hkdf_expand(MASTER_KEY, b"order-access-token")
```

## O que o módulo não faz

- **Rate limit distribuído.** A janela é por processo. Com mais de um worker ou mais
  de uma instância, troque o armazenamento por Redis.
- **Hash de senha de usuário.** `secrets.py` usa PBKDF2, adequado para segredo de
  máquina. Para senha de pessoa, use `argon2-cffi` ou `passlib[bcrypt]`.
- **CSRF token.** Só é necessário em autenticação por cookie; o módulo assume token
  em header. Se usar cookie de sessão, adicione CSRF.
- **Validação de magic bytes em upload.** `validate_upload` checa extensão, tipo
  declarado e tamanho. Para arquivo que será renderizado ou executado, valide também
  os bytes iniciais com `python-magic`.
