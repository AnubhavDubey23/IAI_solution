from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.services.pdf_processor import extract_text_from_pdf, process_zip_invoices, extract_amounts_from_text
from app.services.llm_service import InvoiceAnalyzer
from app.services.vector_store import VectorStore
from app.models.schemas import InvoiceAnalysisRequest, ChatRequest, AnalysisResult,InvoiceResponse,ChatResponse
from typing import List
import uuid
from datetime import datetime
import os
import uvicorn
import requests



app = FastAPI(
    title="IAI Solution Invoice Reimbursement System",
    description="Automated invoice analysis against company policy",
    version="1.0"
)

analyzer = InvoiceAnalyzer()
vector_db = VectorStore()

@app.post("/analyze-invoice", response_model=dict)
async def analyze_invoice(
    policy_pdf: UploadFile = File(..., description="Company reimbursement policy PDF"),
    invoices_zip: UploadFile = File(..., description="ZIP file containing invoice PDFs"),
    employee_name: str = Form(..., min_length=2, max_length=100),
):
    try:
        # Validate inputs
        response = requests.post("http://localhost:8000/analyze-invoice", json={"abc": "def"})
        print(response.json())

        if not policy_pdf.filename.endswith('.pdf'):
            raise HTTPException(400, "Policy file must be PDF")
        if not invoices_zip.filename.endswith('.zip'):
            raise HTTPException(400, "Invoices must be in ZIP file")

        # Process policy
        policy_text = extract_text_from_pdf(policy_pdf.file)
        if not policy_text:
            raise HTTPException(400, "Could not extract text from policy PDF")

        # Process invoices
        invoices = process_zip_invoices(invoices_zip.file)
        if not invoices:
            raise HTTPException(400, "No PDF invoices found in ZIP file")

        results = []
        for filename, invoice_file in invoices:
            invoice_text = extract_text_from_pdf(invoice_file)
            if not invoice_text:
                continue
                
            analysis = analyzer.analyze_invoice(policy_text, invoice_text)
            invoice_id = f"inv-{uuid.uuid4().hex[:8]}"
            
            vector_db.store_analysis(
                invoice_id=invoice_id,
                invoice_text=invoice_text,
                analysis=analysis,
                employee_name=employee_name
            )
            
            results.append({
                "invoice_id": invoice_id,
                "status": analysis.status.value,
                "reimbursed_amount": analysis.reimbursed_amount,
                "reason": analysis.reason
            })

        return JSONResponse({
            "status": "success",
            "processed_invoices": len(results),
            "results": results
        })

    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")

@app.post("/chat", response_model=dict)
async def chat_with_bot(request: ChatRequest):
    try:
        # Convert status filter to enum value if present
        filters = request.filters or {}
        if 'status' in filters:
            filters['status'] = filters['status'].capitalize() + " Reimbursed"
            
        search_results = vector_db.search(
            query=request.query,
            filters=filters
        )
        
        # Format context for LLM
        context = "\n\n".join([
            f"Document {i+1}:\n{doc['document']}\nMetadata: {doc['metadata']}"
            for i, doc in enumerate(search_results)
        ])
        
        # Generate response (in real implementation, use LLM here)
        response = {
            "response": f"Found {len(search_results)} matching invoices:\n\n{context}",
            "context": request.history + [{"role": "assistant", "content": request.query}]
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        raise HTTPException(500, f"Chat error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)