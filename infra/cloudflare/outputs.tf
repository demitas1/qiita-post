output "bucket_name" {
  description = "R2 バケット名"
  value       = cloudflare_r2_bucket.images.name
}

output "r2_endpoint" {
  description = "boto3 用 S3 互換エンドポイント URL"
  value       = "https://${var.account_id}.r2.cloudflarestorage.com"
}
