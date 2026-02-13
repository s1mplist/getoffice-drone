import re
import unicodedata
from datetime import date, datetime
from functools import lru_cache
from logging import getLogger
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

logger = getLogger(__name__)
DATE_FORMAT = "%d/%m/%Y"


def _string_contains_time(s: str) -> bool:
    """Detecta se a string contém um componente de hora (HH:MM).

    Aceita formatos como 'YYYY-MM-DDTHH:MM', 'YYYY-MM-DD HH:MM', ou qualquer
    ocorrência de '\\d{2}:\\d{2}' na string.
    """
    if not s or not isinstance(s, str):
        return False
    return bool(re.search(r"\d{2}:\d{2}", s))


def format_br_date(value):
    """Formata date/datetime/strings ISO para padrão BR.

    - Se receber um objeto `date` -> `DD/MM/YYYY`
    - Se receber um objeto `datetime` -> `DD/MM/YYYY HH:MM:SS` (00:00:00)
    - Se receber `str` -> tenta parse ISO; se a string contém hora, trata como datetime,
      caso contrário como date.
    - Em falha de parse retorna a string original.
    """
    logger.debug("Formatting date value: %r", value)

    # objetos já tipados
    if isinstance(value, datetime):
        if value.time() == datetime.min.time():
            return value.date().strftime(DATE_FORMAT)
        return value.strftime(f"{DATE_FORMAT} %H:%M:%S")

    if isinstance(value, date):
        return value.strftime(DATE_FORMAT)

    # strings (vêm do Notion como ISO strings frequentemente)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        # normaliza 'Z' -> '+00:00' para fromisoformat
        iso = s.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso)
            # se a string contém hora explicitamente, preserva hora
            if _string_contains_time(s) or parsed.time() != datetime.min.time():
                return parsed.strftime(f"{DATE_FORMAT} %H:%M:%S")
            return parsed.date().strftime(DATE_FORMAT)
        except Exception:
            # fallback: se contém padrão HH:MM, retorna a string tal qual
            if _string_contains_time(s):
                return s
            # tenta parse de date-only
            try:
                parsed_date = date.fromisoformat(s)
                return parsed_date.strftime(DATE_FORMAT)
            except Exception:
                return s

    return ""


# --------------------
# Normalization
# --------------------
def _normalize_prop_name_impl(name: str) -> str:
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    s = no_accents.lower()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalize_property_name_flexible_impl(name: str) -> str:
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    normalized = no_accents.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


cached_normalize_prop_name = lru_cache(maxsize=2048)(_normalize_prop_name_impl)
cached_normalize_prop_name_flexible = lru_cache(maxsize=2048)(
    _normalize_property_name_flexible_impl
)


def normalize_prop_name(name: str) -> str:
    try:
        return cached_normalize_prop_name(name or "")
    except Exception:  # pragma: no cover
        logger.exception("Error normalizing property name")
        return ""


def normalize_property_name_flexible(name: str) -> str:
    try:
        return cached_normalize_prop_name_flexible(name or "")
    except Exception:  # pragma: no cover
        logger.exception("Error in flexible normalization")
        return ""


def to_snake(name: str) -> str:
    n = normalize_prop_name(name)
    if not n:
        return ""
    s = re.sub(r"\s+", "_", n)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def normalize_properties(props: Mapping[str, Any]) -> Dict[str, Tuple[str, Any]]:
    if not props:
        return {}
    norm: Dict[str, Tuple[str, Any]] = {}
    for orig_key, val in props.items():
        if not isinstance(orig_key, str):
            continue
        snake = to_snake(orig_key)
        if not snake:
            continue
        if snake not in norm:
            norm[snake] = (orig_key, val)
    return norm


# --------------------
# Regex search helper
# --------------------
def find_property_by_regex(props: Mapping[str, Any], pattern: str) -> Optional[Any]:
    if not props or not pattern:
        return None
    try:
        reg = re.compile(pattern, flags=re.IGNORECASE)
    except re.error:
        logger.warning("Invalid regex in find_property_by_regex: %s", pattern)
        return None

    norm = normalize_properties(props)
    for snake, (_, val) in norm.items():
        if reg.search(snake):
            return val

    for orig_key, val in props.items():
        nk = normalize_property_name_flexible(orig_key)
        if reg.search(nk):
            return val
    return None


# --------------------
# Rich text / title extraction
# --------------------
def plain_text(rich: Iterable[Mapping[str, Any]]) -> str:
    if not rich:
        return ""
    parts: List[str] = []
    for seg in rich:
        if not isinstance(seg, Mapping):
            continue
        pt = seg.get("plain_text") or (seg.get("text") or {}).get("content") or ""
        if pt:
            parts.append(str(pt))
    return "".join(parts)


def extract_title(prop: Mapping[str, Any]) -> str:
    return plain_text(prop.get("title") or [])


def extract_rich_text(prop: Mapping[str, Any]) -> str:
    return plain_text(prop.get("rich_text") or [])


# --------------------
# Other extractors
# --------------------
def extract_relation_ids(prop: Mapping[str, Any]) -> List[str]:
    rel = prop.get("relation") or []
    ids: List[str] = []
    for r in rel:
        if not isinstance(r, Mapping):
            continue
        rid = r.get("id")
        if rid:
            ids.append(str(rid).replace("-", ""))
    return ids


