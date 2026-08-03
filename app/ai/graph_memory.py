import json
import os
import re
from app.ai.assistant_memory import AssistantMemory


class GraphMemory:
    """Lightweight graph-style memory for related terms and concepts.

    Stores a simple adjacency list in JSON alongside the existing AssistantMemory.
    Provides methods to add nodes, link nodes, query related concepts, and
    a helper to learn from free text by extracting candidate terms.
    """

    def __init__(self, file="astra_graph_memory.json"):
        self.file = file
        self.data = self.load()
        self.data.setdefault("nodes", {})
        self.data.setdefault("edges", {})
        self.assistant_memory = AssistantMemory()

    def load(self):
        if not os.path.exists(self.file):
            return {}
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"nodes": {}, "edges": {}}

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def normalize(self, text):
        if not text:
            return ""
        txt = str(text).lower()
        txt = re.sub(r"[^a-z0-9ığüşöç ]+", " ", txt)
        txt = " ".join(txt.split())
        return txt.strip()

    def add_node(self, term, meta=None):
        key = self.normalize(term)
        if not key:
            return
        self.data["nodes"].setdefault(key, {})
        if meta:
            self.data["nodes"][key].update(meta)
        self.save()

    def link(self, a, b, weight=1):
        a_k = self.normalize(a)
        b_k = self.normalize(b)
        if not a_k or not b_k:
            return
        self.data.setdefault("edges", {})
        self.data["edges"].setdefault(a_k, {})
        self.data["edges"][a_k][b_k] = self.data["edges"][a_k].get(b_k, 0) + weight
        # symmetric
        self.data["edges"].setdefault(b_k, {})
        self.data["edges"][b_k][a_k] = self.data["edges"][b_k].get(a_k, 0) + weight
        self.save()

    def related(self, term, top_n=8):
        k = self.normalize(term)
        if not k:
            return []
        edges = self.data.get("edges", {}).get(k, {})
        sorted_edges = sorted(edges.items(), key=lambda x: -x[1])
        return [item[0] for item in sorted_edges[:top_n]]

    def learn_from_text(self, text):
        # use AssistantMemory's extractor for candidates
        candidates = self.assistant_memory.extract_candidate_terms(text)
        for i, a in enumerate(candidates):
            self.add_node(a)
            for b in candidates[i + 1: i + 1 + 6]:
                self.link(a, b, weight=1)
        return candidates

    def summary(self):
        nodes = list(self.data.get("nodes", {}).keys())
        unknowns = [n for n in nodes if not self.assistant_memory.get_term(n)]
        return {
            "nodes": len(nodes),
            "unknown_terms": unknowns[:20],
        }
