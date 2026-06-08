variable "region" {
  description = "AWS リージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "bucket_name" {
  description = "S3 バケット名（全世界でユニークであること）"
  type        = string
}

variable "prefix" {
  description = "S3 オブジェクトのプレフィックス（末尾スラッシュあり）"
  type        = string
  default     = "qiita/"
}