def extract_files(prop: Mapping[str, Any]) -> List[str]:
    files: List[str] = []
    for f in prop.get("files") or []:
        if not isinstance(f, Mapping):
            continue
        ftype = f.get("type")
        if ftype == "file":
            url = (f.get("file") or {}).get("url")
            if url:
                files.append(url)
        elif ftype == "external":
            url = (f.get("external") or {}).get("url")
            if url:
                files.append(url)
    return files


def _select_name(prop: Mapping[str, Any]) -> Optional[str]:
    sel = prop.get("select")
    return sel.get("name") if isinstance(sel, Mapping) else None


def _multi_select_names(prop: Mapping[str, Any]) -> List[str]:
    return [
        s.get("name")
        for s in (prop.get("multi_select") or [])
        if isinstance(s, Mapping) and s.get("name") is not None
    ]


def _people_list(prop: Mapping[str, Any]) -> List[str]:
    return [
        p.get("name") or (p.get("person") or {}).get("email") or p.get("id")
        for p in (prop.get("people") or [])
        if isinstance(p, Mapping)
    ]


def extract_rollup(prop: Mapping[str, Any]) -> Any:
    roll = prop.get("rollup") or {}
    rtype = roll.get("type")

    if rtype == "array":
        arr = roll.get("array") or []
        values: List[Any] = []
        for item in arr:
            v = simplify_property(item if isinstance(item, Mapping) else {})
            if v is None or v == "":
                continue
            if isinstance(v, list):
                values.extend(v)
            else:
                values.append(v)
        if not values:
            return None
        return values[0] if len(values) == 1 else values

    for key in ("number", "date", "string", "boolean"):
        if key in roll:
            return roll.get(key)
    return None


def extract_date(prop: Mapping[str, Any]) -> Optional[str]:
    d = prop.get("date") or {}
    return d.get("start") or d.get("end")


def extract_user(user: Mapping[str, Any]) -> Optional[str]:
    return user.get("name") or (user.get("person") or {}).get("email") or user.get("id")


def extract_formula(prop: Mapping[str, Any]) -> Any:
    formula = prop.get("formula") or {}
    ftype = formula.get("type")
    if ftype == "string":
        return formula.get("string")
    if ftype == "number":
        return formula.get("number")
    if ftype == "boolean":
        return formula.get("boolean")
    if ftype == "date":
        return extract_date(formula)
    return None


def _status_name(prop: Mapping[str, Any]) -> Optional[str]:
    s = prop.get("status")
    return s.get("name") if isinstance(s, Mapping) else None


def _created_by(prop: Mapping[str, Any]) -> Optional[str]:
    return extract_user(prop.get("created_by") or {})


def _last_edited_by(prop: Mapping[str, Any]) -> Optional[str]:
    return extract_user(prop.get("last_edited_by") or {})


def _unique_id(prop: Mapping[str, Any]) -> Optional[str]:
    uid = prop.get("unique_id") or {}
    prefix = uid.get("prefix")
    number = uid.get("number")
    if number is None:
        return None
    return f"{prefix}{number}" if prefix else str(number)


def _verification(prop: Mapping[str, Any]) -> Any:
    ver = prop.get("verification") or {}
    return ver.get("state") or ver


# --------------------
# Public simplification API
# --------------------
def simplify_property(prop: Mapping[str, Any]) -> Any:
    if not isinstance(prop, Mapping):
        return None
    ptype = prop.get("type")
    handler = _PROPERTY_EXTRACTORS.get(ptype)
    if handler:
        return handler(prop)
    logger.debug("Unknown Notion property type: %r", ptype)
    return None


def simplify_properties_map(props: Mapping[str, Any]) -> Dict[str, Any]:
    norm = normalize_properties(props)
    simplified: Dict[str, Any] = {}
    for snake, (_orig, raw) in norm.items():
        simplified[snake] = simplify_property(
            raw if isinstance(raw, Mapping) else {"type": None}
        )
    return simplified


_PROPERTY_EXTRACTORS: Dict[str, Callable[[Mapping[str, Any]], Any]] = {
    "rollup": extract_rollup,
    "title": lambda prop: extract_title(prop),
    "rich_text": lambda prop: extract_rich_text(prop),
    "number": lambda prop: prop.get("number"),
    "select": _select_name,
    "multi_select": _multi_select_names,
    "relation": extract_relation_ids,
    "people": _people_list,
    "date": extract_date,
    "checkbox": lambda prop: prop.get("checkbox"),
    "url": lambda prop: prop.get("url"),
    "email": lambda prop: prop.get("email"),
    "phone_number": lambda prop: prop.get("phone_number"),
    "status": _status_name,
    "files": extract_files,
    "formula": extract_formula,
    "created_by": _created_by,
    "last_edited_by": _last_edited_by,
    "created_time": lambda prop: prop.get("created_time"),
    "last_edited_time": lambda prop: prop.get("last_edited_time"),
    "unique_id": _unique_id,
    "verification": _verification,
}
