from scraper import Scraper
from nano_graphrag.genkg import GenerateKG
import time
import json

if __name__ == "__main__":
    # STEP 1: Retrieve paper texts

    # Define your search query
    # query = "reinforcement learning reward shaping"

    # print("Step 1: Scraping for papers...")
    # s = time.time()
    # scraper = Scraper()
    # pdf_urls = scraper.find_similar_papers(query, num_results=5, depth=2, return_pdf=True, verbose=True)
    # print(pdf_urls)
    # e = time.time()
    # print("Step 1 took " + str(e-s) + " seconds!")

    # paper_texts = scraper.load_multiple_papers(pdf_urls)
    # print(len(paper_texts))

    # Emergency: Dump to disk and load back in
    # with open("pdfpathtotext.json", "w", encoding="utf-8") as f:
    #     json.dump(paper_texts, f, ensure_ascii=False, indent=2)
    
    print("Step 1 (Alternative): Retrieving paper texts...")
    with open("pdfpathtotext.json", "r", encoding="utf-8") as f:
        paper_texts = json.load(f)
    pdf_urls = list(paper_texts.keys())

    # STEP 2: Generate knowledge graphs

    print("Step 2: Generating knowledge graph...")
    s = time.time()
    genKG = GenerateKG()
    genKG.generate_knowledge_graph(
        paper_paths=pdf_urls,
        paper_texts=paper_texts,
        output_path = "output.html"
    )
    e = time.time()
    print("Step 2 took " + str(e-s) + " seconds!")

    # STEP 3: TODO - Populate graph RAG

    # STEP 4: TODO - Query graph RAG

