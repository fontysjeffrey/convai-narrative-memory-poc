import argparse
import json
import os
from typing import Iterable, List

from qdrant_client import QdrantClient
from qdrant_client.http import models


DEFAULT_COLLECTION = os.getenv("QDRANT_COLLECTION", "anchors")
DEFAULT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")


def iter_points(
    client: QdrantClient,
    collection: str,
    limit: int,
    with_vectors: bool,
) -> Iterable[models.Record]:
    fetched = 0
    offset = None
    batch = min(limit, 64)
    while fetched < limit:
        points, offset = client.scroll(
            collection_name=collection,
            limit=min(batch, limit - fetched),
            offset=offset,
            with_payload=True,
            with_vectors=with_vectors,
        )
        if not points:
            break
        for point in points:
            yield point
            fetched += 1
            if fetched >= limit:
                break
        if offset is None:
            break


def describe_payload(payload: dict) -> str:
    text = payload.get("text", "")
    stored = payload.get("stored_at", "?")
    salience = payload.get("salience")
    salience_part = (
        f" salience={salience:.2f}" if isinstance(salience, (int, float)) else ""
    )
    summary = text.strip().replace("\n", " ")
    if len(summary) > 200:
        summary = summary[:197] + "..."
    meta = {
        k: v for k, v in payload.items() if k not in {"text", "stored_at", "salience"}
    }
    extra = f" meta={json.dumps(meta, ensure_ascii=False)}" if meta else ""
    return f"stored={stored}{salience_part}\n    text={summary}{extra}"


def main():
    parser = argparse.ArgumentParser(
        description="Inspect anchors stored in a Qdrant collection."
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"Collection name (default: %(default)s)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Qdrant base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of points to display (default: 20).",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        help="Explicit point IDs to retrieve (overrides limit/scroll).",
    )
    parser.add_argument(
        "--vectors",
        action="store_true",
        help="Include vector payload in the output (can be large).",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Optional path to write the raw results as JSON.",
    )
    args = parser.parse_args()

    client = QdrantClient(url=args.url)

    if args.ids:
        records: List[models.Record] = client.retrieve(
            collection_name=args.collection,
            ids=args.ids,
            with_payload=True,
            with_vectors=args.vectors,
        )
    else:
        records = list(
            iter_points(
                client=client,
                collection=args.collection,
                limit=args.limit,
                with_vectors=args.vectors,
            )
        )

    print(
        f"Collection '{args.collection}' at {args.url} — showing {len(records)} point(s)"
    )
    for idx, record in enumerate(records, 1):
        print(f"\n[{idx}] id={record.id}")
        payload = record.payload or {}
        print(describe_payload(payload))
        if args.vectors and record.vector is not None:
            dim = len(record.vector)
            preview = record.vector[:8]
            print(f"    vector(dim={dim})={preview}...")

    if args.json_path:
        payload = []
        for record in records:
            entry = {
                "id": record.id,
                "payload": record.payload,
            }
            if args.vectors and record.vector is not None:
                entry["vector"] = record.vector
            payload.append(entry)
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\nSaved raw output to {args.json_path}")


if __name__ == "__main__":
    main()
