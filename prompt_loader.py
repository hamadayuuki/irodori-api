"""
Prompt Loader Utility

テキストファイルからプロンプトを読み込むユーティリティ
"""

import os
from pathlib import Path
from typing import Dict


class PromptLoader:
    """プロンプトファイル管理クラス"""

    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize Prompt Loader

        Args:
            prompts_dir: プロンプトファイルが格納されているディレクトリ
        """
        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load(self, prompt_name: str, use_cache: bool = True) -> str:
        """
        プロンプトファイルを読み込む

        Args:
            prompt_name: プロンプトファイル名（拡張子なし）
            use_cache: キャッシュを使用するか（デフォルト: True）

        Returns:
            str: プロンプトテキスト

        Raises:
            FileNotFoundError: プロンプトファイルが見つからない場合
        """
        # キャッシュチェック
        if use_cache and prompt_name in self._cache:
            return self._cache[prompt_name]

        # ファイルパス構築
        prompt_file = self.prompts_dir / f"{prompt_name}.txt"

        if not prompt_file.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_file}\n"
                f"Please create the file at: {prompt_file.absolute()}"
            )

        # ファイル読み込み
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt = f.read()

            # キャッシュに保存
            self._cache[prompt_name] = prompt

            return prompt

        except Exception as e:
            raise IOError(f"Error reading prompt file {prompt_file}: {e}")

    def format(self, prompt_name: str, **kwargs) -> str:
        """
        プロンプトファイルを読み込んでフォーマット

        Args:
            prompt_name: プロンプトファイル名（拡張子なし）
            **kwargs: フォーマット用のキーワード引数

        Returns:
            str: フォーマット済みプロンプトテキスト

        Example:
            loader = PromptLoader()
            prompt = loader.format("analyze_recent_coordinates", tags="カジュアル, シンプル")
        """
        template = self.load(prompt_name)
        return template.format(**kwargs)

    def clear_cache(self):
        """キャッシュをクリア"""
        self._cache.clear()

    def list_prompts(self) -> list:
        """
        利用可能なプロンプトファイル一覧を取得

        Returns:
            list: プロンプトファイル名のリスト（拡張子なし）
        """
        if not self.prompts_dir.exists():
            return []

        return [
            f.stem
            for f in self.prompts_dir.glob("*.txt")
            if f.is_file()
        ]


# グローバルインスタンス（シングルトンパターン）
_prompt_loader = None


def get_prompt_loader(prompts_dir: str = "prompts") -> PromptLoader:
    """
    PromptLoaderのグローバルインスタンスを取得

    Args:
        prompts_dir: プロンプトディレクトリ

    Returns:
        PromptLoader: プロンプトローダーインスタンス
    """
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader(prompts_dir)
    return _prompt_loader
