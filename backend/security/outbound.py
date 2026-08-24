"""Chamadas HTTP de saída seguras (itens 14, 19).

``urllib.request.urlopen`` aceita qualquer esquema que o opener conheça — inclusive
``file://``, ``ftp://`` e ``data:``. Enquanto a URL for uma constante do código isso
é inofensivo, mas basta um refactor que monte a URL a partir de um webhook, de um
campo de config ou de uma resposta de terceiro para virar SSRF ou leitura de arquivo
local. Este wrapper recusa tudo que não for HTTPS, antes de abrir a conexão.
"""
from __future__ import annotations

import urllib.request
from urllib.parse import urlparse

ALLOWED_SCHEMES = frozenset({"https"})


class UnsafeURL(ValueError):
    pass


def _check(url: str) -> None:
    scheme = urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeURL(f"esquema não permitido em chamada de saída: {scheme or '(vazio)'}")


def safe_urlopen(req: urllib.request.Request | str, timeout: float = 15):
    """``urlopen`` restrito a HTTPS.

    Também desliga o redirecionamento automático para outro esquema: um 302 de
    ``https://`` para ``file:///etc/passwd`` seria seguido em silêncio pelo opener
    padrão.
    """
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    _check(url)

    opener = urllib.request.build_opener(_HTTPSOnlyRedirectHandler)
    return opener.open(req, timeout=timeout)


class _HTTPSOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
