from __future__ import annotations
import logging
import spacy
import json
logger  = logging.getLogger(__name__)
DEFAULT_CHUNK_SIZE_WORDS = 300
DEFAULT_OVERLAP_WORDS  = 50

_nlp  = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        try :
            _nlp  = spacy.load("en_core_web_sm",disable=["ner", "tagger", "lemmatizer", "attribute_ruler"])
        except OSError:
            logger.error("spaCy model 'en_core_web_sm' not found. Install it with:\n")
            raise
    return _nlp


def _split_into_sentences(text : str) -> list[str] :
    nlp = _get_nlp()
    doc  = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def chunk_text(text:str,chunk_size_words : int = DEFAULT_CHUNK_SIZE_WORDS,overlap_words : int=DEFAULT_OVERLAP_WORDS,):
    if not text or not text.strip():
        return []
    if overlap_words >= chunk_size_words:
        logger.warning("overlap_words (%d) >= chunk_size_words (%d); reducing overlap to avoid infinite loop",overlap_words, chunk_size_words)
        overlap_words  = chunk_size_words // 4

    sentences  = _split_into_sentences(text)
    if not sentences :
        return []

    chunks : list[str]  = []
    current_words : list[str] = []

    for sentence in sentences:
        sentence_words  = sentence.split()
        if len(sentence_words) > chunk_size_words:
            if current_words :
                chunks.append(" ".join(current_words))
                current_words  = []
            chunks.append(sentence)
            continue




# ---- standalone test ----
# Run directly with: uv run python -m core_engine.rag.chunking
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
 
    sample_text = (
        "Warfarin is an anticoagulant used to prevent blood clots, e.g. in patients with A-fib. "
        "It works by inhibiting vitamin K-dependent clotting factors (approx. 5.0 mg/day dosing). "
        "Amoxicillin is a penicillin-class antibiotic commonly used for bacterial infections, "
        "including those caused by Dr. Fleming's famously discovered mold-derived compounds. "
        "When taken together, amoxicillin may alter gut flora responsible for vitamin K synthesis. "
        "This can potentiate the anticoagulant effect of warfarin, increasing INR and bleeding risk. "
        "Clinicians should monitor INR more frequently when these drugs are co-administered. "
    ) 

    result  = split_into_sentences(sample_text)
    print(result)
    print(type(result))
    # with open("chunking_doc.json","w") as f:
    #     json.dump(result,f)


 
    # chunks = chunk_document(
    #     sample_text,
    #     title="Warfarin-Amoxicillin Interaction Overview",
    #     source="test",
    #     url="https://example.com",
    #     drug_names=["Warfarin", "Amoxicillin"],
    #     chunk_size_words=50,  # small size here just to demonstrate multiple chunks
    #     overlap_words=10,
    # )
 
    # print(f"Produced {len(chunks)} chunk(s)\n")
    # for i, c in enumerate(chunks):
    #     word_count = len(c["text"].split())
    #     print(f"--- Chunk {i+1} ({word_count} words) ---")
    #     print(c["text"])
    #     print()
 


