#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd

# ---------------------------------------------------------------------
# 定数・関数
# ---------------------------------------------------------------------
ALL_TYPES = ["アウター", "トップス", "ボトムス", "シューズ", "アクセサリー"]

def _nfkc(s: str) -> str: return unicodedata.normalize("NFKC", s)
def _norm_text(x: Any) -> str:
    if x is None: return ""
    return re.sub(r"\s+", " ", _nfkc(str(x)).strip().lower())
def _clean_part(x: Any) -> str:
    if x is None or pd.isna(x): return ""
    return _nfkc(str(x)).strip().replace("_", "")
def _norm_key(x: Any) -> str:
    if x is None: return ""
    return re.sub(r"\s+", "", _nfkc(str(x)).strip().lower())

_TYPE_ALIASES = {
    "アウター": {"アウター", "outer", "outerwear", "coat", "jacket", "blouson", "down", "コート", "ジャケット", "ブルゾン", "ダウン", "羽織", "ベスト", "vest"},
    "トップス": {"トップス", "tops", "top", "upper", "shirt", "t-shirt", "cutsew", "knit", "sweater", "hoodie", "parka", "sweat", "シャツ", "ブラウス", "カットソー", "ニット", "セーター", "パーカー", "スウェット", "トレーナー", "tシャツ"},
    "ボトムス": {"ボトムス", "bottoms", "bottom", "pants", "trousers", "skirt", "denim", "jeans", "パンツ", "ズボン", "スカート", "デニム", "ジーンズ", "スラックス"},
    "シューズ": {"シューズ", "shoes", "shoe", "sneaker", "boots", "pumps", "sandals", "loafer", "靴", "スニーカー", "パンプス", "サンダル", "ブーツ", "ローファー", "革靴"},
    "アクセサリー": {"アクセサリー", "アクセ", "accessory", "accessories", "goods", "bag", "hat", "cap", "scarf", "muffler", "stole", "belt", "小物", "バッグ", "鞄", "帽子", "ハット", "キャップ", "マフラー", "ストール", "ベルト", "眼鏡", "メガネ"},
}
_TYPE_ALIASES = {k: {_norm_key(v) for v in vs} for k, vs in _TYPE_ALIASES.items()}

def canon_type(raw: Any) -> Optional[str]:
    s = _norm_key(raw)
    for canon, aliases in _TYPE_ALIASES.items():
        if s in aliases: return canon
    return None

def make_strict_label(item_type: str, item_name: str, color: str) -> str:
    t = _clean_part(item_type)
    n = _clean_part(item_name)
    c = _clean_part(color)
    return f"{t}_{n}_{c}"

# ---------------------------------------------------------------------
# 推論ロジック
# ---------------------------------------------------------------------

def find_similar_items(
    model: Dict[str, Any], 
    itype: str, 
    category: str, 
    text: str,
    top_k: int = 50,
    min_sim: float = 0.0
) -> List[Tuple[str, float]]:
    items = model.get("items", {})
    tfidf = model.get("tfidf", {})
    candidates = []

    query_str = f"{category} {text}"
    
    # 完全一致チェック
    potential_exact_id = make_strict_label(itype, category, text)
    if potential_exact_id in items:
        candidates.append((potential_exact_id, 2.0))

    # TF-IDF類似検索
    idx = tfidf.get(itype)
    if idx:
        vectorizer = idx["vectorizer"]
        matrix = idx["matrix"]
        keys = idx["keys"]

        query_vec = vectorizer.transform([query_str])
        sims = (matrix @ query_vec.T).toarray().ravel()
        
        sorted_indices = sims.argsort()[::-1]
        for i in sorted_indices[:top_k]:
            sim = float(sims[i])
            if sim < min_sim: break
            key = keys[i]
            if key != potential_exact_id:
                candidates.append((key, sim))

    return candidates

