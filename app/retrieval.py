import os
import dotenv
import requests
import operator
import pathlib

from langchain_openai import AzureOpenAIEmbeddings
import pymupdf4llm
from qdrant_client import QdrantClient

from langchain_community.document_loaders import TextLoader  # , PyMuPDFLoader
from langchain_text_splitters import MarkdownTextSplitter
from langchain_community.vectorstores import Qdrant

from langchain.agents import tool
from langchain.chains import RetrievalQA

#from fuzzywuzzy import fuzz
#from fuzzywuzzy import process


dotenv.load_dotenv()

qdrant_api_key = os.environ["QDRANT_API_KEY"]

# ---- GLOBAL DECLARATIONS ---- #

PDF_FOLDER_PATH = "data/reports/"
VECTORSTORE_LOCATION = os.environ["QDRANT_VECTORSTORE_LOCATION"]
#VECTORSTORE_COLLECTION_NAME = os.environ['LANGCHAIN_PROJECT']

# -- RETRIEVAL -- #

# LOAD OpenAI EMBEDDINGS API object
#embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
embedding_model = AzureOpenAIEmbeddings(
    #model="text-embedding-3-small",
    azure_deployment=os.environ['AZURE_OPENAI_EMB_DEPLOYMENT'],
    openai_api_version="2023-05-15",
)

qdrant_client = QdrantClient(url=VECTORSTORE_LOCATION, api_key=qdrant_api_key)


directory_path = "data/reports/"
txt_files = [file for file in os.listdir(directory_path) if file.endswith('.pdf')]

all_documents = {}
qdrant_collections = {}

for txt_file in txt_files:

    collection_exists = qdrant_client.collection_exists(collection_name=txt_file)

    if collection_exists == False:

        md_text = pymupdf4llm.to_markdown(PDF_FOLDER_PATH + txt_file)
        md_path = PDF_FOLDER_PATH  + txt_file + '.md'
        pathlib.Path(md_path).write_bytes(md_text.encode())
        text_loader = TextLoader(md_path)

        #loader = TextLoader(os.path.join(directory_path, txt_file))
        documents = text_loader.load()

        # Step 2: Split documents into chunks and add metadata
        text_splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(documents)
        for doc in docs:
            doc.metadata["source"] = txt_file  # Add source metadata

        all_documents[txt_file] = docs
        
        qdrant_collections[txt_file] = Qdrant.from_documents(
            all_documents[txt_file],
            embedding_model,
            location=VECTORSTORE_LOCATION, 
            collection_name=txt_file,
            prefer_grpc=True,
            api_key=qdrant_api_key,
        )

    
    else:
        qdrant_collections[txt_file] = Qdrant.from_existing_collection(
            embedding_model,
            path=None,
            collection_name=txt_file,
            url=VECTORSTORE_LOCATION,
            prefer_grpc=True,
            api_key=qdrant_api_key,
        )

retriever = {}
for txt_file in txt_files:
    retriever[txt_file] = qdrant_collections[txt_file].as_retriever()


qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        verbose=True,
        return_source_documents=True
    )


@tool
def pdf_retriever(name):
    """
    Tool to check a PDF repository of reports that have already been produced
    and are available for consultation by the user.
    """

    print(name)

    search_name = name

    # Find the best match using fuzzy search    
    best_match = process.extractOne(search_name, txt_files, scorer=fuzz.ratio)

    # Get the selected file name
    selected_file = best_match[0]
    
    selected_retriever = retriever[selected_file]

    #global query
    results = selected_retriever.get_relevant_documents()
    #global retrieved_text
    
    #total_content = "\n\nBelow are the related document's content: \n\n"
    #chunk_count = 0
    #for result in results:
    #    chunk_count += 1
    #    if chunk_count > 4:
    #        break
    #    total_content += result.page_content + "\n"
    #retrieved_text = total_content
    return results
