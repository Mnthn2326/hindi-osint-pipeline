"""Verification script for embeddings (Phase 4).

Loads clustering/embeddings.npz and computes cosine similarity between specific
posts to sanity-check the SBERT outputs.
"""
import numpy as np

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def main():
    data = np.load("clustering/embeddings.npz")
    post_ids = data["post_ids"].tolist()
    embeddings = data["embeddings"]
    
    print(f"Loaded {len(post_ids)} embeddings.")
    
    # We want to check similarities:
    # Post 2: Mirabai Chanu wins silver at Asian games
    # Post 6: Asian Games live updates, Mirabai gets silver
    # Post 4: UP murders/encounter
    try:
        idx_2 = post_ids.index(2)
        idx_6 = post_ids.index(6)
        idx_4 = post_ids.index(4)
        
        sim_2_6 = cosine_similarity(embeddings[idx_2], embeddings[idx_6])
        sim_2_4 = cosine_similarity(embeddings[idx_2], embeddings[idx_4])
        
        print("\n--- Verification Results ---")
        print(f"Similarity (Post 2, Post 6) [Similar events]:  {sim_2_6:.4f}")
        print(f"Similarity (Post 2, Post 4) [Unrelated events]: {sim_2_4:.4f}")
        
    except ValueError as e:
        print("Required post_ids not found in embeddings.", e)

if __name__ == "__main__":
    main()
