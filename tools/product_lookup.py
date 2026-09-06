"""
EcoSphere - Product Lookup Tool
Search product catalog using RAG for accurate, grounded answers.
"""

import os
import sys
from typing import Optional, Dict, Any, List

# Add parent directory to path for knowledge module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge.rag import get_knowledge_base, ProductKnowledgeBase


class ProductLookup:
    """
    Product search and lookup tool.
    Uses RAG to find relevant product information.
    """
    
    def __init__(self):
        """Initialize with the knowledge base."""
        self.kb = get_knowledge_base()
    
    def search_products(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search products using natural language query.
        
        Args:
            query: Natural language query (e.g., "How much does Enterprise cost?")
            n_results: Number of results to return
            
        Returns:
            List of relevant product information
        """
        return self.kb.search(query, n_results=n_results)
    
    def get_product_details(self, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific product.
        
        Args:
            product_name: Name or ID of the product
            
        Returns:
            Product details or None if not found
        """
        # Try by ID first
        product = self.kb.get_product_by_id(product_name.lower())
        if product:
            return product
        
        # Try by name
        for product in self.kb.products:
            if product_name.lower() in product["name"].lower():
                return product
        
        return None
    
    def compare_products(self, product1: str, product2: str) -> str:
        """
        Compare two products side by side.
        
        Args:
            product1: First product name/ID
            product2: Second product name/ID
            
        Returns:
            Formatted comparison
        """
        p1 = self.get_product_details(product1)
        p2 = self.get_product_details(product2)
        
        if not p1 or not p2:
            return "Could not find one or both products for comparison."
        
        comparison = f"""
📊 Product Comparison

{p1['name']} (${p1['price']}/mo)
• Target: {p1['target']}
• Key features: {', '.join(p1['features'][:4])}

vs.

{p2['name']} (${p2['price']}/mo)
• Target: {p2['target']}
• Key features: {', '.join(p2['features'][:4])}

💡 Recommendation:
"""
        # Add recommendation based on price difference
        if p1["price"] < p2["price"]:
            comparison += f"• {p1['name']} is best for budget-conscious teams\n"
            comparison += f"• {p2['name']} is best for teams needing advanced features"
        else:
            comparison += f"• {p2['name']} is best for budget-conscious teams\n"
            comparison += f"• {p1['name']} is best for teams needing advanced features"
        
        return comparison
    
    def get_recommendation(self, needs: str) -> str:
        """
        Recommend a product based on stated needs.
        
        Args:
            needs: Description of customer needs
            
        Returns:
            Product recommendation with reasoning
        """
        # Search for relevant products
        results = self.search_products(needs, n_results=3)
        
        if not results:
            return "I'd need to understand your needs better to make a recommendation."
        
        # Build recommendation
        recommendation = "Based on what you've told me, I recommend:\n\n"
        
        for i, result in enumerate(results[:2]):
            text = result.get("text", "")
            recommendation += f"{i+1}. {text}\n\n"
        
        recommendation += "Would you like more details about any of these options?"
        
        return recommendation
    
    def format_for_voice(self, product: Dict[str, Any]) -> str:
        """
        Format product info for voice conversation (short, natural).
        
        Args:
            product: Product dictionary
            
        Returns:
            Voice-friendly text
        """
        popular = " This is our most popular plan." if product.get("popular") else ""
        
        return (
            f"The {product['name']} is ${product['price']} per month.{popular} "
            f"It's designed for {product['target'].lower()} and includes "
            f"{', '.join(product['features'][:3])}. "
            f"Would you like to know more about any specific feature?"
        )


# Singleton instance
_product_lookup = None

def get_product_lookup() -> ProductLookup:
    """Get or create the singleton product lookup instance."""
    global _product_lookup
    if _product_lookup is None:
        _product_lookup = ProductLookup()
    return _product_lookup


# LangChain tool definitions
def create_product_tools():
    """Create LangChain-compatible tools for product lookup."""
    try:
        from langchain_core.tools import tool
        
        @tool
        def search_products(query: str) -> str:
            """
            Search the product catalog for pricing and feature information.
            
            Args:
                query: What to search for (e.g., "Enterprise pricing", "Pro plan features")
            
            Returns:
                Relevant product information
            """
            lookup = get_product_lookup()
            results = lookup.search_products(query)
            
            if not results:
                return "No matching products found. Could you rephrase your question?"
            
            # Format results for voice
            response = "Here's what I found:\n\n"
            for i, result in enumerate(results[:2]):
                response += f"{i+1}. {result['text'][:200]}\n\n"
            
            return response
        
        @tool
        def get_pricing(plan_name: str = "") -> str:
            """
            Get pricing information for a specific plan or all plans.
            
            Args:
                plan_name: Name of the plan (e.g., "Pro", "Enterprise") or empty for all
            
            Returns:
                Pricing information
            """
            kb = get_knowledge_base()
            
            if plan_name:
                product = get_product_lookup().get_product_details(plan_name)
                if product:
                    return get_product_lookup().format_for_voice(product)
                return f"I couldn't find a plan called '{plan_name}'. We offer Starter ($29/mo), Pro ($79/mo), and Enterprise ($199/mo)."
            
            return kb.get_pricing_summary()
        
        @tool
        def schedule_sales_meeting(
            customer_name: str,
            email: str,
            company: str = "",
            context: str = ""
        ) -> str:
            """
            Schedule a meeting with a human sales agent.
            
            Args:
                customer_name: Customer's full name
                email: Customer's email address
                company: Customer's company name
                context: Context from the call
            
            Returns:
                Meeting confirmation
            """
            try:
                from tools.calendar import get_scheduler
                scheduler = get_scheduler()
                meeting = scheduler.schedule_meeting(
                    customer_name=customer_name,
                    email=email,
                    company=company,
                    context=context
                )
                return scheduler.get_meeting_confirmation(meeting)
            except Exception as e:
                return f"I'll have our sales team reach out to you directly. Could you provide your email and a good time to connect?"
        
        return [search_products, get_pricing, schedule_sales_meeting]
    
    except ImportError:
        # Fallback if langchain not available
        return []


# For testing
if __name__ == "__main__":
    lookup = get_product_lookup()
    
    print("="*50)
    print("Product Lookup Test")
    print("="*50)
    
    # Test searches
    test_queries = [
        "How much does Enterprise cost?",
        "What's included in the Pro plan?",
        "I need something for a large team",
        "Compare Starter vs Pro"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-"*40)
        
        results = lookup.search_products(query, n_results=2)
        for i, result in enumerate(results):
            print(f"{i+1}. {result['text'][:150]}...")
    
    print("\n" + "="*50)
    print("Voice Format Test:")
    product = lookup.get_product_details("Pro")
    if product:
        print(lookup.format_for_voice(product))
    
    print("\n" + "="*50)
    print("Comparison Test:")
    print(lookup.compare_products("Starter", "Pro"))
