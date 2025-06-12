import torch 
import streamlit as st
from app.services.pdf_processor import extract_text_from_pdf, process_zip_invoices
from app.services.llm_service import InvoiceAnalyzer
from app.services.vector_store import VectorStore
import tempfile
import uuid

# Initialize components
analyzer = InvoiceAnalyzer()
vector_db = VectorStore()

# st.set_option('server.fileWatcherType', 'none')
st.title("📄 IAI Invoice Reimbursement System")

# Tab 1: Invoice Analysis
tab1, tab2 = st.tabs(["Analyze Invoices", "Chat Query"])

with tab1:
    st.header("Upload Documents")
    policy_pdf = st.file_uploader("HR Policy PDF", type="pdf")
    invoices_zip = st.file_uploader("Invoices ZIP", type="zip")
    employee_name = st.text_input("Employee Name")

    if st.button("Analyze"):
        if not all([policy_pdf, invoices_zip, employee_name]):
            st.error("All fields required!")
        else:
            with st.spinner("Processing..."):
                try:
                    # Process policy
                    policy_text = extract_text_from_pdf(policy_pdf)
                    
                    # Process invoices
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp.write(invoices_zip.getvalue())
                        invoices = process_zip_invoices(tmp.name)
                    
                    # Analyze each invoice
                    for filename, invoice_file in invoices:
                        invoice_text = extract_text_from_pdf(invoice_file)
                        analysis = analyzer.analyze_invoice(policy_text, invoice_text)
                        
                        # Store in vector DB
                        invoice_id = f"inv-{uuid.uuid4().hex[:6]}"
                        vector_db.store_analysis(
                            invoice_id=invoice_id,
                            invoice_text=invoice_text,
                            analysis=analysis,
                            employee_name=employee_name
                        )
                        
                        # Display results
                        st.success(f"Processed {filename}")
                        st.json({
                            "Status": analysis.status.value,
                            "Amount Reimbursed": f"₹{analysis.reimbursed_amount}",
                            "Reason": analysis.reason
                        })
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with tab2:
    st.header("Query Invoices")
    query = st.text_input("Ask about invoices")
    if st.button("Search"):
        results = vector_db.search(query)
        for doc in results:
            with st.expander(f"Result {doc['metadata']['invoice_id']}"):
                st.write(doc['document'])