# AWS Deployment Plan — Fineas (App Runner + RDS)

## Overview

Deploy the Fineas FastAPI backend to AWS with a shareable HTTPS URL and a full CI/CD pipeline:
tests run on every PR, automatic build + deploy on merge to `main`.

**Why App Runner instead of ECS + ALB:**
ECS Fargate + ALB costs ~$44/month (ALB alone is ~$17/month regardless of traffic). App Runner
has no load balancer — it provides a built-in HTTPS URL — and uses idle pricing when not serving
requests, making it ~$3-18/month for a low-traffic portfolio project.

The Next.js frontend (Phase 5) is not built yet — defer to Vercel when ready.

---

## Architecture

```
GitHub PR   →  .github/workflows/ci.yml     →  pytest (postgres service container)
GitHub main →  .github/workflows/deploy.yml →  ECR push → start-deployment → poll RUNNING

Internet (HTTPS) → App Runner (:8000)
                        ↓  VPC connector (default VPC, public subnets + IGW)
                   RDS PostgreSQL 16 (db.t3.micro, private)

AWS Secrets Manager  →  ANTHROPIC_API_KEY
AWS SSM Param Store  →  DATABASE_URL, CORS_ORIGINS, LLM_PROVIDER
```

### Key design decisions

| Decision | Reason |
|---|---|
| App Runner 0.25 vCPU / 512 MB | Cheapest valid tier; ~$2.60/month at idle |
| VPC connector on default VPC | App Runner egress routes through VPC's IGW → Anthropic API works, no NAT Gateway needed |
| RDS `publicly_accessible = false` | Only reachable from App Runner via VPC connector |
| Migrations in `entrypoint.sh` | Runs `alembic upgrade head` before uvicorn; safe for single instance. If autoscaling is enabled later, move migrations to a pre-deploy CI step |
| GitHub OIDC (no static AWS keys) | IAM role assumed via OIDC token; zero secrets stored in GitHub for AWS auth |
| `auto_deployments_enabled = false` | CI/CD controls deploy via `aws apprunner start-deployment` — gives explicit deploy/wait step |
| Terraform provider `~> 5.0` | Earlier versions have a validation regex bug rejecting CPU/memory values below 1024/2048 |

---

## Cost Estimate

| Service | Configuration | Monthly |
|---|---|---|
| App Runner | 0.25 vCPU / 512 MB, mostly idle | ~$2.60 |
| RDS PostgreSQL 16 | db.t3.micro, 20 GB gp2, single-AZ | ~$14 (**$0** on 12-month free tier) |
| ECR | ~1 GB storage | ~$0.10 |
| Secrets Manager | 2 secrets | ~$0.80 |
| **Total** | | **~$3.50 (during free tier) → ~$17.50 (after)** |

> New AWS accounts receive $200 in credits, covering several months of this setup.

---

## Files to Create / Modify

### 1. `apps/backend/entrypoint.sh` _(new)_

```bash
#!/bin/bash
set -e
python -m alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8000
```

`set -e` ensures a failed migration exits the container immediately — App Runner marks the
deployment as failed and keeps the old version running.

### 2. `apps/backend/Dockerfile` _(modified)_

Two changes from the current version: add `curl` (for the health check) and use `entrypoint.sh`.

```dockerfile
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./entrypoint.sh"]
```

`start-period=90s` gives Alembic time to complete before the first health check fires.

### 3. `infra/` _(new directory — Terraform)_

```
infra/
├── main.tf         # AWS provider (hashicorp/aws ~> 5.0) + S3 remote state backend
├── variables.tf    # aws_region, project, db_password, anthropic_api_key, github_org, github_repo
├── outputs.tf      # service_url, ecr_repository_url, app_runner_service_arn, github_actions_role_arn
├── data.tf         # data sources: default VPC, subnets, current account ID/region
├── ecr.tf          # aws_ecr_repository + lifecycle policy (keep 10 most recent images)
├── sg.tf           # 2 security groups: apprunner_connector (egress all) + rds (ingress 5432 from connector SG)
├── rds.tf          # aws_db_instance (postgres:16, db.t3.micro, publicly_accessible=false)
├── secrets.tf      # Secrets Manager: ANTHROPIC_API_KEY; SSM SecureString: DATABASE_URL; SSM String: CORS_ORIGINS, LLM_PROVIDER
├── iam.tf          # App Runner access role, App Runner instance role, GitHub OIDC provider + role
└── apprunner.tf    # aws_apprunner_vpc_connector + aws_apprunner_service
```

#### `main.tf`

