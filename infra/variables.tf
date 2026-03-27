variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "project" {
  type    = string
  default = "fineas"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for EC2 access (contents of ~/.ssh/fineas-ec2.pub)"
}
