"""
Pinecone Vector Database Manager
Handles embedding storage and retrieval for RAG
"""
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import time

class PineconeManager:
    """
    Manages Pinecone vector database operations
    
    Features:
    - Store documents with embeddings
    - Semantic search
    - Metadata filtering
    - Batch operations
    
    """
    def __init__(
        self,
        api_key: str,
        index_name: str = "insightforge-context",
        dimension: int = 384,
        metric: str = "cosine"
    ):
        self.api_key = api_key
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric

        # Intialize Pinecone client
        try:
            self.pc = Pinecone(api_key=api_key)
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Get or create index
            self.index = self._get_or_create_index()
            
            print(f"✅ Pinecone connected: {index_name}")
            
        except Exception as e:
            print(f"❌ Pinecone connection failed: {e}")
            self.index = None

    def _get_or_create_index(self):
        """Get existing index or create new one"""

        #Check if index exists
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name in existing_indexes:
            print(f"📦 Using existing index: {self.index_name}")
            return self.pc.Index(self.index_name)
        
        # Create new index
        print(f"🔨 Creating new index: {self.index_name}")

        self.pc.create_index(
            name=self.index_name,
            dimension=self.dimension,
            metric=self.metric,
            spec=ServerlessSpec(
            cloud='aws',  # or 'gcp'
            region='us-west-2'  # adjust based on your region
            )
        )
        
        # wait for index to be ready
        while not self.pc.describe_index(self.index_name).status['ready']:
            time.sleep(1)

        return self.pc.Index(self.index_name)
    
    def upsert_documents(
        self,
        documents: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> int:
        """
        Store documents in Pinecone
        
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
            namespace: Namespace to organize vectors
            
        Returns:
            Number of documents stored
        """

        if not self.index:
            print("⚠️  Pinecone not available")
            return 0
        
        vectors = []

        for doc in documents:
            # Generate embedding
            embedding = self.embedding_model.encode(doc['content']).tolist()

        # Prepare vector
            vector = {
                'id': doc['id'],
                'values': embedding,
                'metadata': {
                    'content': doc['content'],
                    **doc.get('metadata', {})
                }
            }

            vectors.append(vector)

        # Batch upsert(max 100 at a time)
        batch_size = 100
        total_upserted = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
            total_upserted += len(batch)
        
        print(f"✅ Upserted {total_upserted} documents to Pinecone")
        
        return total_upserted
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "default",
        filter_dict: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in Pinecone
        
        Args:
            query: Search query text
            top_k: Number of results to return
            namespace: Namespace to search in
            filter_dict: Metadata filters (e.g., {'category': 'competition'})
            
        Returns:
            List of matching documents with scores
        """

        if not self.index:
            print("⚠️  Pinecone not available, returning empty results")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()

        # Search 
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter=filter_dict,
            include_metadata = True
        )

        # Format results
        formatted_results = []

        for match in results['matches']:
            formatted_results.append({
                'id': match['id'],
                'score': match['score'],
                'content': match['metadata'].get('content', ''),
                'metadata': {k: v for k, v in match['metadata'].items() if k != 'content'}
            })

        return formatted_results

    def delete_all(self, namespace: str = "default"):
        """Delete all vectors in namespace"""
        if self.index:
            self.index.delete(delete_all=True, namespace=namespace)
            print(f"🗑️  Deleted all vectors in namespace: {namespace}")
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        if self.index:
            stats = self.index.describe_index_stats()
            return {
                'total_vectors': stats.get('total_vector_count', 0),
                'dimension': stats.get('dimension', 0),
                'namespaces': stats.get('namespaces', {})
            }
        return {}