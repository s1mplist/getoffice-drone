from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl

ImgList = List[HttpUrl]


class Logo(BaseModel):
    header_logo_url: str = Field(description="URL do logo do cabeçalho")
    foot_logo_url: str = Field(description="URL do logo da empresa")


class Empresa(BaseModel):
    nome: str = Field(description="Nome da empresa")
    cnpj: str = Field(description="CNPJ da empresa")
    logo: Optional[Logo] = Field(default=None, description="Logos da empresa")


class Gerais(BaseModel):
    data_inicio: date = Field(description="Data de início da aplicação")
    data_fim: date = Field(description="Data de término da aplicação")
    data_emissao: date = Field(
        default_factory=date.today, description="Data de emissão do relatório"
    )
    cidade_uf: str = Field(default=None, description="Cidade e UF da aplicação")
    cliente: str = Field(description="Nome do cliente")
    fazenda: str = Field(description="Nome da fazenda")
    hectares: float = Field(description="Hectares pulverizados")
    doc_numero: str = Field(description="Número do documento")
    footer_msg: str = Field(
        default="GetOffice - Gestão em drones agrícolas",
        description="Mensagem do rodapé",
    )


class Geografia(BaseModel):
    coordenada: str = Field(description="Coordenada geográfica")
    hectares: float = Field(description="Hectares pulverizados")


class Drone(BaseModel):
    modelo: str = Field(description="Modelo do drone")
    prefixo: str = Field(description="Prefixo do drone")
    bico: Optional[str] = Field(default=None, description="Tipo de bico do drone")
    gota: Optional[str] = Field(default=None, description="Tipo de gota utilizada")


class Equipe(BaseModel):
    piloto: str = Field(description="Nome do piloto")
    caar: str = Field(description="CAAR do piloto")
    assistente: Optional[str] = Field(description="Nome do assistente")
    altura: int = Field(description="Altura de voo em metros")
    drone: Drone = Field(description="Informações do drone utilizado")


class Midia(BaseModel):
    mapa: ImgList = Field(description="Imagens do mapa da aplicação")
    alvo: ImgList = Field(
        description="Imagens do papel hidrosensivel comprovando a aplicação"
    )  # noqa: E501
    produto: ImgList = Field(description="Imagens da calda preparada/PH")
    clima: ImgList = Field(description="Imagens das condições climáticas")


class Produto(BaseModel):
    nome: str = Field(description="Nome do produto utilizado")
    dosagem: str = Field(description="Dosagem do produto utilizado")
