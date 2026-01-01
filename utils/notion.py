import re
import unicodedata
from functools import lru_cache
from logging import Logger, getLogger
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


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


# Cache normalization results for performance across many properties
cached_normalize_prop_name = lru_cache(maxsize=2048)(_normalize_prop_name_impl)
cached_normalize_prop_name_flexible = lru_cache(maxsize=2048)(
    _normalize_property_name_flexible_impl
)


class NotionUtils:
    """Utilities to safely extract and normalize Notion API objects.

    Focused responsibilities:
    - Normalize property names deterministically
    - Extract plain values from Notion property payloads
    - Provide small, testable public API for mapping/simplifying properties

    Design notes:
    - Logger can be injected for testability/DI
    - Normalization is cached to improve performance when processing many pages
    - Methods do not raise for malformed inputs; they return sensible defaults
    """

    def __init__(self, logger: Optional[Logger] = None) -> None:
        self.logger = logger or getLogger(__name__)
        self.logger.debug("NotionUtils initialized")

    # --------------------
    # Normalization
    # --------------------
    def normalize_prop_name(self, name: str) -> str:
        """Normalize a property name (remove accents/punctuation, lowercase)."""
        try:
            return cached_normalize_prop_name(name or "")
        except Exception:  # pragma: no cover - defensive
            self.logger.exception("Error normalizing property name")
            return ""

    def normalize_property_name_flexible(self, name: str) -> str:
        """More permissive normalization for flexible matching."""
        try:
            return cached_normalize_prop_name_flexible(name or "")
        except Exception:  # pragma: no cover - defensive
            self.logger.exception("Error in flexible normalization")
            return ""

    def to_snake(self, name: str) -> str:
        """Convert a name to deterministic snake_case using normalized input."""
        n = self.normalize_prop_name(name)
        if not n:
            return ""
        s = re.sub(r"\s+", "_", n)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    def normalize_properties(self, props: Mapping[str, Any]) -> Dict[str, Tuple[str, Any]]:
        """Return mapping snake_name -> (original_key, original_value).

        The first occurrence wins to avoid nondeterministic overwrites.
        """
        if not props:
            return {}
        norm: Dict[str, Tuple[str, Any]] = {}
        for orig_key, val in props.items():
            if not isinstance(orig_key, str):
                continue
            snake = self.to_snake(orig_key)
            if not snake:
                continue
            if snake not in norm:
                norm[snake] = (orig_key, val)
        return norm

    # --------------------
    # Regex search helper
    # --------------------
    def find_property_by_regex(self, props: Mapping[str, Any], pattern: str) -> Optional[Any]:
        """Find a property value by applying `pattern` to normalized snake names.

        Returns the raw property value (as returned by Notion) or None.
        """
        if not props or not pattern:
            return None
        try:
            reg = re.compile(pattern, flags=re.IGNORECASE)
        except re.error:
            self.logger.warning("Invalid regex in find_property_by_regex: %s", pattern)
            return None

        norm = self.normalize_properties(props)
        for snake, (_, val) in norm.items():
            if reg.search(snake):
                return val

        # Fallback: test looser normalized names
        for orig_key, val in props.items():
            nk = self.normalize_prop_name(orig_key)
            if reg.search(nk):
                return val
        return None

    # --------------------
    # Rich text / title extraction
    # --------------------
    def plain_text(self, rich: Iterable[Mapping[str, Any]]) -> str:
        """Extract `plain_text` (or text.content) from rich text arrays.

        Returns a concatenated string. Ignores malformed segments.
        """
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

    def extract_title(self, prop: Mapping[str, Any]) -> str:
        return self.plain_text(prop.get("title") or [])

    def extract_rich_text(self, prop: Mapping[str, Any]) -> str:
        return self.plain_text(prop.get("rich_text") or [])

    # --------------------
    # Other extractors
    # --------------------
    def extract_relation_ids(self, prop: Mapping[str, Any]) -> List[str]:
        rel = prop.get("relation") or []
        ids: List[str] = []
        for r in rel:
            if not isinstance(r, Mapping):
                continue
            rid = r.get("id")
            if rid:
                ids.append(str(rid).replace("-", ""))
        return ids

    def extract_files(self, prop: Mapping[str, Any]) -> List[str]:
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

    def extract_rollup(self, prop: Mapping[str, Any]) -> Any:
        roll = prop.get("rollup") or {}
        rtype = roll.get("type")
        if rtype == "array":
            arr = roll.get("array") or []
            values: List[Any] = []
            for item in arr:
                if not isinstance(item, Mapping):
                    continue
                itype = item.get("type")
                if itype in ("rich_text", "title"):
                    values.append(self.plain_text(item.get(itype) or []))
                elif itype == "number":
                    values.append(item.get("number"))
                elif itype == "relation":
                    rels = item.get("relation") or []
                    values.extend([r.get("id", "").replace("-", "") for r in rels if r.get("id")])
                else:
                    for v in item.values():
                        if isinstance(v, list):
                            for seg in v:
                                if isinstance(seg, Mapping):
                                    pt = seg.get("plain_text")
                                    if pt:
                                        values.append(pt)
            if not values:
                return None
            return values[0] if len(values) == 1 else values
        for key in ("number", "date", "string", "boolean"):
            if key in roll:
                return roll.get(key)
        return None

    def extract_date(self, prop: Mapping[str, Any]) -> Dict[str, Optional[str]]:
        d = prop.get("date") or {}
        return {"start": d.get("start"), "end": d.get("end")}

    # --------------------
    # Public simplification API
    # --------------------
    def simplify_property(self, prop: Mapping[str, Any]) -> Any:
        """Map Notion property payload to simple Python values.

        Returns None when property type is unknown or not present.
        """
        if not isinstance(prop, Mapping):
            return None
        ptype = prop.get("type")
        if ptype == "rollup":
            return self.extract_rollup(prop)
        if ptype == "title":
            return self.extract_title(prop)
        if ptype == "rich_text":
            return self.extract_rich_text(prop)
        if ptype == "number":
            return prop.get("number")
        if ptype == "select":
            sel = prop.get("select")
            return sel.get("name") if isinstance(sel, Mapping) else None
        if ptype == "multi_select":
            return [
                s.get("name")
                for s in (prop.get("multi_select") or [])
                if isinstance(s, Mapping) and s.get("name") is not None
            ]
        if ptype == "relation":
            return self.extract_relation_ids(prop)
        if ptype == "people":
            return [
                p.get("name")
                for p in (prop.get("people") or [])
                if isinstance(p, Mapping) and p.get("name") is not None
            ]
        if ptype == "date":
            return self.extract_date(prop)
        if ptype == "checkbox":
            return prop.get("checkbox")
        if ptype == "url":
            return prop.get("url")
        if ptype == "email":
            return prop.get("email")
        if ptype == "phone_number":
            return prop.get("phone_number")
        if ptype == "status":
            s = prop.get("status")
            return s.get("name") if isinstance(s, Mapping) else None
        if ptype == "files":
            return self.extract_files(prop)
        self.logger.debug("Unknown Notion property type: %r", ptype)
        return None

    def simplify_properties_map(self, props: Mapping[str, Any]) -> Dict[str, Any]:
        """Return mapping snake_name -> simplified value for all properties.

        This is a convenience for working with `notion_client` page results.
        """
        norm = self.normalize_properties(props)
        simplified: Dict[str, Any] = {}
        for snake, (_orig, raw) in norm.items():
            simplified[snake] = self.simplify_property(
                raw if isinstance(raw, Mapping) else {"type": None}
            )
        return simplified
