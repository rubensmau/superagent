import logging
from typing import Literal

from decouple import config
from langchain.docstore.document import Document
from qdrant_client import QdrantClient, models
from qdrant_client.http import models as rest
from qdrant_client.http.models import PointStruct

from app.models.request import EmbeddingsModelProvider
from app.utils.helpers import get_first_non_null
from app.vectorstores.abstract import VectorStoreBase
from app.vectorstores.embeddings import get_embeddings_model_provider

logger = logging.getLogger(__name__)


class QdrantVectorStore(VectorStoreBase):
    def __init__(
        self,
        options: dict,
        embeddings_model_provider: EmbeddingsModelProvider,
        index_name: str = None,
        host: str = None,
        api_key: str = None,
    ) -> None:
        self.options = options

        variables = {
            "QDRANT_INDEX": get_first_non_null(
                index_name,
                options.get("QDRANT_INDEX"),
                config("QDRANT_INDEX", None),
            ),
            "QDRANT_HOST": get_first_non_null(
                host,
                options.get("QDRANT_HOST"),
                config("QDRANT_HOST", None),
            ),
            "QDRANT_API_KEY": get_first_non_null(
                api_key,
                options.get("QDRANT_API_KEY"),
                config("QDRANT_API_KEY", None),
            ),
        }

        for var, value in variables.items():
            if not value:
                raise ValueError(
                    f"Please provide a {var} via the "
                    f"`{var}` environment variable"
                    "or check the `VectorDb` table in the database."
                )

        self.client = QdrantClient(
            url=variables["QDRANT_HOST"],
            api_key=variables["QDRANT_API_KEY"],
        )
        self.embeddings = get_embeddings_model_provider(
            embeddings_model_provider=embeddings_model_provider
        )

        self.index_name = variables["QDRANT_INDEX"]
        logger.info(f"Initialized Qdrant Client with: {self.index_name}")

    def embed_documents(self, documents: list[Document], batch_size: int = 100) -> None:
        collections = self.client.get_collections()
        if self.index_name not in [c.name for c in collections.collections]:
            self.client.recreate_collection(
                collection_name=self.index_name,
                vectors_config={
                    "content": rest.VectorParams(
                        distance=rest.Distance.COSINE,
                        size=1536,
                    ),
                },
            )
        points = []
        i = 0
        for document in documents:
            i += 1
            response = self.embeddings.embed_documents([document.page_content])
            points.append(
                PointStruct(
                    id=i,
                    vector={"content": response[0]},
                    payload={"text": document.page_content, **document.metadata},
                )
            )
        self.client.upsert(collection_name=self.index_name, wait=True, points=points)

    def query_documents(
        self,
        prompt: str,
        datasource_id: str,
        top_k: int | None,
        _query_type: Literal["document", "all"] = "document",
    ) -> list[str]:
        response = self.embeddings.embed_documents([prompt])
        embeddings = response[0]
        search_result = self.client.search(
            collection_name=self.index_name,
            query_vector=("content", embeddings),
            limit=top_k,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="datasource_id",
                        match=models.MatchValue(value=datasource_id),
                    ),
                ]
            ),
            with_payload=True,
        )
        return search_result

    def delete(self, datasource_id: str) -> None:
        try:
            self.client.delete(
                collection_name=self.index_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="datasource_id",
                                match=models.MatchValue(value=datasource_id),
                            ),
                        ],
                    )
                ),
            )
        except Exception as e:
            logger.error(f"Failed to delete {datasource_id}. Error: {e}")
