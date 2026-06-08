variable "cloudflare_api_token" {
  description = "Cloudflare API トークン（Workers R2 Storage: Edit 権限）"
  type        = string
  sensitive   = true
}

variable "account_id" {
  description = "Cloudflare アカウント ID"
  type        = string
}

variable "bucket_name" {
  description = "R2 バケット名"
  type        = string
  default     = "qiita-post-images"
}
