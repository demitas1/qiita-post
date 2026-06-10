resource "aws_iam_user" "uploader" {
  name = "qiita-post-uploader"
}

resource "aws_iam_access_key" "uploader" {
  user = aws_iam_user.uploader.name
}

# アップロード専用の最小権限ポリシー
# GetObject: HeadObject で ETag 確認（重複アップロード防止）に必要
# DeleteObject: S3 オブジェクトの削除（管理用途）
# ListBucket: HeadObject が存在しないキーに対して 404 を返すために必要（なければ 403 になる）
resource "aws_iam_user_policy" "uploader" {
  name = "qiita-post-s3-upload"
  user = aws_iam_user.uploader.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.images.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.images.arn
      }
    ]
  })
}

# CloudFront OAC からの GetObject を許可するバケットポリシー
resource "aws_s3_bucket_policy" "images" {
  bucket     = aws_s3_bucket.images.id
  depends_on = [aws_s3_bucket_public_access_block.images]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.images.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.images.arn
        }
      }
    }]
  })
}
