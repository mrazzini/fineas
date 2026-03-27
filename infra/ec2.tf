resource "aws_key_pair" "deployer" {
  key_name   = "${var.project}-deployer"
  public_key = var.ssh_public_key
  tags       = local.tags
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.ec2.id]
  user_data              = file("${path.module}/userdata.sh")

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  tags = merge(local.tags, { Name = "${var.project}-app" })
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  tags     = merge(local.tags, { Name = "${var.project}-eip" })
}
