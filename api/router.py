import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from api.core.context import (
    Clima,
    Drone,
    Empresa,
    Equipe,
    Geografia,
    Gerais,
    Midia,
    Produto,
)
from api.core.delta import get_delta_t_image
from api.core.notion import Notion
from api.core.settings import get_settings
from api.utils.produtos import parse_produtos

logger = logging.getLogger(__name__)

router = APIRouter()
# Use absolute path relative to this file's location
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/drone/{page_id}", tags=["Notion"])
async def get_drone_report(request: Request, page_id: str):
    logger.debug(f"Received request for drone report with page ID: {page_id}")
    logger.info(request)

    async with Notion() as notion:
        response = await notion.get_page_data(page_id)
        logger.debug(f"Notion response data: {response}")
    logger.info(f"Fetched data for page ID {page_id}")

    empresa = Empresa(nome=response.get("empresa"), cnpj=response.get("cnpj"))
    gerais = Gerais(
        data_inicio=response.get("data_e_horario_de_inicio_das_aplicacoes"),
        data_fim=response.get("data_e_horario_de_encerramento_das_aplicacoes"),
        cidade_uf=response.get("cidade_e_estado", ""),
        hectares=response.get("hectares_pulverizados", 0.0),
        cliente=response.get("nome_do_produtor_completo"),
        fazenda=response.get("nome_da_fazenda"),
        doc_numero=response.get("id_interno", ""),
    )
    geografia = Geografia(
        coordenada=response.get("coordenada_geografica", ""),
        hectares=response.get("hectares_pulverizados", ""),
    )
    equipe = Equipe(
        piloto=response.get("piloto"),
        caar=response.get("caar", ""),
        altura=response.get("altura_de_voo", ""),
        assistente=response.get("assistente", ""),
        drone=Drone(
            modelo=response.get("drone"),
            prefixo=response.get("drone"),
            bico=response.get("drone_bico"),
            gota=response.get("rpm_tipo_de_gota")[0],
        ),
    )
    midia = Midia(
        mapa=response.get("mapa_aplicacao", []),
        alvo=response.get("papel_hidronssensivel", []),
        produto=response.get("foto_dos_produtos", []),
        clima=response.get("fotos_clima_anemometro_e_termo_higrometro", []),
    )

    # Parseia produtos do texto bruto
    texto_produtos = response.get("produtos_utilizados", "")
    lista_produtos = parse_produtos(texto_produtos)

    produtos = [Produto(nome=p["nome"], dosagem=p["dosagem"]) for p in lista_produtos]

    clima = Clima(
        temperatura=response.get("temperatura"),
        umidade=response.get("umidade"),
        vento=response.get("velocidade_vento"),
    )

    chart_base64 = get_delta_t_image(clima.temperatura, clima.umidade)

    # Prepara dados para o script de download PDF
    settings = get_settings()
    farm_code = gerais.fazenda.replace(" ", "-") if gerais.fazenda else "relatorio"
    today_date = str(gerais.data_inicio) if gerais.data_inicio else ""

    result = {
        "request": request,
        "data": gerais,
        "empresa": empresa,
        "geografia": geografia,
        "equipe": equipe,
        "midia": midia,
        "lista_produtos": lista_produtos,
        "produtos": produtos,
        "clima": clima,
        "chart_base64": f"data:image/png;base64,{chart_base64}",
        "farm_code": farm_code,
        "today_date": today_date,
        "pdf_service_url": settings.pdf_service_url,
    }

    logger.info(f"Rendering report for page ID {page_id}")
    logger.debug(f"Report context data: {result}")
    return templates.TemplateResponse("report.html", result)
    # return response
