import re


def parse_produtos(texto_produtos):
    """
    Parseia string de produtos em diversos formatos.

    Formatos suportados:
    - "Galopeiro 5 LTS"
    - "Dominum..2.5l"
    - "Break thru....100 ml"
    - "ADJUST SILVER 50 ml"
    - "Padron 01"

    Retorna lista de dicts: [{'nome': str, 'dosagem': str}, ...]
    """
    if not texto_produtos:
        return []

    produtos = []
    linhas = texto_produtos.strip().split("\n")

    for linha in linhas:
        linha = linha.strip()

        # Pula linhas vazias ou cabeçalhos genéricos
        if not linha or linha.lower() in ["dose por ha", "produtos", "calda"]:
            continue

        # Remove travessões/pontos múltiplos que separam nome e dosagem
        linha_limpa = re.sub(r"[\.—-]{2,}", " ", linha)

        # Tenta extrair: nome (até o número) + dosagem (número + unidade)
        # Regex: captura tudo antes do número, depois número + unidade opcional
        # Permite espaço opcional antes do número
        match = re.match(
            r"^(.+?)\s*(\d+(?:[.,]\d+)?)\s*(ml|mL|l|lt|lts|LTS|LT|L|grs?|gr|GR|GRS|kg|KG|g|G)?",
            linha_limpa,
            re.IGNORECASE,
        )

        if match:
            nome = match.group(1).strip()
            numero = match.group(2).replace(",", ".")
            unidade = match.group(3) if match.group(3) else ""

            # Limpa pontos/travessões extras do nome
            nome = re.sub(r"[\.—\s]+$", "", nome).strip()

            # Monta dosagem
            dosagem = f"{numero} {unidade}".strip()

            produtos.append({"nome": nome, "dosagem": dosagem})
        else:
            # Fallback: se não conseguiu parsear, coloca tudo como nome
            produtos.append({"nome": linha, "dosagem": "Não especificado"})

    return produtos
