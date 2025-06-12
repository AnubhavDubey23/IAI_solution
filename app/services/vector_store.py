import chromadb
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional
from datetime import datetime
from app.models.schemas import AnalysisResult
import os

class VectorStore:
    def __init__(self, persist_path: str = None):
        # Use temp directory if no path specified
        if persist_path is None:
            persist_path = os.path.join(os.getcwd(), "chroma_db")
        
        # Create directory if it doesn't exist
        os.makedirs(persist_path, exist_ok=True)
        
        try:
            embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            
            # ✅ NEW CLIENT INITIALIZATION
            self.client = Client(
                Settings(
                    persist_directory=persist_path,
                    anonymized_telemetry=False
                )
            )
            
            # Get or create collection with embedding function
            self.collection = self.client.get_or_create_collection(
                name="invoice_analyses",
                embedding_function=embedding_fn
            )

        except Exception as e:
            # Clean up if initialization fails
            if hasattr(self, 'client'):
                del self.client
            raise RuntimeError(f"Failed to initialize VectorStore: {str(e)}")
    
    # ... [keep all your existing methods unchanged] ...
        
    def store_analysis(self, invoice_id: str, invoice_text: str, 
                     analysis: AnalysisResult, employee_name: str) -> None:
        """Store analysis results with detailed metadata"""
        metadata = {
            "employee": employee_name,
            "status": analysis.status.value,
            "date": datetime.now().isoformat(),
            "reimbursed_amount": str(analysis.reimbursed_amount),
            "requested_amount": str(analysis.requested_amount),
            "category": self._detect_category(analysis.reason)
        }
        
        document_text = f"""
        Invoice Analysis for {employee_name}:
        Status: {analysis.status.value}
        Amount Requested: ₹{analysis.requested_amount}
        Amount Reimbursed: ₹{analysis.reimbursed_amount}
        Reason: {analysis.reason}
        Policy References: {', '.join(analysis.policy_references)}
        """
        
        self.collection.add(
            documents=[document_text],
            metadatas=[metadata],
            ids=[invoice_id]
        )
    
    def _detect_category(self, reason: str) -> str:
        """Detect expense category from reason text"""
        reason_lower = reason.lower()
        if 'meal' in reason_lower or 'food' in reason_lower:
            return "Food"
        elif 'travel' in reason_lower or 'flight' in reason_lower:
            return "Travel"
        elif 'cab' in reason_lower or 'taxi' in reason_lower:
            return "Cab"
        return "Other"
    
    def search(self, query: str, filters: Optional[Dict] = None, n_results: int = 5) -> List[Dict]:
        """Search with both vector similarity and metadata filtering"""
        if filters is None:
            filters = {}
            
        # Convert amount filters to numeric comparisons
        amount_filters = {}
        for key in ['reimbursed_amount', 'requested_amount']:
            if key in filters:
                amount_filters[key] = float(filters[key])
                del filters[key]
        
        results = self.collection.query(
            query_texts=[query],
            where=filters,
            n_results=n_results
        )
        
        # Apply amount filters post-query if needed
        if amount_filters:
            filtered_results = []
            for doc, meta in zip(results['documents'], results['metadatas']):
                include = True
                for key, value in amount_filters.items():
                    if float(meta[key]) < value:
                        include = False
                        break
                if include:
                    filtered_results.append({
                        'document': doc,
                        'metadata': meta
                    })
            return filtered_results
            
        return [{'document': d, 'metadata': m} for d, m in zip(results['documents'], results['metadatas'])]