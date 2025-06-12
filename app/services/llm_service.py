from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import os
from app.models.schemas import ReimbursementStatus, AnalysisResult
from typing import Dict, Any
import re
from dotenv import load_dotenv

load_dotenv()

class InvoiceAnalyzer:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        self.output_parser = StrOutputParser()
        
        # Define the prompt as a template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert invoice reimbursement analyst for IAI Solution. 
            Analyze the invoice against the provided policy and determine reimbursement status:
            
            Policy Guidelines to Consider:
            1. Food/Beverages: ₹200/meal max (alcohol strictly excluded)
            2. Travel: 
               - Flights/Buses: ₹2000/trip max (inclusive of all taxes)
               - Cabs: ₹150/day for office commutes (toll fees excluded)
            3. Accommodation: ₹500/night max
            
            Required Analysis:
            1. Determine expense category
            2. Compare amounts against policy limits
            3. Determine status (Fully/Partially/Declined)
            4. Calculate reimbursable amount
            5. Provide specific policy references
            
            Respond in this EXACT format:
            Category: [category]
            Status: [Fully/Partially/Declined]
            Requested Amount: ₹X
            Reimbursed Amount: ₹Y
            Reason: [explanation]
            Policy References:
            - [reference 1]
            - [reference 2]"""),
            ("human", "COMPANY POLICY:\n{policy_text}\n\nINVOICE DETAILS:\n{invoice_text}")
        ])
        
        # Create the chain
        self.analysis_chain = self.prompt_template | self.llm | self.output_parser

    def analyze_invoice(self, policy_text: str, invoice_text: str) -> AnalysisResult:
        try:
            # Invoke the chain
            response = self.analysis_chain.invoke({
                "policy_text": policy_text,
                "invoice_text": invoice_text
            })
            
            return self._parse_response(response)
        except Exception as e:
            # Fallback response if parsing fails
            return AnalysisResult(
                status=ReimbursementStatus.DECLINED,
                reimbursed_amount=0.0,
                requested_amount=0.0,
                reason=f"Analysis failed: {str(e)}",
                policy_references=[]
            )
    
    def _parse_response(self, text: str) -> AnalysisResult:
        try:
            # Extract all required fields including category
            category_match = re.search(r'Category:\s*(.+)', text, re.IGNORECASE)
            status_match = re.search(r'Status:\s*(Fully|Partially|Declined)', text, re.IGNORECASE)
            req_amount_match = re.search(r'Requested Amount:\s*₹(\d+\.?\d*)', text)
            reimb_amount_match = re.search(r'Reimbursed Amount:\s*₹(\d+\.?\d*)', text)
            reason_match = re.search(r'Reason:\s*(.+?)(?=\nPolicy References:|$)', text, re.DOTALL)
            
            # Get status with proper enum conversion
            status_str = status_match.group(1).title() if status_match else "Declined"
            status = ReimbursementStatus[status_str.upper()]
            
            return AnalysisResult(
                category=category_match.group(1).strip() if category_match else "Unknown",
                status=status,
                reimbursed_amount=float(reimb_amount_match.group(1)) if reimb_amount_match else 0.0,
                requested_amount=float(req_amount_match.group(1)) if req_amount_match else 0.0,
                reason=reason_match.group(1).strip() if reason_match else "No reason provided",
                policy_references=self._extract_policy_references(text)
            )
        except Exception as e:
            raise ValueError(f"Failed to parse LLM response: {str(e)}\nResponse was: {text}")
    
    def _extract_policy_references(self, text: str) -> list:
        """Extracts policy references from the LLM response"""
        if "Policy References:" not in text:
            return []
        
        ref_section = text.split("Policy References:")[1]
        return [line.strip() for line in ref_section.split("\n") if line.strip().startswith("-")]

class Chatbot:
    def __init__(self, vector_db):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        self.vector_db = vector_db
        self.output_parser = StrOutputParser()
        
        # Define the prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an invoice reimbursement assistant. Use the provided invoice data to answer questions.
            Respond in clear markdown format with:
            - **Answer**: Direct response to query
            - **Sources**: Relevant invoice excerpts
            - **Confidence**: High/Medium/Low"""),
            ("human", """User query: {query}
            
            Relevant invoices:
            {search_results}""")
        ])
        
        # Create the chain
        self.chat_chain = self.prompt_template | self.llm | self.output_parser

    def query_invoices(self, user_query: str, chat_history: list = None):
        search_results = self.vector_db.search_with_filters(user_query)
        
        response = self.chat_chain.invoke({
            "query": user_query,
            "search_results": search_results
        })
        
        return response