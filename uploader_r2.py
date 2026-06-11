"""
uploader_r2.py - Cloudflare R2 への画像アップロードモジュール

qiita_post.py から使用する。
- R2 への画像アップロード（boto3 S3 互換モード）
- ETag によるファイル変更検知（未変更ファイルのアップロードをスキップ）
- r2.dev または カスタムドメイン URL の返却

config["r2"] キーの構造:
  {
    "account_id":        "Cloudflare アカウント ID",
    "bucket":            "バケット名",
    "prefix":            "qiita/",
    "access_key_id":     "R2 API トークンのアクセスキー",
    "secret_access_key": "R2 API トークンのシークレットキー",
    "public_url":        "https://pub-xxxx.r2.dev"
  }
"""

import hashlib
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("boto3 が必要です: pip install boto3")
    sys.exit(1)


def _file_md5(path: Path) -> str:
    """ローカルファイルの MD5 ハッシュを返す（R2 ETag との比較用）"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def upload(local_path: str, config: dict) -> str:
    """
    画像を R2 にアップロードし公開 URL を返す。
    ETag が一致する場合はアップロードをスキップしてキャッシュ済み URL を返す。
    失敗時は RuntimeError を送出する。
    """
    r2_conf = config.get("r2", {})
    account_id       = r2_conf.get("account_id", "")
    bucket           = r2_conf.get("bucket", "")
    prefix           = r2_conf.get("prefix", "")
    access_key_id    = r2_conf.get("access_key_id", "")
    secret_access_key = r2_conf.get("secret_access_key", "")
    public_url       = r2_conf.get("public_url", "").rstrip("/")

    if not account_id:
        raise RuntimeError("config.json の r2.account_id が設定されていません。")
    if not bucket:
        raise RuntimeError("config.json の r2.bucket が設定されていません。")
    if not access_key_id or not secret_access_key:
        raise RuntimeError("config.json の r2.access_key_id / r2.secret_access_key が設定されていません。")
    if not public_url:
        raise RuntimeError("config.json の r2.public_url が設定されていません。")

    path = Path(local_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"画像ファイルが見つかりません: {local_path}")

    key = f"{prefix}{path.name}"
    dest_url = f"{public_url}/{key}"

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    r2 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name="auto",
    )

    local_md5 = _file_md5(path)
    try:
        head = r2.head_object(Bucket=bucket, Key=key)
        remote_etag = head["ETag"].strip('"')
        if remote_etag == local_md5:
            print(f"  スキップ（変更なし）: {key}")
            return dest_url
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchKey"):
            raise RuntimeError(f"R2 確認失敗: {e}") from e

    try:
        r2.upload_file(str(path), bucket, key)
    except ClientError as e:
        raise RuntimeError(f"R2 アップロード失敗: {e}") from e

    print(f"  アップロード完了: {key}")
    return dest_url
