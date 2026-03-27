output "ec2_public_ip" {
  value       = aws_eip.app.public_ip
  description = "Elastic IP of the EC2 instance"
}

output "ssh_command" {
  value       = "ssh -i ~/.ssh/fineas-ec2 ec2-user@${aws_eip.app.public_ip}"
  description = "SSH command to connect to the instance"
}

output "app_url" {
  value       = "https://${aws_eip.app.public_ip}.nip.io"
  description = "Application URL (HTTPS via Caddy + nip.io)"
}
