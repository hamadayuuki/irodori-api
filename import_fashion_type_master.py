#!/usr/bin/env python3
"""
ファッションタイプマスターデータをFirestoreにインポートするバッチスクリプト

使用方法:
    python import_fashion_type_master.py

動作:
    - fashion-type.md から16タイプ、4グループ、10質問、4軸のデータを抽出
    - Firestoreの4つのコレクションに保存
      - fashion-type-master (16件)
      - fashion-type-groups (4件)
      - fashion-type-questions (10件)
      - fashion-type-axes (4件)
"""

import sys
import re
import os
import firebase_admin
from firebase_admin import credentials, firestore


# 16タイプのタイプコードとタイプ名のマッピング
TYPE_MAPPING = {
    "TPAQ": "アヴァンギャルド・スター",
    "TPAE": "トレンド・エディター",
    "TPFQ": "アクティブ・クリエイター",
    "TPFE": "スマート・フォロワー",
    "TRAQ": "ソーシャル・アイコン",
    "TRAE": "モテ・プランナー",
    "TRFQ": "エグゼクティブ・ノマド",
    "TRFE": "クリーン・スタンダード",
    "CPAQ": "オーセンティック・アーティスト",
    "CPAE": "ヴィンテージ・ミニマリスト",
    "CPFQ": "ヘビー・デューティー",
    "CPFE": "セルフ・ミニマリスト",
    "CRAQ": "ロイヤル・クラシック",
    "CRAE": "トラッド・コンサバ",
    "CRFQ": "プロフェッショナル・ギア",
    "CRFE": "エッセンシャル・ワーカー"
}

# グループマッピング
GROUP_MAPPING = {
    "TP": {"name": "流行・自己起点", "color": "ピンク", "nuance": "常に新しく、誰にも似ていない個性を放つ色"},
    "TR": {"name": "流行・社会起点", "color": "ゴールド", "nuance": "周囲を明るく彩り、場に価値を与える主役の色"},
    "CP": {"name": "定番・自己起点", "color": "青色", "nuance": "使うほどに深まり、自分の一部になるこだわりの色"},
    "CR": {"name": "定番・社会起点", "color": "ネイビー", "nuance": "規律と伝統を重んじ、絶対的な信頼を与える色"}
}

