import os
import re
import time
import faiss
import numpy as np
import tiktoken
from openai import OpenAI
import threading
from notion_client import Client as NotionClient
from dotenv import load_dotenv
import builtins
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
from flask_session import Session

app = Flask(__name__)
CORS(app)

CACHE_FILE = "chunks_cache.pkl"
FORCE_REFRESH = False

# DO NOT TOUCH
chunked_pairs = []
index = None
index_lock = threading.Lock()

load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

notion = NotionClient(auth=NOTION_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

depth_filter = 3

# === Configure these ===
chat_model = "gpt-4"
id_list = [
        "15e37e2bd5664a22a1afe69f0f52cb21",  # Mentors
        "6a30c7fe1db548d7943420749de67c56",   # Startup Resources
        ""
]
k_results = 15
recrawl_interval = 20 # in minutes

def print(*args, **kwargs):
    from datetime import datetime
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    builtins.print(timestamp, *args, **kwargs)

def notion_url_from_page_and_block(page_id, block_id):
    clean_page_id = page_id.replace("-", "")
    clean_block_id = block_id.replace("-", "")
    return f"https://www.notion.so/{clean_page_id}#{clean_block_id}"

def extract_plain_text(prop):
    if "rich_text" in prop and prop["rich_text"]:
        return "".join(t.get("plain_text", "") for t in prop["rich_text"])
    if "title" in prop and prop["title"]:
        return "".join(t.get("plain_text", "") for t in prop["title"])
    return ""

def extract_tags(prop):
    if "multi_select" in prop:
        return [t["name"] for t in prop["multi_select"]]
    return []

def extract_text_from_pages(page_ids, depth_limit):
    if not FORCE_REFRESH and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            print("✅ Loaded chunks from cache.")
            return pickle.load(f)

    chunk_data = []

    def crawl_page(page_id, depth=0):
        print(f"Crawling page {page_id}...")

        if depth > depth_limit:
            print(f"🟨 Skipping children at depth {depth} for {page_id}")
            return

        try:
            children = notion.blocks.children.list(block_id=page_id)["results"]
        except Exception as e:
            print(f"❌ Error fetching blocks for {page_id}: {e}")
            return

        for block in children:
            block_type = block.get("type")
            block_id = block.get("id")
            value = block.get(block_type, {})

            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
                fragments = value.get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in fragments])
                if text.strip():
                    chunk_data.append((text.strip(), notion_url_from_page_and_block(page_id, block_id)))

            elif block_type == "child_page":
                crawl_page(block_id, depth + 1)

            elif block_type == "child_database":
                print(f"📘 Found a Notion database (ID: {block_id}) — attempting to extract rows")
                try:
                    rows = notion.databases.query(database_id=block_id)["results"]
                    for row in rows:
                        props = row.get("properties", {})
                        name = extract_plain_text(props.get("Name", {}))
                        role = extract_plain_text(props.get("Role", {}))
                        tags = extract_tags(props.get("Tags", {}))
                        location = extract_plain_text(props.get("Location", {}))
                        summary = f"{name} — {role}. Tags: {', '.join(tags)}. Location: {location}"
                        chunk_data.append((summary, notion_url_from_page_and_block(page_id, row["id"])))
                except Exception as e:
                    print(f"❌ Error querying database {block_id}: {e}")

    for pid in page_ids:
        crawl_page(pid)

    # Cache the result
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(chunk_data, f)
        print("📦 Saved crawled chunks to cache.")

    return chunk_data


def chunk_text_with_sources(text_url_pairs, max_tokens=300):
    encoding = tiktoken.encoding_for_model(chat_model)
    chunked = []

    for text, url in text_url_pairs:
        tokens = encoding.encode(text)
        for i in range(0, len(tokens), max_tokens):
            chunk = encoding.decode(tokens[i:i + max_tokens])
            chunked.append((chunk, url))

    return chunked

def get_embeddings(chunks, model="text-embedding-3-small", batch_size=10, max_workers=6):
    def embed_batch(batch_index, batch_data):
        texts = [chunk for chunk, _ in batch_data]
        try:
            response = client.embeddings.create(input=texts, model=model)
            return batch_index, [r.embedding for r in response.data]
        except Exception as e:
            print(f"🟥Batch {batch_index} failed: {e}")
            return batch_index, [None] * len(batch_data)

    # Create all batches with index
    batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]

    results = [None] * len(batches)

    print(f"Embedding {len(chunks)} chunks across {len(batches)} batches using {max_workers} threads...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(embed_batch, i, batch) for i, batch in enumerate(batches)]

        for f in as_completed(futures):
            batch_index, batch_embeddings = f.result()
            results[batch_index] = batch_embeddings
            print(f"🟩Finished batch {batch_index + 1}/{len(batches)}")

    # Flatten the results and filter out None
    flat_embeddings = []
    for batch in results:
        if batch:
            flat_embeddings.extend(batch)

    return flat_embeddings

def create_faiss_index(embeddings):
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))
    return index

def retrieve_chunks(query, index, chunks):
    response = client.embeddings.create(input=[query], model="text-embedding-3-small")
    q_embedding = response.data[0].embedding

    D, I = index.search(np.array([q_embedding]).astype("float32"), k_results)
    return [chunks[i] for i in I[0]]

