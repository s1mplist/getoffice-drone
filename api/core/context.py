import re
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator
from api.utils.notion import format_br_date

ImgList = List[HttpUrl]


class Logo(BaseModel):
    header_logo_url: str = Field(description="URL do logo do cabeçalho")
    foot_logo_url: str = Field(description="URL do logo da empresa")


class Empresa(BaseModel):
    nome: str = Field(description="Nome da empresa")
    cnpj: str = Field(description="CNPJ da empresa")
    logo: Optional[Logo] = Field(default=None, description="Logos da empresa")


class Gerais(BaseModel):
    data_inicio: str = Field(description="Data de início da aplicação")
    data_fim: str = Field(description="Data de término da aplicação")
    data_emissao: date = Field(
        default_factory=date.today, description="Data de emissão do relatório"
    )
    cidade_uf: str = Field(default=None, description="Cidade e UF da aplicação")
    cliente: str = Field(description="Nome do cliente")
    fazenda: str = Field(description="Nome da fazenda")
    cultura: List[str] = Field(description="Cultura aplicada")
    hectares: float = Field(description="Hectares pulverizados")
    doc_numero: str = Field(description="Número do documento")
    footer_msg: str = Field(
        default="GetOffice - Gestão em drones agrícolas",
        description="Mensagem do rodapé",
    )

    @property
    def date(self) -> Optional[str]:
        return format_br_date(self.data_inicio)

    @property
    def cultura_hectares(self) -> str:
        return f"{self.cultura[0]} - {self.hectares}"


class Geografia(BaseModel):
    coordenada: str = Field(description="Coordenada geográfica")
    hectares: float = Field(description="Hectares pulverizados")


class Drone(BaseModel):
    drone: str = Field(description="Modelo do drone")
    bico: Optional[str] = Field(default=None, description="Tipo de bico do drone")
    gota: Optional[str] = Field(default=None, description="Tipo de gota utilizada")

    @staticmethod
    def _split_model_prefix(value: str) -> tuple[str, Optional[str]]:
        # Prioritize 'PS' token: left => modelo, right => prefixo
        m = re.search(r"\bps\b", value, flags=re.IGNORECASE)
        if m:
            left = value[: m.start()].strip()
            right = value[m.end() :].strip()
            # normaliza separadores residuais
            left = re.sub(r"[-–—]\s*$", "", left).strip()
            right = re.sub(r"^\s*[-–—]", "", right).strip()
            # extrai dígitos do lado direito como prefixo
            # se não houver dígitos, usa a string direita inteira
            pm = re.search(r"(\d+)", right)
            prefix = pm.group(1) if pm else (right or None)
            return (left or value, prefix)

        # Fallback: comport. anterior (split por traços e heurísticas)
        parts = [p.strip() for p in re.split(r"[-–—]", value) if p.strip()]
        model_parts: list[str] = []
        prefix: Optional[str] = None
        for p in parts:
            if re.fullmatch(r"\d+", p):
                prefix = p
            elif p.lower().startswith("ps"):
                m2 = re.search(r"(\d+)", p)
                if m2:
                    prefix = m2.group(1)
            else:
                model_parts.append(p)
        model = (
            " - ".join(model_parts).strip()
            if model_parts
            else (parts[0] if parts else value)
        )
        return model, prefix

    @model_validator(mode="before")
    def _parse_model_and_prefix(cls, values: dict) -> dict:
        # accept either 'modelo' or legacy 'drone' raw value
        raw = values.get("modelo") or values.get("drone")
        if isinstance(raw, str) and raw.strip():
            model, prefix = cls._split_model_prefix(raw)
            values["modelo"] = model or raw
            if prefix and not values.get("prefixo"):
                values["prefixo"] = prefix
        return values

    @property
    def modelo(self) -> str:
        model, _ = self._split_model_prefix(self.drone)
        return model

    @property
    def prefixo(self) -> str:
        _, prefix = self._split_model_prefix(self.drone)
        return prefix


class Equipe(BaseModel):
    piloto: str = Field(description="Nome do piloto")
    caar: str = Field(description="CAAR do piloto")
    assistente: Optional[str] = Field(description="Nome do assistente")
    altura: float = Field(description="Altura de voo em metros")
    drone: Drone = Field(description="Informações do drone utilizado")


class Midia(BaseModel):
    mapa: ImgList = Field(description="Imagens do mapa da aplicação")
    alvo: ImgList = Field(
        description="Imagens do papel hidrosensivel comprovando a aplicação"
    )
    produto: ImgList = Field(description="Imagens da calda preparada/PH")
    clima: ImgList = Field(description="Imagens das condições climáticas")


class Produto(BaseModel):
    nome: str = Field(description="Nome do produto utilizado")
    dosagem: str = Field(description="Dosagem do produto utilizado")


class Clima(BaseModel):
    temperatura: Optional[float] = Field(description="Temperatura durante a aplicação")
    umidade: Optional[float] = Field(
        description="Umidade relativa do ar durante a aplicação"
    )
    vento: Optional[float] = Field(
        description="Velocidade do vento durante a aplicação"
    )