# 質問データ
QUESTIONS_DATA = [
    {
        "question_id": "Q1",
        "order": 1,
        "axis": "トレンド感度",
        "axis_code": "Trend",
        "question_text": "SNSや雑誌、街のディスプレイで「今年の流行」をチェックするのが楽しい。",
        "viewpoint": "新しい刺激や変化へのポジティブな反応（トレンド受容性）。",
        "navigation": "例えば、季節の変わり目に「今年はどんな色が流行るんだろう？」とワクワクして調べ始めるタイプですか？"
    },
    {
        "question_id": "Q2",
        "order": 2,
        "axis": "トレンド感度",
        "axis_code": "Trend",
        "question_text": "自分のスタイルは既に決まっており、流行に関係なく「いつもの感じ」が一番落ち着く。",
        "viewpoint": "普遍性・安定性への志向（クラシック志向）。",
        "navigation": "例えば、10年前の自分が着ていた服を、今そのまま着ても違和感がない、あるいは「自分の制服」のような定番が決まっている方は高い数値になります。"
    },
    {
        "question_id": "Q3",
        "order": 3,
        "axis": "思考の起点",
        "axis_code": "Origin",
        "question_text": "服を選ぶとき、周囲の目よりも「自分が今日、どんな気分でいたいか」を優先する。",
        "viewpoint": "自己の内面・感情に基づく意思決定（自己起点）。",
        "navigation": "例えば、雨の日でも自分が大好きな明るい色の服を着ることで、自分のテンションを上げたい！と思うタイプですか？"
    },
    {
        "question_id": "Q4",
        "order": 4,
        "axis": "思考の起点",
        "axis_code": "Origin",
        "question_text": "「なりたい自分」や「理想のイメージ」に近づくためのツールとして服を選んでいる。",
        "viewpoint": "自己実現・理想自己の投影。",
        "navigation": "例えば、「今日は仕事ができる人に見せたい」「大人っぽく見られたい」など、自分のなりたい姿を服で作ろうとしますか？"
    },
    {
        "question_id": "Q5",
        "order": 5,
        "axis": "思考の起点",
        "axis_code": "Origin",
        "question_text": "誰かと会うときは、その相手が「自分にどんな印象を抱くか」をまず最初に考える。",
        "viewpoint": "対人関係における調和と印象管理（社会起点）。",
        "navigation": "例えば、初対面の人に会うとき「この服なら失礼がないか」「清潔感があって安心してもらえるか」を真っ先に考えますか？"
    },
    {
        "question_id": "Q6",
        "order": 6,
        "axis": "思考の起点",
        "axis_code": "Origin",
        "question_text": "出かける場所（TPO）のルールや空気に、違和感なく溶け込んでいることが心地よい。",
        "viewpoint": "社会的文脈への適合性（社会起点）。",
        "navigation": "例えば、高級レストランや親戚の集まりで「浮いていないこと」を確認して、初めて安心してその場を楽しめるタイプですか？"
    },
    {
        "question_id": "Q7",
        "order": 7,
        "axis": "価値の置所",
        "axis_code": "Value",
        "question_text": "多少歩きにくかったり、肩が凝ったりしても、シルエットが綺麗な服を選びたい。",
        "viewpoint": "視覚的・審美的な美しさへのこだわり（装飾性）。",
        "navigation": "例えば、「このヒールを履くと足が綺麗に見えるから、多少の痛みは我慢！」と、鏡の中の自分を優先することがありますか？"
    },
    {
        "question_id": "Q8",
        "order": 8,
        "axis": "価値の置所",
        "axis_code": "Value",
        "question_text": "結局、一日中ストレスなく動ける「着心地の良さ」が、自分にとっての正解だ。",
        "viewpoint": "身体的快適さ・利便性の追求（機能性）。",
        "navigation": "例えば、デザインがいくら良くても、素材がチクチクしたり、動きにくかったりする服は、結局クローゼットの肥やしになってしまいますか？"
    },
    {
        "question_id": "Q9",
        "order": 9,
        "axis": "投資の姿勢",
        "axis_code": "Investment",
        "question_text": "服を買うときは、まず値札を見て「この価格なら納得できるか（コスパ）」を吟味する。",
        "viewpoint": "経済的合理性と買い物における得感（経済性）。",
        "navigation": "例えば、同じようなデザインなら「1円でも安い方」や「セールでどれだけお得か」を重視して選びますか？"
    },
    {
        "question_id": "Q10",
        "order": 10,
        "axis": "投資の姿勢",
        "axis_code": "Investment",
        "question_text": "高価であっても、素材の背景やブランドの哲学に共感すれば、長く着るつもりで投資する。",
        "viewpoint": "情緒的価値・耐久性・品質への信頼（品質投資）。",
        "navigation": "例えば、「一生モノ」という言葉に弱かったり、数年後にクタクタにならず、むしろ味が出るような良い素材のものを一着持っていたいと思いますか？"
    }
]

# 軸データ
AXES_DATA = [
    {
        "axis_id": "axis1",
        "axis_name": "トレンド感度",
        "axis_code": "Trend",
        "positive_label": "T (Trend)",
        "negative_label": "C (Classic)",
        "positive_description": "流行：最新のトレンドを追い、新しいものを楽しむ",
        "negative_description": "定番：自分のスタイルが確立され、流行に左右されない",
        "threshold": 3.0,
        "calculation": "(Q1 + (6 - Q2)) / 2",
        "judgment_rule": "スコア >= 3.0 なら T、< 3.0 なら C"
    },
    {
        "axis_id": "axis2",
        "axis_name": "思考の起点",
        "axis_code": "Origin",
        "positive_label": "P (Proactive)",
        "negative_label": "R (Reactive)",
        "positive_description": "自己起点：自分の感性や理想を優先",
        "negative_description": "社会起点：周囲との調和や印象を優先",
        "threshold": None,
        "calculation": "(Q3 + Q4) / 2 と (Q5 + Q6) / 2 を比較",
        "judgment_rule": "自己スコア >= 社会スコアなら P、社会スコア > 自己スコアなら R"
    },
    {
        "axis_id": "axis3",
        "axis_name": "価値の置所",
        "axis_code": "Value",
        "positive_label": "A (Aesthetic)",
        "negative_label": "F (Function)",
        "positive_description": "美学：視覚的な美しさやデザインを重視",
        "negative_description": "機能：着心地や動きやすさを重視",
        "threshold": 3.0,
        "calculation": "(Q7 + Q8) / 2",
        "judgment_rule": "スコア < 3.0 なら A、>= 3.0 なら F"
    },
    {
        "axis_id": "axis4",
        "axis_name": "投資の姿勢",
        "axis_code": "Investment",
        "positive_label": "Q (Quality)",
        "negative_label": "E (Economy)",
        "positive_description": "投資：品質や哲学に共感して投資",
        "negative_description": "節約：コスパや経済性を重視",
        "threshold": 3.0,
        "calculation": "(Q9 + (6 - Q10)) / 2",
        "judgment_rule": "スコア < 3.0 なら Q、>= 3.0 なら E"
    }
]


