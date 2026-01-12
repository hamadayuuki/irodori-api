"""
Firebase Service for handling storage and Firestore operations.

## Firebase Setup Instructions (初回のみ)

### 1. Firebase Consoleでプロジェクトを作成
   1. https://console.firebase.google.com/ にアクセス
   2. 「プロジェクトを追加」をクリック
   3. プロジェクト名を入力（例: irodori-fashion）
   4. Google Analyticsは任意で有効化

### 2. Firebase Storageを有効化
   1. Firebase Consoleで左メニューから「ビルド」→「Storage」を選択
   2. 「使ってみる」をクリック
   3. セキュリティルールを設定（テストモードでOK、後で変更可能）
   4. ロケーションを選択（例: asia-northeast1 - Tokyo）
   5. 「完了」をクリック

### 3. Cloud Firestoreを有効化
   1. Firebase Consoleで左メニューから「ビルド」→「Firestore Database」を選択
   2. 「データベースの作成」をクリック
   3. セキュリティルールを設定（テストモードでOK、後で変更可能）
   4. ロケーションを選択（例: asia-northeast1 - Tokyo）
   5. 「有効にする」をクリック

### 4. サービスアカウントキーをダウンロード
   1. Firebase Consoleで左上の歯車アイコン → 「プロジェクトの設定」をクリック
   2. 「サービスアカウント」タブを選択
   3. 「新しい秘密鍵の生成」をクリック
   4. JSONファイルがダウンロードされる（例: irodori-fashion-firebase-adminsdk-xxxxx.json）
   5. このファイルを安全な場所に保存（例: /path/to/serviceAccountKey.json）
   ⚠️ このファイルは機密情報を含むため、絶対にGitにコミットしないでください

### 5. Storageのバケット名を確認
   1. Firebase Consoleで「Storage」を開く
   2. 上部に表示されているバケット名をコピー（例: your-project.appspot.com）

### 6. 環境変数を設定

   #### ローカル開発の場合:
   以下の環境変数を.envファイルまたはシェルで設定

   ```bash
   export FIREBASE_STORAGE_BUCKET="your-project.appspot.com"
   export GOOGLE_GENAI_API_KEY="your-gemini-api-key"
   ```

   #### 本番環境（Render等）の場合:
   Environment Variablesセクションで以下を設定
   - FIREBASE_STORAGE_BUCKET: Storageバケット名
   - GOOGLE_GENAI_API_KEY: Gemini APIキー

### 7. Firestoreのインデックスを作成（optional, クエリ実行時にエラーが出た場合のみ）
   エラーメッセージに表示されるURLからインデックスを自動作成できます

### 8. Storage セキュリティルールの設定（本番環境用）
   Firebase Console → Storage → ルールタブで以下を設定:

   ```
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       match /coordinates/{userId}/{allPaths=**} {
         // 認証済みユーザーは自分のフォルダのみ読み書き可能
         allow read: if request.auth != null;
         allow write: if request.auth != null && request.auth.uid == userId;
       }
     }
   }
   ```

### 9. Firestore セキュリティルールの設定（本番環境用）
   Firebase Console → Firestore Database → ルールタブで以下を設定:

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /coordinates/{coordinateId} {
         // 認証済みユーザーは自分のcoordinatesのみ読み書き可能
         allow read: if request.auth != null && resource.data.user_id == request.auth.uid;
         allow create: if request.auth != null && request.resource.data.user_id == request.auth.uid;
         allow update, delete: if request.auth != null && resource.data.user_id == request.auth.uid;
       }

       match /items/{itemId} {
         allow read: if request.auth != null;
         allow write: if request.auth != null;
       }
     }
   }
   ```

### トラブルシューティング
- エラー: "The caller does not have permission"
  → サービスアカウントの権限を確認。Firebase ConsoleでIAMと管理を確認

- エラー: "Bucket not found"
  → FIREBASE_STORAGE_BUCKETが正しいバケット名か確認（gs://は不要）
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, storage, firestore
from io import BytesIO


class FirebaseService:
    _initialized = False
    _db = None
    _bucket = None

    def __init__(self):
        """
        Initialize Firebase Admin SDK if not already initialized.

        環境変数:
            FIREBASE_STORAGE_BUCKET: Storageバケット名（例: your-project.appspot.com）
        """
        if not FirebaseService._initialized:
            try:
                # Try to get credentials from environment variable
                cred_path = "/etc/secrets/irodori-e5c71-firebase-adminsdk-fbsvc-6b9a947875.json"

                if cred_path and os.path.exists(cred_path):
                    # ローカル開発: JSONファイルから認証情報を読み込み
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
                    })
                else:
                    # 本番環境: GOOGLE_APPLICATION_CREDENTIALS環境変数を使用
                    # または Application Default Credentials (ADC) を使用
                    firebase_admin.initialize_app(options={
                        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
                    })

                FirebaseService._initialized = True
                FirebaseService._db = firestore.client()
                FirebaseService._bucket = storage.bucket()

                print("Firebase initialized successfully")
            except Exception as e:
                print(f"Error initializing Firebase: {e}")
                raise

    @property
    def db(self):
        """Get Firestore client."""
        if FirebaseService._db is None:
            FirebaseService._db = firestore.client()
        return FirebaseService._db

    @property
    def bucket(self):
        """Get Storage bucket."""
        if FirebaseService._bucket is None:
            FirebaseService._bucket = storage.bucket()
        return FirebaseService._bucket

    def upload_image(self, image_data: bytes, folder: str = "coordinates") -> str:
        """
        Upload image to Firebase Storage.

        Args:
            image_data: Image binary data
            folder: Storage folder path

        Returns:
            str: Public URL of uploaded image
        """
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            blob_name = f"{folder}/{file_id}.jpg"

            # Upload to Storage
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(image_data, content_type='image/jpeg')

            # Make the blob publicly accessible
            blob.make_public()

            return blob.public_url
        except Exception as e:
            print(f"Error uploading image: {e}")
            raise

    def save_coordinate(
        self,
        user_id: str,
        coordinate_id: str,
        image_path: str,
        ai_catchphrase: str,
        ai_review_comment: str,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Save coordinate data to Firestore.

        Args:
            user_id: User ID
            coordinate_id: Coordinate ID
            image_path: Firebase Storage image URL
            ai_catchphrase: AI generated catchphrase
            ai_review_comment: AI generated review comment
            tags: Optional tags list

        Returns:
            dict: Saved coordinate data
        """
        try:
            coordinate_data = {
                'id': coordinate_id,
                'user_id': user_id,
                'date': datetime.now().isoformat(),
                'coordinate_image_path': image_path,
                'ai_catchphrase': ai_catchphrase,
                'ai_review_comment': ai_review_comment,
                'tags': tags or [],
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }

            # Save to Firestore
            doc_ref = self.db.collection('coordinates').document(coordinate_id)
            doc_ref.set(coordinate_data)

            return coordinate_data
        except Exception as e:
            print(f"Error saving coordinate: {e}")
            raise

    def save_item(
        self,
        item_id: str,
        coordinate_id: str,
        item_type: str,
        item_image_path: str
    ) -> Dict[str, Any]:
        """
        Save item data to Firestore.

        Args:
            item_id: Item ID
            coordinate_id: Related coordinate ID
            item_type: Type of item (e.g., 'tops', 'bottoms', 'shoes')
            item_image_path: Firebase Storage image URL

        Returns:
            dict: Saved item data
        """
        try:
            item_data = {
                'id': item_id,
                'coordinate_id': coordinate_id,
                'item_type': item_type,
                'item_image_path': item_image_path,
                'created_at': firestore.SERVER_TIMESTAMP
            }

            # Save to Firestore
            doc_ref = self.db.collection('items').document(item_id)
            doc_ref.set(item_data)

            return item_data
        except Exception as e:
            print(f"Error saving item: {e}")
            raise

    def get_user_coordinates(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's recent coordinates from Firestore.

        Args:
            user_id: User ID
            limit: Maximum number of coordinates to retrieve

        Returns:
            list: List of coordinate data
        """
        try:
            # Query coordinates by user_id, ordered by date
            docs = (
                self.db.collection('coordinates')
                .where('user_id', '==', user_id)
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )

            coordinates = []
            for doc in docs:
                data = doc.to_dict()
                # Convert Timestamp to string if exists
                if 'created_at' in data and data['created_at']:
                    data['created_at'] = data['created_at'].isoformat() if hasattr(data['created_at'], 'isoformat') else str(data['created_at'])
                if 'updated_at' in data and data['updated_at']:
                    data['updated_at'] = data['updated_at'].isoformat() if hasattr(data['updated_at'], 'isoformat') else str(data['updated_at'])
                coordinates.append(data)

            return coordinates
        except Exception as e:
            print(f"Error getting user coordinates: {e}")
            return []

    def get_coordinate_items(self, coordinate_id: str) -> List[Dict[str, Any]]:
        """
        Get items for a specific coordinate.

        Args:
            coordinate_id: Coordinate ID

        Returns:
            list: List of item data
        """
        try:
            docs = (
                self.db.collection('items')
                .where('coordinate_id', '==', coordinate_id)
                .stream()
            )

            items = []
            for doc in docs:
                data = doc.to_dict()
                items.append(data)

            return items
        except Exception as e:
            print(f"Error getting coordinate items: {e}")
            return []

    def get_coordinate_by_id(self, coordinate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific coordinate by ID.

        Args:
            coordinate_id: Coordinate ID

        Returns:
            dict or None: Coordinate data
        """
        try:
            doc = self.db.collection('coordinates').document(coordinate_id).get()
            if doc.exists:
                data = doc.to_dict()
                # Convert Timestamp to string
                if 'created_at' in data and data['created_at']:
                    data['created_at'] = data['created_at'].isoformat() if hasattr(data['created_at'], 'isoformat') else str(data['created_at'])
                if 'updated_at' in data and data['updated_at']:
                    data['updated_at'] = data['updated_at'].isoformat() if hasattr(data['updated_at'], 'isoformat') else str(data['updated_at'])
                return data
            return None
        except Exception as e:
            print(f"Error getting coordinate by ID: {e}")
            return None
