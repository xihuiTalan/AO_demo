import streamlit as st
import os
from langchain.docstore.document import Document
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import AzureOpenAI
from langchain.chains import RetrievalQA
from pdfSplitter import pdfSplitter

#---------Environment variables
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_VERSION"] = "2023-03-15-preview"
os.environ["OPENAI_API_BASE"] = "https://azure-openia-westeu-02.openai.azure.com/"
os.environ["OPENAI_API_KEY"] = '17f9a552c43141fd9a2cb68de5b6e0ea'

# Streamlit app
st.title('RFP Analyzer and Q&A')

uploaded_file = st.file_uploader("Choose a file", type="pdf")
texts_list = []

if uploaded_file is not None:

    pdf_splitter = pdfSplitter(uploaded_file, chunk_size=4000)
    chunks = pdf_splitter.get_chunk_by_section()
    docs = [Document(page_content=chunk, metadata=pdf_splitter.meta_data) for chunk in chunks]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(chunk_size=1))
    retriever = vectorstore.as_retriever(search_type='similarity')  # search_kwargs={'k': k} what is the default value

    # Q&A chain
    llm = AzureOpenAI(deployment_name="text-davinci-003", model_name="text-davinci-003", temperature=0)
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type='stuff', retriever=retriever)

    # ask a series of questions in order to infer the global context
    questions = ["Peux-tu identifier le client de l'appel d'offre ?",
                 "Peux-tu identifier le secteur de l'appel d'offre ?",
                 "Peux-tu identifier l'industrie de l'appel d'offre ?",
                 "Peux-tu identifier le type de projet de l'appel d'offre ? Voici quelques exemples : 'Build et de RUN', 'Migration', ... ",
                 "Peux-tu identifier les technologies citées dans l'appel d'offre ?",
                 "Peux-tu identifier la méthodologie appliquée dans l'appel d'offre ?"]

    # topic modeling 
    global_context = ""
    for query in questions:
        result = qa_chain({'query': query})
        global_context += result['result'] + "\n"

    st.write(global_context)


