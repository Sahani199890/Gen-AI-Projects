from pathlib import Path
from langchain_community.document_loaders import UnstructuredFileLoader
from typing import List,Dict,Any,Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document_chunk(file_path:str)->List[Dict[str,Any]]:
    
    result=[]
    path=Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found at {file_path}")
    else:
        loader=UnstructuredFileLoader(str(file_path))
        raw_documents = loader.load()

        text_splitter=RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n","\n"," ",""]
            )
        chunks=text_splitter.split_documents(raw_documents)

        for chunk_index,chunk in enumerate(chunks):
            result.append({
                "chunk_index":chunk_index,
                "content":chunk.page_content,
                "metadata":chunk.metadata
            })

        return result


def generate_embeddings(texts:List[str])->List[List[float]]:
    pass


if __name__=="__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    file_path=PROJECT_ROOT / "data" / "Abhishek-Sahani-Resume.pdf"
    print(load_document_chunk(file_path))
        