"""
uploader_s3.py - AWS S3 への画像アップロードモジュール

qiita_post.py から使用する。
- S3 への画像アップロード
- ETag によるファイル変更検知（未変更ファイルのアップロードをスキップ）
- CloudFront URL の返却

config["s3"] キーの構造:
  {
    "bucket":         "バケット名",
    "region":         "ap-northeast-1",
    "prefix":         "qiita/",
    "cloudfront_url": "https://xxx.cloudfront.net",
    "profile":        "qiita-post"  # 省略時は default プロファイル
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
    """ローカルファイルの MD5 ハッシュを返す（S3 ETag との比較用）"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def upload(local_path: str, config: dict) -> str:
    """
    画像を S3 にアップロードし CloudFront URL を返す。
    ETag が一致する場合はアップロードをスキップしてキャッシュ済み URL を返す。
    失敗時は RuntimeError を送出する。
    """
    s3_conf = config.get("s3", {})
    bucket   = s3_conf.get("bucket", "")
    prefix   = s3_conf.get("prefix", "")
    cf_url   = s3_conf.get("cloudfront_url", "").rstrip("/")
    region   = s3_conf.get("region", "ap-northeast-1")
    profile  = s3_conf.get("profile")

    if not bucket:
        raise RuntimeError("config.json の s3.bucket が設定されていません。")
    if not cf_url:
        raise RuntimeError("config.json の s3.cloudfront_url が設定されていません。")

    path = Path(local_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"画像ファイルが見つかりません: {local_path}")

    key = f"{prefix}{path.name}"
    dest_url = f"{cf_url}/{key}"

    session = boto3.Session(profile_name=profile)
    s3 = session.client("s3", region_name=region)

    local_md5 = _file_md5(path)
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        remote_etag = head["ETag"].strip('"')
        if remote_etag == local_md5:
            print(f"  スキップ（変更なし）: {key}")
            return dest_url
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchKey"):
            raise RuntimeError(f"S3 確認失敗: {e}") from e

    try:
        s3.upload_file(str(path), bucket, key)
    except ClientError as e:
        raise RuntimeError(f"S3 アップロード失敗: {e}") from e

    print(f"  アップロード完了: {key}")
    return dest_url
