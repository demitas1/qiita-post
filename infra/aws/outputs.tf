output "cloudfront_url" {
  description = "CloudFront ディストリビューションの URL"
  value       = "https://${aws_cloudfront_distribution.images.domain_name}"
}

output "bucket_name" {
  description = "S3 バケット名"
  value       = aws_s3_bucket.images.bucket
}

output "iam_access_key_id" {
  description = "IAM ユーザーのアクセスキー ID（~/.aws/credentials に追記すること）"
  value       = aws_iam_access_key.uploader.id
}

output "iam_secret_access_key" {
  description = "IAM ユーザーのシークレットアクセスキー（再表示不可）"
  value       = aws_iam_access_key.uploader.secret
  sensitive   = true
}
