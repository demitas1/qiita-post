resource "aws_iam_user" "uploader" {
  name = "qiita-post-uploader"
}

resource "aws_iam_access_key" "uploader" {
  user = aws_iam_user.uploader.name
}

# アップロード専用の最小権限ポリシー
resource "aws_iam_user_policy" "uploader" {
  name = "qiita-post-s3-upload"
  user = aws_iam_user.uploader.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:PutObject"
      Resource = "${aws_s3_bucket.images.arn}/*"
    }]
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