```hcl
terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket         = "fineas-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"          # change to your region
    dynamodb_table = "fineas-terraform-locks"
    encrypt        = true
  }
}

provider "aws" { region = var.aws_region }

locals {
  tags = { Project = var.project, Environment = "prod", ManagedBy = "terraform" }
}
```

#### `variables.tf`

```hcl
variable "aws_region"        { type = string; default = "us-east-1" }
variable "project"           { type = string; default = "fineas" }
variable "db_password"       { type = string; sensitive = true }
variable "anthropic_api_key" { type = string; sensitive = true }
variable "github_org"        { type = string }   # your GitHub username
variable "github_repo"       { type = string; default = "fineas" }
```

#### `data.tf`

```hcl
data "aws_region"          "current" {}
data "aws_caller_identity" "current" {}
data "aws_vpc"     "default" { default = true }
data "aws_subnets" "default" {
  filter { name = "vpc-id"; values = [data.aws_vpc.default.id] }
}
```

#### `ecr.tf`

```hcl
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project}-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{ rulePriority = 1, description = "Keep 10 images",
      selection = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 },
      action = { type = "expire" } }]
  })
}
```

#### `sg.tf`

```hcl
resource "aws_security_group" "apprunner_connector" {
  name   = "${var.project}-apprunner-connector-sg"
  vpc_id = data.aws_vpc.default.id
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
  tags = local.tags
}

resource "aws_security_group" "rds" {
  name   = "${var.project}-rds-sg"
  vpc_id = data.aws_vpc.default.id
  ingress {
    from_port       = 5432; to_port = 5432; protocol = "tcp"
    security_groups = [aws_security_group.apprunner_connector.id]
  }
  tags = local.tags
}
```

#### `rds.tf`

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
  tags       = local.tags
}

resource "aws_db_instance" "postgres" {
  identifier              = "${var.project}-postgres"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  storage_type            = "gp2"
  db_name                 = "fineas"
  username                = "fineas"
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  publicly_accessible     = false
  multi_az                = false
  backup_retention_period = 7
  deletion_protection     = false
  skip_final_snapshot     = true
  tags                    = local.tags
}
```

#### `secrets.tf`

```hcl
# Secrets Manager — for sensitive values
resource "aws_secretsmanager_secret"         "anthropic_api_key" { name = "/${var.project}/prod/ANTHROPIC_API_KEY"; tags = local.tags }
resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

# SSM — DATABASE_URL assembled from RDS endpoint after apply
resource "aws_ssm_parameter" "database_url" {
  name  = "/${var.project}/prod/DATABASE_URL"
  type  = "SecureString"
  value = "postgresql+asyncpg://fineas:${var.db_password}@${aws_db_instance.postgres.address}:5432/fineas"
  tags  = local.tags
}

resource "aws_ssm_parameter" "cors_origins" {
  name  = "/${var.project}/prod/CORS_ORIGINS"
  type  = "String"
  value = "https://placeholder.update-after-apply.com"  # update after first terraform output
  tags  = local.tags
}

resource "aws_ssm_parameter" "llm_provider" {
  name  = "/${var.project}/prod/LLM_PROVIDER"
  type  = "String"
  value = "anthropic"
  tags  = local.tags
}
```

> After `terraform apply`, update `CORS_ORIGINS` with the actual App Runner service URL:
> ```bash
> aws ssm put-parameter --name "/fineas/prod/CORS_ORIGINS" \
>   --value "https://$(terraform output -raw service_url)" \
>   --type String --overwrite
> ```

#### `iam.tf`

```hcl
# ── App Runner access role (pulls image from ECR) ───────────────────────────
resource "aws_iam_role" "apprunner_access" {
  name = "${var.project}-apprunner-access-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "build.apprunner.amazonaws.com" },
      Action = "sts:AssumeRole" }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# ── App Runner instance role (runtime container — reads secrets) ────────────
