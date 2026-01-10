import logging
from typing import Any, Dict, Optional

from notion_client import AsyncClient

from core.settings import get_settings
from utils.notion import simplify_properties_map

logger = logging.getLogger(__name__)
settings = get_settings()


class Notion:
    """Wrapper around Notion AsyncClient with async context management."""

    def __init__(self) -> None:
        self.notion_token = settings.notion_token
        self.database_id = settings.notion_database_id
        self._client: Optional[AsyncClient] = None
        logger.debug(f"Notion wrapper initialized with database_id: {self.database_id}")

    async def __aenter__(self) -> "Notion":
        """Open AsyncClient for use inside `async with`."""
        self._client = AsyncClient(auth=self.notion_token)
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Close AsyncClient when exiting `async with`."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> AsyncClient:
        """Create a client if not opened by context manager."""
        if self._client is None:
            logger.debug("Lazy-creating Notion AsyncClient (outside context manager).")
            self._client = AsyncClient(auth=self.notion_token)
        return self._client

    async def query_database(
        self, filter: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Query the Notion database."""
        logger.debug(f"Querying database {self.database_id} with filter: {filter}")
        try:
            client = self._ensure_client()
            result = await client.databases.query(
                database_id=self.database_id,
                filter=filter or {},
            )
            logger.info(
                f"Queried database {self.database_id} with ",
                f" {len(result.get('results', []))} results.",
            )
            return result
        except Exception as e:
            logger.error(
                f"Error querying database {self.database_id}: {e}", exc_info=True
            )
            raise

    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve a single page by ID."""
        logger.debug(f"Retrieving page: {page_id}")
        try:
            client = self._ensure_client()
            page = await client.pages.retrieve(page_id=page_id)
            logger.info(f"Successfully retrieved page: {page_id}")
            return page
        except Exception as e:
            logger.error(f"Error retrieving page {page_id}: {e}", exc_info=True)
            raise

    async def get_page_data(self, page_id: str) -> Dict[str, Any]:
        """Return simplified property map from a Notion page."""
        page = await self.get_page(page_id)
        props = page.get("properties", {})
        return simplify_properties_map(props)