def parse_type_description(md_path: str, type_code: str) -> str:
    """
    fashion-type.mdから特定のタイプの説明文を抽出

    Args:
        md_path: fashion-type.mdのパス
        type_code: タイプコード (例: "TPAQ")

    Returns:
        tuple: (core_stance, full_description)
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # タイプ名を取得
    type_name = TYPE_MAPPING[type_code]

    # タイプコードをハイフン区切りに変換 (TPAQ -> T-P-A-Q)
    hyphenated_code = '-'.join(type_code)

    # パターン: ## タイプ名 (T-P-A-Q) から次の ## まで
    pattern = rf'## {re.escape(type_name)} \({re.escape(hyphenated_code)}\)\n\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        description = match.group(1).strip()
        # 最初の行（核心となるスタンス）と残りの説明を分離
        lines = description.split('\n', 1)
        core_stance = lines[0].strip() if lines else ""
        full_description = lines[1].strip() if len(lines) > 1 else ""
        return core_stance, full_description

    return "", ""


def import_fashion_type_master(db, md_path: str):
    """ファッションタイプマスターデータをFirestoreにインポート"""
    print("\n[1/4] ファッションタイプマスターデータをインポート中...")

    success_count = 0

    for type_code, type_name in TYPE_MAPPING.items():
        try:
            # 説明文を抽出
            core_stance, description = parse_type_description(md_path, type_code)

            # グループコードを判定（最初の2文字）
            group_code = type_code[:2]
            group_info = GROUP_MAPPING[group_code]

            # 軸情報を抽出
            axes = {
                "axis1": type_code[0],
                "axis1_label": "トレンド" if type_code[0] == "T" else "定番",
                "axis2": type_code[1],
                "axis2_label": "自己起点" if type_code[1] == "P" else "社会起点",
                "axis3": type_code[2],
                "axis3_label": "美学" if type_code[2] == "A" else "機能",
                "axis4": type_code[3],
                "axis4_label": "投資" if type_code[3] == "Q" else "節約"
            }

            # Firestore保存用データ
            master_data = {
                "type_code": type_code,
                "type_name": type_name,
                "description": description,
                "core_stance": core_stance,
                "group": group_info["name"],
                "group_code": group_code,
                "group_color": group_info["color"],
                "group_color_nuance": group_info["nuance"],
                "axes": axes
            }

            # Firestoreに保存
            doc_ref = db.collection('fashion-type-master').document(type_code)
            doc_ref.set(master_data)

            print(f"  ✅ {type_code} - {type_name}")
            success_count += 1

        except Exception as e:
            print(f"  ❌ {type_code} の保存に失敗: {e}")

    print(f"\n  ✅ 合計 {success_count}/16 件のタイプデータを保存しました")
    return success_count


def import_fashion_type_groups(db):
    """ファッションタイプグループデータをFirestoreにインポート"""
    print("\n[2/4] ファッションタイプグループデータをインポート中...")

    # 各グループに含まれるタイプコードを生成
    group_types = {
        "TP": ["TPAQ", "TPAE", "TPFQ", "TPFE"],
        "TR": ["TRAQ", "TRAE", "TRFQ", "TRFE"],
        "CP": ["CPAQ", "CPAE", "CPFQ", "CPFE"],
        "CR": ["CRAQ", "CRAE", "CRFQ", "CRFE"]
    }

    success_count = 0

    for group_code, group_info in GROUP_MAPPING.items():
        try:
            group_data = {
                "group_code": group_code,
                "group_name": group_info["name"],
                "color": group_info["color"],
                "color_nuance": group_info["nuance"],
                "description": f"{group_info['name']}グループ",
                "types": group_types[group_code]
            }

            doc_ref = db.collection('fashion-type-groups').document(group_code)
            doc_ref.set(group_data)

            print(f"  ✅ {group_code} - {group_info['name']}")
            success_count += 1

        except Exception as e:
            print(f"  ❌ {group_code} の保存に失敗: {e}")

    print(f"\n  ✅ 合計 {success_count}/4 件のグループデータを保存しました")
    return success_count


def import_fashion_type_questions(db):
    """ファッションタイプ質問データをFirestoreにインポート"""
    print("\n[3/4] ファッションタイプ質問データをインポート中...")

    success_count = 0

    for question in QUESTIONS_DATA:
        try:
            question_data = {
                **question,
                "scale_type": "1-5",
                "scale_description": "1: 全く当てはまらない 〜 5: 非常に当てはまる"
            }

            doc_ref = db.collection('fashion-type-questions').document(question["question_id"])
            doc_ref.set(question_data)

            print(f"  ✅ {question['question_id']} - {question['axis']}")
            success_count += 1

        except Exception as e:
            print(f"  ❌ {question['question_id']} の保存に失敗: {e}")

    print(f"\n  ✅ 合計 {success_count}/10 件の質問データを保存しました")
    return success_count


def import_fashion_type_axes(db):
    """ファッションタイプ軸データをFirestoreにインポート"""
    print("\n[4/4] ファッションタイプ軸データをインポート中...")

    success_count = 0

    for axis in AXES_DATA:
        try:
            doc_ref = db.collection('fashion-type-axes').document(axis["axis_id"])
            doc_ref.set(axis)

            print(f"  ✅ {axis['axis_id']} - {axis['axis_name']}")
            success_count += 1

        except Exception as e:
            print(f"  ❌ {axis['axis_id']} の保存に失敗: {e}")

    print(f"\n  ✅ 合計 {success_count}/4 件の軸データを保存しました")
    return success_count


def main():
    """メイン処理"""
    print("=" * 70)
    print("ファッションタイプマスターデータをFirestoreにインポート")
    print("=" * 70)

    # fashion-type.mdのパス
    md_path = "/Users/yuki.hamada/Desktop/IRODORI/fashion-type/fashion-type.md"

    # Firebase初期化
    print("\n[初期化] Firebase接続中...")
    try:
        # Firebase認証情報
        cred_path = '/Users/yuki.hamada/Desktop/IRODORI/firebase/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json'

        if not os.path.exists(cred_path):
            print(f"❌ 認証情報ファイルが見つかりません: {cred_path}")
            sys.exit(1)

        # Firebase初期化
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'irodori-e5c71.firebasestorage.app'
        })

        db = firestore.client()
        print("✅ Firebase接続成功")
    except Exception as e:
        print(f"❌ Firebase接続失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # データインポート
    type_count = import_fashion_type_master(db, md_path)
    group_count = import_fashion_type_groups(db)
    question_count = import_fashion_type_questions(db)
    axis_count = import_fashion_type_axes(db)

    # 結果サマリー
    print("\n" + "=" * 70)
    print("インポート完了")
    print("=" * 70)
    print(f"✅ タイプマスター: {type_count} 件 (fashion-type-master)")
    print(f"✅ グループ: {group_count} 件 (fashion-type-groups)")
    print(f"✅ 質問: {question_count} 件 (fashion-type-questions)")
    print(f"✅ 軸: {axis_count} 件 (fashion-type-axes)")
    print(f"\n📊 合計: {type_count + group_count + question_count + axis_count} 件")
    print("\n💡 これらのデータは今後、APIから直接参照できます")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
