import csv, os, traceback
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS

BASE_DIR = '/Users/pallavichede/BedrockAgentCoreRAGApp'
CSV_PATH = os.path.join(BASE_DIR, 'customer_qna.csv')
INDEX_PATH = os.path.join(BASE_DIR, 'faiss_index')

try:
    print('Step 1: Loading CSV...')
    docs = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            docs.append(Document(page_content=f"Q: {row['question'].strip()}\nA: {row['answer'].strip()}"))
    print(f'✅ Loaded {len(docs)} docs')

    print('Step 2: Splitting...')
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0).split_documents(docs)
    print(f'✅ Got {len(chunks)} chunks')

    print('Step 3: Building FAISS index...')
    embeddings = BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0', region_name='eu-north-1')
    store = FAISS.from_documents(chunks, embeddings)
    print('✅ Index built!')

    print('Step 4: Saving...')
    os.makedirs(INDEX_PATH, exist_ok=True)
    store.save_local(INDEX_PATH)
    print('✅ Saved! Files:', os.listdir(INDEX_PATH))

except Exception as e:
    print(f'❌ Failed at step above: {e}')
    traceback.print_exc()