resource "aws_iam_role" "apprunner_instance" {
  name = "${var.project}-apprunner-instance-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "tasks.apprunner.amazonaws.com" },
      Action = "sts:AssumeRole" }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy" "apprunner_secrets" {
  name = "${var.project}-apprunner-secrets"
  role = aws_iam_role.apprunner_instance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"],
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:/${var.project}/*" },
      { Effect = "Allow", Action = ["ssm:GetParameters", "ssm:GetParameter"],
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/*" }
    ]
  })
}

# ── GitHub OIDC role (no static AWS keys in GitHub) ─────────────────────────
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1",
                     "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
}
resource "aws_iam_role" "github_actions" {
  name = "${var.project}-github-actions-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike   = { "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*" }
      }
    }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy" "github_actions" {
  name = "${var.project}-github-actions-policy"
  role = aws_iam_role.github_actions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow",
        Action = ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage", "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage"],
        Resource = "*" },
      { Effect = "Allow",
        Action  = ["apprunner:StartDeployment", "apprunner:DescribeService", "apprunner:ListOperations"],
        Resource = "*" }
    ]
  })
}
```

#### `apprunner.tf`

```hcl
resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${var.project}-vpc-connector"
  subnets            = data.aws_subnets.default.ids
  security_groups    = [aws_security_group.apprunner_connector.id]
  tags               = local.tags
}

resource "aws_apprunner_service" "backend" {
  service_name = "${var.project}-backend"

  source_configuration {
    authentication_configuration { access_role_arn = aws_iam_role.apprunner_access.arn }
    auto_deployments_enabled = false

    image_repository {
      image_repository_type = "ECR"
      image_identifier      = "${aws_ecr_repository.backend.repository_url}:latest"

      image_configuration {
        port = "8000"
        runtime_environment_variables = { APP_ENV = "production", LOG_LEVEL = "INFO" }
        runtime_environment_secrets = {
          DATABASE_URL      = aws_ssm_parameter.database_url.arn
          ANTHROPIC_API_KEY = aws_secretsmanager_secret.anthropic_api_key.arn
          CORS_ORIGINS      = aws_ssm_parameter.cors_origins.arn
          LLM_PROVIDER      = aws_ssm_parameter.llm_provider.arn
        }
      }
    }
  }

  instance_configuration {
    cpu               = "256"    # 0.25 vCPU
    memory            = "512"    # 512 MB
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.main.arn
    }
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  tags = local.tags
}
```

#### `outputs.tf`

```hcl
output "service_url"              { value = aws_apprunner_service.backend.service_url }
output "ecr_repository_url"       { value = aws_ecr_repository.backend.repository_url }
output "app_runner_service_arn"   { value = aws_apprunner_service.backend.arn }
output "github_actions_role_arn"  { value = aws_iam_role.github_actions.arn }
output "rds_endpoint"             { value = aws_db_instance.postgres.address; sensitive = true }
```

### 4. `.github/workflows/ci.yml` _(new)_

```yaml
name: CI
on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: fineas
          POSTGRES_PASSWORD: fineas
          POSTGRES_DB: fineas
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U fineas"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: apps/backend/requirements*.txt
      - name: Install dependencies
        working-directory: apps/backend
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Create test database
        run: psql -h localhost -U fineas -d fineas -c "CREATE DATABASE fineas_test;"
        env:
          PGPASSWORD: fineas
      - name: Run pytest
        working-directory: apps/backend
        run: pytest -v --tb=short
        env:
          DATABASE_URL: postgresql+asyncpg://fineas:fineas@localhost:5432/fineas
          LLM_PROVIDER: anthropic
          # ANTHROPIC_API_KEY intentionally omitted — tests mock the LLM
```

### 5. `.github/workflows/deploy.yml` _(new)_

```yaml
name: Deploy
on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: us-east-1         # match var.aws_region in Terraform
  ECR_REPOSITORY: fineas-backend

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push image
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
          TAG: ${{ github.sha }}
        run: |
          docker build -t $REGISTRY/$ECR_REPOSITORY:$TAG \
                       -t $REGISTRY/$ECR_REPOSITORY:latest \
                       apps/backend/
          docker push $REGISTRY/$ECR_REPOSITORY:$TAG
          docker push $REGISTRY/$ECR_REPOSITORY:latest

      - name: Trigger App Runner deployment
        run: |
          aws apprunner start-deployment \
            --service-arn ${{ secrets.APP_RUNNER_SERVICE_ARN }}

      - name: Wait for deployment to complete
        run: |
          SERVICE_ARN="${{ secrets.APP_RUNNER_SERVICE_ARN }}"
          for i in $(seq 1 30); do
            STATUS=$(aws apprunner describe-service \
              --service-arn "$SERVICE_ARN" \
              --query "Service.Status" --output text)
            echo "[attempt $i/30] Status: $STATUS"
            [ "$STATUS" = "RUNNING" ] && exit 0
            [[ "$STATUS" == *"FAILED"* || "$STATUS" == "DELETED" ]] && \
              echo "Deployment failed." && exit 1
            sleep 30
          done
          echo "Timed out after 15 minutes." && exit 1
```

---

## GitHub Secrets (2 total)

Add in repo → Settings → Secrets and variables → Actions.

| Secret | Value | How to get it |
|---|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::<account-id>:role/fineas-github-actions-role` | `terraform output github_actions_role_arn` |
| `APP_RUNNER_SERVICE_ARN` | `arn:aws:apprunner:<region>:<account-id>:service/...` | `terraform output app_runner_service_arn` |

All application secrets (`ANTHROPIC_API_KEY`, `DATABASE_URL`, etc.) live in AWS and are never
stored in GitHub.

---

## Bootstrap Steps (one-time, run from your PC)

### Step 0: Prerequisites

```bash
# Verify AWS CLI is configured with admin-level credentials
aws sts get-caller-identity

# Verify Terraform >= 1.7
terraform -version
```

### Step 1: Create Terraform state backend (once)

```bash
AWS_REGION=us-east-1   # change to your preferred region

aws s3api create-bucket \
  --bucket fineas-terraform-state \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

aws s3api put-bucket-versioning \
  --bucket fineas-terraform-state \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket fineas-terraform-state \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws dynamodb create-table \
  --table-name fineas-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $AWS_REGION
```

### Step 2: Terraform apply

```bash
cd infra/

# Create terraform.tfvars (DO NOT commit — add to .gitignore)
cat > terraform.tfvars <<EOF
aws_region        = "us-east-1"
project           = "fineas"
db_password       = "CHOOSE_A_STRONG_PASSWORD"
anthropic_api_key = "sk-ant-..."
github_org        = "your-github-username"
github_repo       = "fineas"
EOF

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Note all four outputs after apply:
```bash
terraform output service_url
terraform output ecr_repository_url
terraform output app_runner_service_arn
terraform output github_actions_role_arn
```

### Step 3: Update CORS_ORIGINS in SSM

```bash
SERVICE_URL=$(terraform output -raw service_url)
aws ssm put-parameter \
  --name "/fineas/prod/CORS_ORIGINS" \
  --value "https://$SERVICE_URL" \
  --type String --overwrite
```

### Step 4: First manual image push

```bash
ECR_URL=$(terraform output -raw ecr_repository_url)

aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin \
    $(echo $ECR_URL | cut -d/ -f1)

docker build -t $ECR_URL:latest apps/backend/
docker push $ECR_URL:latest

# Trigger first deployment
aws apprunner start-deployment \
  --service-arn $(terraform output -raw app_runner_service_arn)
```

Wait ~2-3 minutes, then verify:
```bash
curl https://$(terraform output -raw service_url)/health
# Expected: {"status":"ok"}
```

### Step 5: Add GitHub Secrets

In your GitHub repo: Settings → Secrets and variables → Actions → New repository secret.

Add `AWS_ROLE_ARN` and `APP_RUNNER_SERVICE_ARN` from the Terraform outputs.

### Step 6: Push all new files

Once you've created all the files listed above, push them to `main`. The `deploy.yml` workflow
will trigger and complete the first automated deployment. All future pushes to `main` will
automatically build, push, and deploy.

---

## Verification

```bash
# Health check
curl https://<service_url>/health
# → {"status":"ok"}

# Swagger UI (paste in browser)
https://<service_url>/docs
```

After a CI/CD deploy triggered by a push to `main`:
```bash
aws apprunner describe-service \
  --service-arn <app_runner_service_arn> \
  --query "Service.Status" --output text
# → RUNNING
```

---

## Frontend (Phase 5) — Deferred to Vercel

When the Next.js app is ready:
1. Connect the GitHub repo to Vercel, set root directory to `apps/frontend`
2. Set `NEXT_PUBLIC_API_URL` env var to `https://<service_url>`
3. Fix `apps/frontend/next.config.mjs`: the `/api/*` rewrite destination currently hardcodes
   `localhost:8000` — change to `process.env.NEXT_PUBLIC_API_URL`
4. Update the SSM `CORS_ORIGINS` parameter to include the Vercel URL, then trigger a new
   App Runner deployment to pick up the change

---

## Notes & Gotchas

- **`infra/terraform.tfvars` must be in `.gitignore`** — it contains your DB password and API key
- **App Runner free tier**: App Runner is NOT included in the 12-month free tier, but new accounts
  get $200 in credits which cover it. RDS db.t3.micro IS free for 12 months.
- **Alembic race condition**: Running migrations at startup is safe with a single App Runner
  instance. App Runner can briefly run two instances during rolling deployments — in practice
  this is rarely an issue for a portfolio project. If you ever enable autoscaling, move migrations
  to a pre-deploy step instead.
- **VPC connector + Anthropic API**: When a VPC connector is attached, ALL App Runner egress
  routes through your VPC. The default VPC uses public subnets with an Internet Gateway, so
  outbound internet access (including Anthropic API calls) works without a NAT Gateway.
- **Rotating secrets**: Secrets Manager / SSM values are only pulled at deployment time. If you
  rotate `ANTHROPIC_API_KEY`, trigger a new App Runner deployment to pick up the new value.
