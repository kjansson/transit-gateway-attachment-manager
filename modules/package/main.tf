data "archive_file" "dotfiles" {
    type        = "zip"
    output_path = var.output_path

    dynamic "source" {
        for_each = toset(var.src_files)
        content {
            content = file(source.value)
            filename = basename(source.value)
        }
    }
}