def recommend(
    model: Dict[str, Any],
    input_type: str,
    category: str,
    text: str,
    num_outfits: int = 3,
    num_candidates: int = 5,
    min_sim: float = 0.0
) -> Dict[str, Any]:
    
    itype = canon_type(input_type)
    if not itype:
        return {"error": f"Invalid type: {input_type}"}

    # ★変更: 入力と同じタイプは出力から除外する
    exclude_type = itype

    # 1. アイテム検索
    similar_items = find_similar_items(model, itype, category, text, top_k=50, min_sim=min_sim)
    if not similar_items:
        return {"error": "No matching items found."}

    best_match_id, _ = similar_items[0]

    items = model["items"]
    recs = model["recs"]
    item_to_outfits = model.get("item_to_outfits", {})
    outfit_data = model.get("outfit_data", {})

    result = {}

    # -----------------------------------------
    # A. 提案コーデ (入力タイプを除いて出力)
    # -----------------------------------------
    collected_outfits = []
    seen_outfit_ids = set()

    for iid, _ in similar_items:
        oids = item_to_outfits.get(iid, [])
        for oid in oids:
            if oid in seen_outfit_ids: continue

            info = outfit_data.get(oid)
            if not info: continue

            # コーデ情報の構築
            coord_content = {"outfit_image_name": info.get("image_name", "")}
            # 出力に必要なキーを初期化（入力タイプ以外）
            target_output_types = [t for t in ALL_TYPES if t != exclude_type]
            for t in target_output_types:
                coord_content[t] = []

            # コーデ内アイテムを振り分け
            for member_id in info.get("items", []):
                if member_id not in items: continue
                m_detail = items[member_id]
                m_type = m_detail["item_type"]

                # 入力タイプと同じものはコーデリストに含めない
                if m_type == exclude_type:
                    continue

                if m_type in coord_content:
                    coord_content[m_type].append(member_id)

            # JSON文字列化
            final_coord = {"outfit_image_name": coord_content["outfit_image_name"]}
            for t in target_output_types:
                final_coord[t] = " ".join(coord_content[t])

            collected_outfits.append(final_coord)
            seen_outfit_ids.add(oid)
            if len(collected_outfits) >= num_outfits: break
        if len(collected_outfits) >= num_outfits: break

    for i, coord in enumerate(collected_outfits):
        result[f"outfit_{i+1}"] = coord

    # -----------------------------------------
    # B. カテゴリ別一覧 (入力タイプを除いて出力)
    # -----------------------------------------
    co_occurring = recs.get(best_match_id, {})

    # 出力対象のカテゴリのみリスト化
    target_list_types = [t for t in ALL_TYPES if t != exclude_type]

    for t in target_list_types:
        json_key = f"{t}_list"
        candidates = []
        
        # 共起リストから取得
        c_ids = co_occurring.get(t, [])
        for cid in c_ids:
            if cid in items:
                candidates.append(cid)
        
        unique_candidates = list(dict.fromkeys(candidates))
        
        # 不足時の補填
        if len(unique_candidates) < num_candidates and len(similar_items) > 1:
            second_id, _ = similar_items[1]
            co_occurring_2 = recs.get(second_id, {})
            c_ids_2 = co_occurring_2.get(t, [])
            for cid in c_ids_2:
                if cid in items:
                    candidates.append(cid)
            unique_candidates = list(dict.fromkeys(candidates))

        result[json_key] = unique_candidates[:num_candidates]

    return result

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--input_type", required=True)
    ap.add_argument("--category", required=True)
    ap.add_argument("--text", required=True)
    
    ap.add_argument("--outfits_num", type=int, default=3)
    ap.add_argument("--candidates_num", type=int, default=5)
    ap.add_argument("--min_sim", type=float, default=0.0)

    args = ap.parse_args()

    try:
        model = joblib.load(args.model)
        output = recommend(
            model=model,
            input_type=args.input_type,
            category=args.category,
            text=args.text,
            num_outfits=args.outfits_num,
            num_candidates=args.candidates_num,
            min_sim=args.min_sim
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))

if __name__ == "__main__":
    main()