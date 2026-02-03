variable "src_files" {
  description = "Paths to the source files for the Lambda function"
  type        = list(string)
}

variable "output_path" {
  description = "Output path for the packaged Lambda function"
  type        = string
}