def ask_gpt(query, context_chunks, model_version, history):
    system_prompt = (
        "You are a knowledgeable assistant answering questions based on internal company notion workspace.\n"
        "If you cannot find a direct answer, you may guide the user to the most relevant section or suggest where they can look further — as long as it comes from the context.\n"
        "Do not make up facts. If nothing is relevant, say: 'I couldn't find that in the notion workspace.'\n"
        "Do not mention 'context' or numerical references like 'context 5' in your responses."
    )

    if context_chunks:
        context = "\n\n".join(
            [f"{i+1}. [{chunk[:200]}...]({url})" for i, (chunk, url) in enumerate(context_chunks)]
        )
        user_msg = f"Context:\n{context}\n\nQuestion: {query}"
    else:
        user_msg = (
            "No internal documentation was found related to the question below. "
            "If you cannot find an answer based on known internal content, respond with: "
            "'I couldn't find that in the notion workspace.'\n\n"
            f"Question: {query}"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    for entry in history:
        if entry["role"] in ["user", "assistant"]:
            messages.append(entry)

    messages.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model=model_version,
        messages=messages,
        temperature=0.2,
    )

    return response.choices[0].message.content



def get_referenced_chunks_from_answer(answer, chunks):
    referenced = []

    for text, url in chunks:
        # Look for explicit phrases (names, matrix, titles) in GPT answer
        key_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)  # Find proper nouns or titles
        for phrase in key_phrases:
            if len(phrase) < 5:
                continue  # Ignore short ones
            if phrase in answer:
                referenced.append((text, url))
                break  # no need to check more phrases in same chunk

    return referenced

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("message", "")
    history = data.get("history", [])

    if not query:
        return jsonify({"reply": "No query provided."}), 400

    with index_lock:
        if not index:
            return jsonify({"reply": "Index is still loading. Please try again shortly."})

        # Try to generate embedding for the query
        try:
            response = client.embeddings.create(input=[query], model="text-embedding-3-small")
            query_embedding = np.array(response.data[0].embedding).astype("float32")
        except Exception as e:
            print(f"🟥 Error generating embedding for query '{query}': {e}")
            return jsonify({"reply": "Sorry, failed to process your question."}), 500

        # Search index for relevant chunks
        D, I = index.search(np.array([query_embedding]), k_results)
        min_distance = D[0][0]

        # Logging for debugging
        print(f"🔍 Query: {query}")
        print(f"📏 Min distance: {min_distance:.4f}")
        print(f"🧠 Top chunk text: {chunked_pairs[I[0][0]][0][:100]}...")
        print(f"🔗 Top chunk source: {chunked_pairs[I[0][0]][1]}")

        relevance_threshold = 1

        if min_distance < relevance_threshold:
            relevant_chunks = [chunked_pairs[i] for i in I[0] if i < len(chunked_pairs)]

            for idx, (text, url) in enumerate(relevant_chunks):
                print(f"🧩 Chunk {idx + 1}:\n{text[:200]}...\n🔗 {url}\n")

            answer = ask_gpt(query, relevant_chunks, chat_model, history)
            print(f"🧾 GPT Response (with context):\n{answer}")

            referenced_chunks = get_referenced_chunks_from_answer(answer, relevant_chunks)

            # Always show 3 links max: GPT-extracted references (or top 3 fallback)
            final_chunks = referenced_chunks[:3] if referenced_chunks else relevant_chunks[:3]
            sources = "\n".join(f"[{text[:60]}...]({url})" for text, url in final_chunks)
            reply = f"{answer}\n\nSources:\n{sources}"
        else:
            answer = ask_gpt(query, [], chat_model, history)
            reply = answer
            print(f"🧾 GPT Response (with context):\n{answer}")
            print("🔴 No relevant context found — skipping sources.")

    return jsonify({"reply": reply})



def refresh_index():
    global chunked_pairs, index

    print("\nBackground: Starting Notion refresh...")

    raw_pairs = extract_text_from_pages(ids, depth_filter)
    print(f"Crawled {len(raw_pairs)} blocks from Notion.")

    new_chunked_pairs = chunk_text_with_sources(raw_pairs)
    print(f"Split into {len(new_chunked_pairs)} chunks (~300 tokens each).")

    print("Sending chunks to OpenAI for embedding...")   
    new_embeddings = get_embeddings(new_chunked_pairs)
    print("Received embeddings from OpenAI.")

    new_index = create_faiss_index(new_embeddings)
    print("FAISS index created and populated.")

    with index_lock:
        chunked_pairs = new_chunked_pairs
        index = new_index

    print("Background: FAISS index refreshed.")

def schedule_background_refresh(interval_min=10):
    """
    Starts a background thread that refreshes the Notion crawl,
    embeddings, and FAISS index every `interval_sec` seconds.
    """
    def background_loop():
        while True:
            time.sleep(interval_min * 60)
            refresh_index()

    thread = threading.Thread(target=background_loop, daemon=True)
    thread.start()

if __name__ == "__main__":
    ids = id_list

    # Startup and recrawl sequence
    refresh_index()                      
    schedule_background_refresh(recrawl_interval)

    # Logic
    print("Ask questions below:")

    while True:
        ids = id_list
        refresh_index()
        schedule_background_refresh(recrawl_interval)
        app.run(host="0.0.0.0", port=5000)
