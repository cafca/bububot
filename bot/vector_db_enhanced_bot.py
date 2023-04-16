
import openai
import logging
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from uuid import uuid4
from functools import wraps
from typing import List, Tuple
from time import sleep
from datetime import datetime

import config
from vector_db import VectorDB

logger = logging.getLogger(__name__)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

tokenizer = tiktoken.get_encoding("p50k_base")
embed_model = "text-embedding-ada-002"
index_name = "telegram-bot-messages"

# Initialize OpenAI and Pinecone
openai.api_key = config.openai_api_key

vector_db = None
# pinecone is flaky...
try:
    vector_db = VectorDB(index_name)
except Exception as e:
    print(f"Failed to initialize Pinecone: {e}")


def tiktoken_len(text: str) -> int:
    """
    This function returns the length of the text encoded using the tiktoken tokenizer.

    Args:
    - text (str): The input text.

    Returns:
    - int: The length of the encoded text.
    """
    tokens = tokenizer.encode(text, disallowed_special=())
    return len(tokens)


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=20,
    length_function=tiktoken_len,
    separators=["\n\n", "\n", " ", ""],
)


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    This function returns the embeddings of a list of texts using OpenAI's text-embedding-ada-002 model.

    Args:
    - texts (List[str]): A list of input texts.

    Returns:
    - List[List[float]]: A list of embeddings.
    """

    # Split input texts into chunks
    splitted_texts = []
    chunk_lengths = []
    for text in texts:
        chunks = text_splitter.split_text(text)
        splitted_texts.extend(chunks)
        chunk_lengths.append(len(chunks))

        logger.debug(f"Splitting text into chunks: {chunks}")

    # Create embeddings for each chunk
    try:
        res = openai.Embedding.create(input=splitted_texts, engine=embed_model)
    except openai.RateLimitError:
        done = False
        while not done:
            sleep(5)
            try:
                res = openai.Embedding.create(input=splitted_texts, engine=embed_model)
                done = True
            except openai.RateLimitError:
                pass

    # Combine embeddings of chunks for each input text
    embeddings = []
    i = 0
    for num_chunks in chunk_lengths:
        text_embedding = [0] * 1536
        for _ in range(num_chunks):
            chunk_embedding = res['data'][i]['embedding']
            text_embedding = [sum(x) for x in zip(text_embedding, chunk_embedding)]
            i += 1
        embeddings.append(text_embedding)

    return embeddings


async def store_in_db(message: str, response: str, user_id: str):
    """
    This function stores message and response in the vector database.

    Args:
        message (str): The input message.
        response (str): The response to the input message.

    Returns:
        None.
    """
    if vector_db is None:
        return
    # Create a string of the current date in the format: YYYY-MM-DD HH:MM:SS
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Get embeddings for the input message and response
    texts = [
        f"User said on {date}: {message}",
        f"Assistant said on {date}: {response}",
    ]
    embeddings = get_embeddings(texts)

    # Generate unique IDs for the embeddings
    ids = [str(uuid4()), str(uuid4())]

    # Combine the embeddings and metadata into tuples for upsertion
    to_upsert = [(ids[0], embeddings[0], {'text': texts[0]}), (ids[1], embeddings[1], {'text': texts[1]})]

    # Upsert the embeddings and metadata into the vector database
    logger.info(f"Storing message and response in vector database: {ids}")
    vector_db.upsert(vectors=to_upsert, namespace=user_id)

def memories_for_message(user_id: str, message: str) -> List[str]:
    """
    This function returns the memories for a given message.
    
    Args:
        user_id (str): The ID of the user.
        message (str): The message for which to retrieve the memories.
    
    Returns:
        List[Tuple[str, str]]: A list of memories.
    """

    if vector_db is None:
        return []
    # Get the embedding of the message
    query_embedding = get_embeddings([message])[0]
    # Retrieve relevant contexts from VectorDB
    res = vector_db.query(query_embedding, top_k=5, namespace=str(user_id))
    
    if res is not None:
        return [match.metadata.get('text', '') for match in res.matches]

    return []