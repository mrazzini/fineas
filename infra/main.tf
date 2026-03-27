terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket         = "fineas-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "fineas-terraform-locks"
    encrypt        = true
  }
}

provider "aws" { region = var.aws_region }

locals {
  tags = { Project = var.project, Environment = "prod", ManagedBy = "terraform" }
}
