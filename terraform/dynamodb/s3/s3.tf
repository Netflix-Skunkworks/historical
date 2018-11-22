// S3 SPECIFIC VARIABLES:
// Set the default values for the Read and Write capacities to your environment's needs
variable "CURRENT_TABLE" {
  default = "HistoricalS3CurrentTable"
}

variable "CURRENT_TABLE_READ_CAP" {
  default = 100
}

variable "CURRENT_TABLE_WRITE_CAP" {
  default = 100
}

variable "DURABLE_TABLE" {
  default = "HistoricalS3DurableTable"
}

variable "DURABLE_TABLE_READ_CAP" {
  default = 100
}

variable "DURABLE_TABLE_WRITE_CAP" {
  default = 100
}
