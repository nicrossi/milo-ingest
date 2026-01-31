variable "environment" {
    type = string
}

variable "vpc_id" {
    type = string
}

variable "db_name" {
    type = string
}

variable "db_username" {
    type = string
}

variable "db_password" {
    type = string
    sensitive = true
}

variable "instance_class" {
    type = string
    default = "db.t3.micro"
}

variable "app_security_group_id" {
    type = string
    default = null
}
