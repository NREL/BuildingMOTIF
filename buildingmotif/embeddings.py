import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import polars as pl
from numba import jit
from rdflib import Graph
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

# disable numba debugging messages
numba_logger = logging.getLogger("numba")
numba_logger.setLevel(logging.WARNING)

BATCH_SIZE = 20


@jit
def fast_dot_product(
    query: np.ndarray, matrix: np.ndarray, k: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    # Ensure the data types are consistent
    query = query.astype(np.float32)
    matrix = matrix.astype(np.float32)

    dot_products = query @ matrix.T

    idx = np.argpartition(dot_products, -k)[-k:]
    idx = idx[np.argsort(dot_products[idx])[::-1]]

    score = dot_products[idx]

    return idx, score


class Embedding:
    """
    Embeds classes of an ontology
    """

    def __init__(
        self,
        graph: Graph,
        cachedir="bmotif-embeddings",
        model_path="Alibaba-NLP/gte-modernbert-base",
    ):
        self.graph = graph
        self.cachedir = Path(cachedir)
        os.makedirs(self.cachedir, exist_ok=True)

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path)

        self.point_embeddings: Optional[np.ndarray] = None
        self.equip_embeddings: Optional[np.ndarray] = None
        self.point_data: Optional[pl.DataFrame] = None
        self.equip_data: Optional[pl.DataFrame] = None

        # load from cache if available
        point_cache_path = self.cachedir / "points.parquet"
        if point_cache_path.exists():
            try:
                loaded_data = pl.read_parquet(point_cache_path)
                if (
                    not loaded_data.is_empty()
                    and "point_embeddings" in loaded_data.columns
                    and "point_ids" in loaded_data.columns
                ):
                    embeddings_list = loaded_data["point_embeddings"].to_list()
                    if embeddings_list:  # Check if the list is not empty
                        self.point_embeddings = np.array(embeddings_list)
                        self.point_data = loaded_data
            except Exception as e:
                logging.warning(
                    f"Failed to load point embeddings from cache {point_cache_path}: {e}"
                )
                self.point_embeddings = None  # Ensure consistent state on failure
                self.point_data = None

        equip_cache_path = self.cachedir / "equip.parquet"
        if equip_cache_path.exists():
            try:
                loaded_data = pl.read_parquet(equip_cache_path)
                if (
                    not loaded_data.is_empty()
                    and "equip_embeddings" in loaded_data.columns
                    and "equip_ids" in loaded_data.columns
                ):
                    embeddings_list = loaded_data["equip_embeddings"].to_list()
                    if embeddings_list:  # Check if the list is not empty
                        self.equip_embeddings = np.array(embeddings_list)
                        self.equip_data = loaded_data
            except Exception as e:
                logging.warning(
                    f"Failed to load equip embeddings from cache {equip_cache_path}: {e}"
                )
                self.equip_embeddings = None  # Ensure consistent state on failure
                self.equip_data = None

        if self.point_embeddings is None and self.equip_embeddings is None:
            self.populate_embeddings()

    def compute_embeddings(self, docs: list[str]) -> np.ndarray:
        tokenized_batch = self.tokenizer(
            docs, max_length=8192, padding=True, truncation=True, return_tensors="pt"
        )
        outputs = self.model(**tokenized_batch)
        embeddings = outputs.last_hidden_state[:, 0].detach().cpu()
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings = embeddings / norm
        return normalized_embeddings.detach().numpy()

    def populate_embeddings(self):
        # build two lists: one of all the embeddings and one of all the ids (uris)
        point_embeddings = []
        point_ids = []
        equip_embeddings = []
        equip_ids = []

        query = """
        SELECT DISTINCT ?class ?label ?unit WHERE {
            ?class rdfs:subClassOf/rdfs:subClassOf+ brick:Point .
            OPTIONAL { ?class brick:hasQuantity/qudt:applicableUnit ?unit }
            ?class a sh:NodeShape, owl:Class .
            ?class rdfs:label ?label .
            FILTER(STRSTARTS(STR(?class), 'https://brickschema.org/schema/Brick#'))
        }
        """
        qres = self.graph.query(query)
        docs = [
            {
                "iri": row["class"],
                "label": row["label"],
                "type": "point",
                "unit": row.get("unit"),
            }
            for row in tqdm(qres.bindings)
        ]
        print(f"Embedding {len(docs)} points")
        for i in tqdm(range(0, len(docs), BATCH_SIZE)):
            batch = docs[i : i + BATCH_SIZE]
            point_embeddings.extend(
                self.compute_embeddings([d["label"] for d in batch])
            )
            point_ids.extend([d["iri"] for d in batch])

        # now do equipment
        query = """
        SELECT DISTINCT ?class ?label WHERE {
            { ?class rdfs:subClassOf brick:Equipment }
            UNION
            { ?class rdfs:subClassOf/rdfs:subClassOf brick:Equipment }
            UNION
            { ?class rdfs:subClassOf/rdfs:subClassOf/rdfs:subClassOf brick:Equipment }

            ?class rdfs:label ?label .
            FILTER NOT EXISTS { ?class brick:aliasOf ?x }
            FILTER(STRSTARTS(STR(?class), 'https://brickschema.org/schema/Brick#'))
        }
        """
        qres = self.graph.query(query)
        docs = [
            {"iri": row["class"], "label": row["label"], "type": "equipment"}
            for row in tqdm(qres.bindings)
        ]
        print(f"Embedding {len(docs)} equipment")
        for i in tqdm(range(0, len(docs), BATCH_SIZE)):
            batch = docs[i : i + BATCH_SIZE]
            equip_embeddings.extend(
                self.compute_embeddings([json.dumps(d) for d in batch])
            )
            equip_ids.extend([d["iri"] for d in batch])

        equip_embeddings_np = np.vstack(equip_embeddings)
        point_embeddings_np = np.vstack(point_embeddings)

        # Store numpy arrays for fast dot product
        self.point_embeddings = point_embeddings_np
        self.equip_embeddings = equip_embeddings_np

        # Create Polars DataFrames for storage and ID mapping
        # Convert numpy array rows to lists for Polars DataFrame
        point_embeddings_list = [row.tolist() for row in point_embeddings_np]
        equip_embeddings_list = [row.tolist() for row in equip_embeddings_np]

        self.point_data = pl.DataFrame(
            {"point_ids": point_ids, "point_embeddings": point_embeddings_list}
        )
        self.equip_data = pl.DataFrame(
            {"equip_ids": equip_ids, "equip_embeddings": equip_embeddings_list}
        )

        os.makedirs(self.cachedir, exist_ok=True)
        self.point_data.write_parquet(self.cachedir / "points.parquet")
        self.equip_data.write_parquet(self.cachedir / "equip.parquet")

    def get_point_matches(self, point: str) -> list[tuple[str, float]]:
        if self.point_embeddings is None or self.point_data is None:
            logging.error("Point embeddings are not loaded.")
            return []
        point_embedding = self.compute_embeddings([point])[0]
        idxs, scores = fast_dot_product(point_embedding, self.point_embeddings)
        return [
            (self.point_data["point_ids"][int(i)], score)
            for i, score in zip(idxs, scores)
        ]

    def get_equip_matches(self, equip: str) -> list[tuple[str, float]]:
        if self.equip_embeddings is None or self.equip_data is None:
            logging.error("Equipment embeddings are not loaded.")
            return []
        equip_embedding = self.compute_embeddings([equip])[0]
        idxs, scores = fast_dot_product(equip_embedding, self.equip_embeddings)
        return [
            (self.equip_data["equip_ids"][int(i)], score)
            for i, score in zip(idxs, scores)
        ]

    def try_align_record(self, record: dict) -> Optional[dict[str, str]]:
        label = record["description"]
        labels: list[tuple[str, str]] = [(label, label)]
        # make every pair of words in the label, split by ' -:.'
        parts = re.split(r"[ -:.]", label)
        # if there are N parts, there are N-1 ways of dividing the string into two parts
        for i in range(1, len(parts)):
            p1 = " ".join(parts[:i])
            p2 = " ".join(parts[i:])
            labels.append((p1, p2))
        # now, 'labels' is a list of pairs of strings. We want to classify each pair
        # as (point, equip) or (equip, point) or (point, point). The get_point_matches
        # and get_equip_matches functions will return the best (match, score) for each
        # string in the pair.
        # We choose the pair with the highest score
        best_score = 0.0
        best_match = None

        scores = []
        for p1, p2 in labels:
            # (point, point)
            p1_point_matches = self.get_point_matches(p1)
            print(f"Point matches for {p1}: {p1_point_matches}")
            p2_point_matches = self.get_point_matches(p2)
            print(f"Point matches for {p2}: {p2_point_matches}")
            # get the best match for each part of the label
            if p1_point_matches and p2_point_matches:
                score = p1_point_matches[0][1] + p2_point_matches[0][1]
                scores.append((p1_point_matches[0][0], p2_point_matches[0][0], score))
                if score > best_score:
                    best_score = score
                    best_match = {"point": p1_point_matches[0][0]}
            # (point, equip)
            p2_equip_matches = self.get_equip_matches(p2)
            if p1_point_matches and p2_equip_matches:
                score = p1_point_matches[0][1] + p2_equip_matches[0][1]
                scores.append((p1_point_matches[0][0], p2_equip_matches[0][0], score))
                if score > best_score:
                    best_score = score
                    best_match = {
                        "point": p1_point_matches[0][0],
                        "equip": p2_equip_matches[0][0],
                    }
            # (equip, point)
            p1_equip_matches = self.get_equip_matches(p1)
            if p1_equip_matches and p2_point_matches:
                score = p1_equip_matches[0][1] + p2_point_matches[0][1]
                scores.append((p1_equip_matches[0][0], p2_point_matches[0][0], score))
                if score > best_score:
                    best_score = score
                    best_match = {
                        "point": p2_point_matches[0][0],
                        "equip": p1_equip_matches[0][0],
                    }
        return best_match

    def try_align_record_equip_only(self, record: dict) -> Optional[dict[str, str]]:
        label = record["description"]
        matches = self.get_equip_matches(label)
        if matches:
            return {"equip": matches[0][0]}
        return None

    def align_records(self, records: list[dict[str, str]]):
        results = {}
        for record in records:
            match = self.try_align_record(record)
            results[record["point"]] = match
        return results

    def align_records_equip_only(self, records: list[dict[str, str]]):
        results = {}
        for record in records:
            match = self.try_align_record_equip_only(record)
            results[record["equip"]] = match
        return results
