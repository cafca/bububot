import pinecone
import config

class VectorDB:
    def __init__(
        self,
        index_name: str,
    ):
        # Init pinecone
        print("Init pinecone...")
        pinecone.init(api_key=config.pinecone_api_key, enviroment="us-east1-gcp")

        # Create index if not exist
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(index_name, dimension=1536, metric="dotproduct")

        # connect to index
        self.index = pinecone.Index(index_name)
        stats = self.index.describe_index_stats()
        print(f"Index {index_name}, stats: {stats}")

    def query(self, vector, top_k=5, namespace=None):
        """
        Query vectors from the index.

        Args:
        - vector (List[float]): The vector to query.
        - top_k (int): The number of results to return.
        - namespace (str): The namespace to use for the query.
        """
        if namespace is None:
            namespace = str(pinecone.deployment.pod_uuid())
        return self.index.query(
            vector, top_k=top_k, namespace=namespace, include_metadata=True
        )

    def upsert(self, vectors, namespace=None):
        """
        Upsert vectors to the index.

        Args:
        - vectors (List[Tuple[str, List[float]]]): A list of tuples of (id, vector)
        - namespace (str): The namespace to use for the vectors.
        """
        if namespace is None:
            namespace = str(pinecone.deployment.pod_uuid())
        self.index.upsert(vectors, namespace=namespace)
