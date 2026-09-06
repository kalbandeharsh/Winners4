"""
EcoSphere - RAG Knowledge Base
ChromaDB-based retrieval for product information and pricing.
"""

import os
import json
from typing import List, Dict, Any, Optional

# Try to import chromadb, fallback to simple search if not available
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    print("⚠️  chromadb not installed. Using fallback search. Install with: pip3 install chromadb")


class ProductKnowledgeBase:
    """
    RAG-powered product knowledge base.
    Retrieves relevant product information for sales conversations.
    """
    
    def __init__(self, products_path: str = None):
        """Initialize the knowledge base with product data."""
        if products_path is None:
            products_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "products.json"
            )
        
        # Load product data
        with open(products_path, "r") as f:
            self.product_data = json.load(f)
        
        self.products = self.product_data["products"]
        self.faqs = self.product_data.get("faqs", [])
        self.add_ons = self.product_data.get("add_ons", [])
        self.competitors = self.product_data.get("competitors", {})
        
        # Initialize ChromaDB if available
        if HAS_CHROMADB:
            self._init_chromadb()
        else:
            self._init_fallback()
    
    def _init_chromadb(self):
        """Initialize ChromaDB vector store."""
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            anonymized_telemetry=False
        ))
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="products",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Index products
        documents = []
        metadatas = []
        ids = []
        
        for product in self.products:
            # Create searchable text from product
            text = f"""
            {product['name']}: ${product['price']}/month for {product['target']}.
            Features: {', '.join(product['features'])}.
            {product['description']}
            """
            documents.append(text.strip())
            metadatas.append({
                "type": "product",
                "product_id": product["id"],
                "name": product["name"],
                "price": str(product["price"])
            })
            ids.append(f"product_{product['id']}")
        
        # Index FAQs
        for i, faq in enumerate(self.faqs):
            documents.append(f"Q: {faq['question']} A: {faq['answer']}")
            metadatas.append({"type": "faq", "index": str(i)})
            ids.append(f"faq_{i}")
        
        # Index add-ons
        for i, addon in enumerate(self.add_ons):
            documents.append(f"{addon['name']}: ${addon['price']}/month - {addon['description']}")
            metadatas.append({"type": "addon", "index": str(i)})
            ids.append(f"addon_{i}")
        
        # Upsert all documents
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Knowledge base initialized with {len(documents)} documents")
    
    def _init_fallback(self):
        """Simple fallback search without ChromaDB."""
        self.search_index = []
        
        for product in self.products:
            text = f"{product['name']}: ${product['price']}/month. {', '.join(product['features'])}"
            self.search_index.append({
                "text": text,
                "type": "product",
                "data": product
            })
        
        for faq in self.faqs:
            self.search_index.append({
                "text": f"{faq['question']} {faq['answer']}",
                "type": "faq",
                "data": faq
            })
        
        print(f"✅ Knowledge base initialized (fallback mode) with {len(self.search_index)} entries")
    
    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for relevant information.
        
        Args:
            query: The search query
            n_results: Number of results to return
            
        Returns:
            List of matching documents with scores
        """
        if HAS_CHROMADB:
            return self._search_chromadb(query, n_results)
        else:
            return self._search_fallback(query, n_results)
    
    def _search_chromadb(self, query: str, n_results: int) -> List[Dict[str, Any]]:
        """Search using ChromaDB."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None
            })
        
        return formatted
    
    def _search_fallback(self, query: str, n_results: int) -> List[Dict[str, Any]]:
        """Simple keyword search fallback."""
        query_lower = query.lower()
        scored = []
        
        for item in self.search_index:
            # Simple word overlap scoring
            words = set(query_lower.split())
            text_words = set(item["text"].lower().split())
            overlap = len(words & text_words)
            scored.append((overlap, item))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {"text": item["text"], "type": item["type"], "data": item["data"]}
            for _, item in scored[:n_results]
        ]
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific product by ID."""
        for product in self.products:
            if product["id"] == product_id:
                return product
        return None
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products."""
        return self.products
    
    def get_pricing_summary(self) -> str:
        """Get a formatted pricing summary."""
        lines = ["EcoSphere Pricing:\n"]
        for product in self.products:
            popular = " (Most Popular)" if product.get("popular") else ""
            lines.append(f"• {product['name']}{popular}: ${product['price']}/month")
            lines.append(f"  Target: {product['target']}")
            lines.append(f"  Key features: {', '.join(product['features'][:3])}")
            lines.append("")
        return "\n".join(lines)
    
    def get_competitor_response(self, competitor: str) -> str:
        """Get a response for competitor comparison."""
        responses = self.competitors.get("responses", {})
        advantages = self.competitors.get("our_advantages", [])
        
        response = responses.get(competitor.lower())
        if response:
            return f"{response}\n\nOur key advantages: {'; '.join(advantages)}"
        
        return f"When comparing to alternatives, remember: {'; '.join(advantages)}"
    
    def format_for_context(self, query: str, max_length: int = 500) -> str:
        """
        Format search results as context for the LLM.
        
        Args:
            query: The user's query
            max_length: Maximum context length
            
        Returns:
            Formatted context string
        """
        results = self.search(query, n_results=3)
        
        context_parts = []
        current_length = 0
        
        for result in results:
            text = result["text"]
            if current_length + len(text) < max_length:
                context_parts.append(text)
                current_length += len(text)
            else:
                break
        
        return "\n\n".join(context_parts) if context_parts else "No relevant information found."


# Singleton instance
_knowledge_base = None

def get_knowledge_base() -> ProductKnowledgeBase:
    """Get or create the singleton knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = ProductKnowledgeBase()
    return _knowledge_base


# For testing
if __name__ == "__main__":
    kb = get_knowledge_base()
    
    print("\n" + "="*50)
    print("Knowledge Base Test")
    print("="*50)
    
    # Test searches
    test_queries = [
        "How much does the Pro plan cost?",
        "What features are included in Enterprise?",
        "Do you offer a free trial?",
        "How does EcoSphere compare to competitors?"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-"*40)
        
        results = kb.search(query, n_results=2)
        for i, result in enumerate(results):
            print(f"{i+1}. {result['text'][:100]}...")
    
    print("\n" + "="*50)
    print("Pricing Summary:")
    print(kb.get_pricing_summary())
